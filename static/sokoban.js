const PRACTICE_LEVEL = {
    name: "Practice level",
    map: "#######\n#     #\n#  .  #\n#  $  #\n#  @  #\n#######",
};
const DIRECTIONS = {
    up: { x: 0, y: -1 },
    down: { x: 0, y: 1 },
    left: { x: -1, y: 0 },
    right: { x: 1, y: 0 },
};
const PLAYER_SPRITES = {
    up: "player_02.png",
    down: "player_01.png",
    left: "player_14.png",
    right: "player_11.png",
};
const LEVEL_PAGE_SIZE = 50;
const ASSET_ROOT = "/static/sokoban_assets/PNG/Default%20size";

const boardElement = document.getElementById("game-board");
const gameGridElement = document.getElementById("game-grid");
const gamePanelElement = document.querySelector(".game-panel");
const fullscreenButton = document.getElementById("fullscreen-button");
const levelNameElement = document.getElementById("current-level-name");
const moveCountElement = document.getElementById("move-count");
const pushCountElement = document.getElementById("push-count");
const gameStatusElement = document.getElementById("game-status");
const levelsStatusElement = document.getElementById("levels-status");
const levelTotalElement = document.getElementById("level-total");
const levelListElement = document.getElementById("level-list");
const showMoreButton = document.getElementById("show-more-button");
const downloadCollectionButton = document.getElementById("download-collection-button");
const collectionSelect = document.getElementById("collection-select");
const collectionsStatusElement = document.getElementById("collections-status");
const collectionDescriptionElement = document.getElementById("collection-description");
const collectionAuthorElement = document.getElementById("collection-author");
const savedCollectionSelect = document.getElementById("saved-collection-select");
const savedCollectionsStatusElement = document.getElementById("saved-collections-status");
const openSavedCollectionButton = document.getElementById("open-saved-collection-button");
const deleteSavedCollectionButton = document.getElementById("delete-saved-collection-button");
const levelListHeading = document.getElementById("level-list-heading");
const previousButton = document.getElementById("previous-button");
const nextButton = document.getElementById("next-button");

let levels = [];
let collections = [];
let savedCollections = [];
let selectedLevelIndex = -1;
let visibleLevelCount = LEVEL_PAGE_SIZE;
let currentGame;
let collectionId = "550";
let collectionName = "Practice level";
let levelsMessage = "Choose or download a collection to list its levels.";

function getLevelName(level, index) {
    if (typeof level === "string") {
        return `Level ${index + 1}`;
    }
    if (!level || typeof level !== "object") {
        return `Level ${index + 1}`;
    }
    const name = level.name ?? level.title ?? level.level_name;
    const id = level.id ?? level.level_id ?? level.number;
    if (name && id !== undefined) {
        return `${id}. ${name}`;
    }
    return String(name ?? id ?? `Level ${index + 1}`);
}

function getLevelMap(level) {
    if (typeof level === "string") {
        return level;
    }
    if (!level || typeof level !== "object") {
        return null;
    }

    for (const key of ["map", "level", "layout", "board", "data"]) {
        const value = level[key];
        if (typeof value === "string"
            && /^[0-7]+$/.test(value)
            && Number.isInteger(level.width)
            && Number.isInteger(level.height)
            && level.width > 0
            && level.height > 0
            && value.length === level.width * level.height) {
            const tiles = " #@$.*+#";
            return Array.from(
                { length: level.height },
                (_, row) => Array.from(
                    value.slice(row * level.width, (row + 1) * level.width),
                    (tile) => tiles[Number(tile)],
                ).join(""),
            ).join("\n");
        }
        if (typeof value === "string"
            && (/[\r\n]/.test(value) || (value.includes("@") && value.includes("$")))) {
            return value;
        }
        if (Array.isArray(value) && value.every((row) => typeof row === "string")) {
            return value.join("\n");
        }
    }
    return null;
}

function parseMap(mapText) {
    const rows = mapText
        .replace(/\r/g, "")
        .split("\n")
        .map((row) => row.replace(/\s+$/, ""));
    while (rows.length && rows[0].trim() === "") rows.shift();
    while (rows.length && rows[rows.length - 1].trim() === "") rows.pop();
    if (!rows.length) {
        throw new Error("This level has an empty map.");
    }

    const game = {
        rows,
        width: Math.max(...rows.map((row) => row.length)),
        height: rows.length,
        walls: new Set(),
        goals: new Set(),
        boxes: new Set(),
        player: null,
        facing: "down",
        moves: 0,
        pushes: 0,
        history: [],
        won: false,
    };

    for (let y = 0; y < game.height; y += 1) {
        for (let x = 0; x < game.width; x += 1) {
            const cell = rows[y][x] ?? " ";
            const position = `${x},${y}`;
            if (cell === "#") game.walls.add(position);
            if (cell === "." || cell === "*" || cell === "+") game.goals.add(position);
            if (cell === "$" || cell === "*") game.boxes.add(position);
            if (cell === "@" || cell === "+") {
                if (game.player !== null) throw new Error("This level has more than one player.");
                game.player = { x, y };
            }
        }
    }

    if (!game.player || game.boxes.size === 0 || game.goals.size === 0) {
        throw new Error("This level map needs a player, at least one crate, and at least one goal.");
    }
    if (game.boxes.size !== game.goals.size) {
        throw new Error("This level has a different number of crates and goals.");
    }
    return game;
}

function positionKey(x, y) {
    return `${x},${y}`;
}

function isWall(game, x, y) {
    return x < 0 || y < 0 || x >= game.width || y >= game.height
        || game.walls.has(positionKey(x, y));
}

function saveHistory(game) {
    game.history.push({
        player: { ...game.player },
        facing: game.facing,
        boxes: [...game.boxes],
        moves: game.moves,
        pushes: game.pushes,
        won: game.won,
    });
}

function movePlayer(direction) {
    const delta = DIRECTIONS[direction];
    if (!currentGame || currentGame.won) return;

    const nextX = currentGame.player.x + delta.x;
    const nextY = currentGame.player.y + delta.y;
    const nextPosition = positionKey(nextX, nextY);
    if (isWall(currentGame, nextX, nextY)) {
        currentGame.facing = direction;
        updatePlayerSprite();
        return;
    }

    const nextBoxes = new Set(currentGame.boxes);
    let pushed = false;
    if (nextBoxes.has(nextPosition)) {
        const boxX = nextX + delta.x;
        const boxY = nextY + delta.y;
        const boxDestination = positionKey(boxX, boxY);
        if (isWall(currentGame, boxX, boxY) || nextBoxes.has(boxDestination)) {
            currentGame.facing = direction;
            updatePlayerSprite();
            return;
        }
        nextBoxes.delete(nextPosition);
        nextBoxes.add(boxDestination);
        pushed = true;
    }

    saveHistory(currentGame);
    currentGame.facing = direction;
    currentGame.boxes = nextBoxes;
    currentGame.player = { x: nextX, y: nextY };
    currentGame.moves += 1;
    if (pushed) currentGame.pushes += 1;
    currentGame.won = [...currentGame.boxes].every((position) => currentGame.goals.has(position));
    renderGame();
}

function undoMove() {
    if (!currentGame || !currentGame.history.length) return;
    const previous = currentGame.history.pop();
    currentGame.player = previous.player;
    currentGame.facing = previous.facing;
    currentGame.boxes = new Set(previous.boxes);
    currentGame.moves = previous.moves;
    currentGame.pushes = previous.pushes;
    currentGame.won = previous.won;
    renderGame();
}

function centerPlayer(behavior = "smooth") {
    const playerCell = gameGridElement.querySelector(".is-player");
    if (!playerCell) return;

    const boardRect = boardElement.getBoundingClientRect();
    const playerRect = playerCell.getBoundingClientRect();
    boardElement.scrollTo({
        left: boardElement.scrollLeft
            + playerRect.left - boardRect.left - boardElement.clientLeft
            + (playerRect.width - boardElement.clientWidth) / 2,
        top: boardElement.scrollTop
            + playerRect.top - boardRect.top - boardElement.clientTop
            + (playerRect.height - boardElement.clientHeight) / 2,
        behavior,
    });
}

function updateFullscreenButton() {
    const isFullscreen = document.fullscreenElement === gamePanelElement;
    fullscreenButton.textContent = isFullscreen ? "Exit fullscreen" : "Fullscreen";
    fullscreenButton.setAttribute("aria-label", isFullscreen
        ? "Exit fullscreen game view"
        : "Enter fullscreen game view");
    fullscreenButton.setAttribute("aria-pressed", String(isFullscreen));
}

function updatePlayerSprite() {
    const playerImage = gameGridElement.querySelector(".is-player img");
    if (playerImage) {
        playerImage.src = `${ASSET_ROOT}/Player/${PLAYER_SPRITES[currentGame.facing]}`;
    }
}

function renderGame() {
    if (!currentGame) return;
    gameGridElement.replaceChildren();
    gameGridElement.style.gridTemplateColumns = `repeat(${currentGame.width}, var(--tile-size))`;

    for (let y = 0; y < currentGame.height; y += 1) {
        for (let x = 0; x < currentGame.width; x += 1) {
            const position = positionKey(x, y);
            const cell = document.createElement("div");
            cell.className = "game-cell";
            if (isWall(currentGame, x, y)) {
                cell.classList.add("is-wall");
            } else if (currentGame.goals.has(position)) {
                cell.classList.add("is-goal");
            }

            let sprite = null;
            if (currentGame.boxes.has(position)) {
                if (currentGame.goals.has(position)) {
                    cell.classList.add("is-box-on-goal");
                    sprite = `${ASSET_ROOT}/Crates/crate_05.png`;
                } else {
                    cell.classList.add("is-box");
                    sprite = `${ASSET_ROOT}/Crates/crate_02.png`;
                }
            } else if (currentGame.player.x === x && currentGame.player.y === y) {
                cell.classList.add("is-player");
                sprite = `${ASSET_ROOT}/Player/${PLAYER_SPRITES[currentGame.facing]}`;
            }

            if (sprite) {
                const image = document.createElement("img");
                image.src = sprite;
                image.alt = currentGame.boxes.has(position) ? "Crate" : "Player";
                cell.append(image);
            }
            gameGridElement.append(cell);
        }
    }

    moveCountElement.textContent = String(currentGame.moves);
    pushCountElement.textContent = String(currentGame.pushes);
    gameStatusElement.classList.toggle("is-won", currentGame.won);
    gameStatusElement.textContent = currentGame.won
        ? `Level complete in ${currentGame.moves} moves and ${currentGame.pushes} pushes!`
        : "Use the arrow keys or WASD to move.";
    previousButton.disabled = selectedLevelIndex <= 0;
    nextButton.disabled = selectedLevelIndex < 0
        || selectedLevelIndex >= levels.length - 1;
    requestAnimationFrame(() => centerPlayer());
}

function selectLevel(index) {
    if (index < 0 || index >= levels.length) return;
    const level = levels[index];
    selectedLevelIndex = index;
    levelNameElement.textContent = getLevelName(level, index);
    previousButton.disabled = index <= 0;
    nextButton.disabled = index >= levels.length - 1;
    renderLevelList();

    const map = getLevelMap(level);
    if (!map) {
        currentGame = null;
        gameGridElement.replaceChildren();
        moveCountElement.textContent = "0";
        pushCountElement.textContent = "0";
        gameStatusElement.textContent = "This level has no supported text map. You can still download its LetsLogic data.";
        gameStatusElement.classList.remove("is-won");
        previousButton.disabled = index <= 0;
        nextButton.disabled = index >= levels.length - 1;
        return;
    }

    try {
        currentGame = parseMap(map);
    } catch (error) {
        currentGame = null;
        gameGridElement.replaceChildren();
        moveCountElement.textContent = "0";
        pushCountElement.textContent = "0";
        gameStatusElement.textContent = error.message;
        gameStatusElement.classList.remove("is-won");
        previousButton.disabled = index <= 0;
        nextButton.disabled = index >= levels.length - 1;
        return;
    }

    renderGame();
}

function renderLevelList() {
    const indexes = levels.map((_, index) => index);
    const shown = indexes.slice(0, visibleLevelCount);
    levelListElement.replaceChildren();

    for (const index of shown) {
        const item = document.createElement("li");
        const button = document.createElement("button");
        button.type = "button";
        button.setAttribute("aria-current", index === selectedLevelIndex ? "true" : "false");
        button.addEventListener("click", () => selectLevel(index));
        const name = document.createElement("span");
        name.textContent = getLevelName(levels[index], index);
        const number = document.createElement("small");
        number.textContent = `#${index + 1}`;
        button.append(name, number);
        item.append(button);
        levelListElement.append(item);
    }

    levelsStatusElement.textContent = levels.length
        ? `${levelsMessage} Showing ${shown.length} of ${indexes.length} levels.`
        : levelsMessage;
    showMoreButton.hidden = shown.length >= indexes.length;
}

function renderCollectionDescription(collection) {
    const description = typeof collection?.description === "string"
        ? collection.description.trim()
        : "";
    const author = typeof collection?.author === "string"
        ? collection.author.trim()
        : "";
    collectionDescriptionElement.textContent = description || "No description provided by LetsLogic.";
    collectionAuthorElement.textContent = author ? `By ${author}` : "";
}

function populateCollectionSelect() {
    collectionSelect.replaceChildren();
    for (const collection of collections) {
        const option = document.createElement("option");
        option.value = collection.id;
        const count = collection.level_count === undefined
            ? ""
            : ` · ${collection.level_count} levels`;
        option.textContent = `${collection.name}${count}`;
        collectionSelect.append(option);
    }
    collectionSelect.disabled = collections.length === 0;
    downloadCollectionButton.disabled = collections.length === 0;
}

function populateSavedCollectionSelect() {
    savedCollectionSelect.replaceChildren();
    for (const collection of savedCollections) {
        const option = document.createElement("option");
        option.value = collection.collection_id;
        option.textContent = `${collection.name} · ${collection.level_count} levels`;
        savedCollectionSelect.append(option);
    }
    if (!savedCollections.length) {
        const option = document.createElement("option");
        option.textContent = "No saved collections";
        savedCollectionSelect.append(option);
    }
    savedCollectionSelect.disabled = savedCollections.length === 0;
    openSavedCollectionButton.disabled = savedCollections.length === 0;
    deleteSavedCollectionButton.disabled = savedCollections.length === 0;
}

function activateCollection(collection, sourceMessage) {
    levels = collection.levels;
    collectionId = String(collection.collection_id ?? "");
    collectionName = String(collection.name ?? `Collection ${collectionId}`);
    selectedLevelIndex = -1;
    visibleLevelCount = LEVEL_PAGE_SIZE;
    levelNameElement.textContent = collectionName;
    levelListHeading.textContent = collectionName;
    levelTotalElement.textContent = `${levels.length} levels`;
    levelsMessage = sourceMessage;
    renderCollectionDescription(collection);
    gameGridElement.replaceChildren();
    moveCountElement.textContent = "0";
    pushCountElement.textContent = "0";
    currentGame = null;
    previousButton.disabled = levels.length < 2 || selectedLevelIndex <= 0;
    nextButton.disabled = levels.length < 2;
    renderLevelList();

    if (levels.length) {
        selectLevel(0);
    } else {
        gameStatusElement.textContent = "This collection has no playable levels.";
        gameStatusElement.classList.remove("is-won");
    }
}

async function loadLetsLogicCollections() {
    try {
        const response = await fetch("/api/sokoban/collections");
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || "Could not load LetsLogic collections.");
        }
        const result = await response.json();
        if (!Array.isArray(result.collections)) {
            throw new Error("LetsLogic returned an unexpected collection list.");
        }

        collections = result.collections;
        populateCollectionSelect();
        collectionsStatusElement.textContent = `${collections.length} LetsLogic collections available.`;
        if (collections.length) {
            renderCollectionDescription(collections[0]);
        }
    } catch (error) {
        collectionsStatusElement.textContent = `${error.message} You can still play the practice level.`;
        collectionSelect.disabled = true;
        downloadCollectionButton.disabled = true;
    }
}

async function loadSavedCollections() {
    try {
        const response = await fetch("/api/sokoban/saved-collections");
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || "Could not load saved collections.");
        }
        const result = await response.json();
        savedCollections = result.collections;
        populateSavedCollectionSelect();
        savedCollectionsStatusElement.textContent = result.storage === "vercel_blob"
            ? `${savedCollections.length} saved in the server.`
            : `${savedCollections.length} saved in data/sokoban/collections/.`;
    } catch (error) {
        savedCollectionsStatusElement.textContent = error.message;
        savedCollectionSelect.disabled = true;
        openSavedCollectionButton.disabled = true;
        deleteSavedCollectionButton.disabled = true;
    }
}

async function downloadSelectedCollection() {
    const selected = collections.find(
        (collection) => collection.id === collectionSelect.value,
    );
    if (!selected) return;

    downloadCollectionButton.disabled = true;
    collectionsStatusElement.textContent = `Importing ${selected.name}…`;
    try {
        const response = await fetch(
            `/api/sokoban/collections/${encodeURIComponent(selected.id)}/download`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: selected.name,
                    description: selected.description,
                    author: selected.author,
                }),
            },
        );
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || "Could not download this collection.");
        }

        const collection = await response.json();
        if (!Array.isArray(collection.levels)) {
            throw new Error("LetsLogic returned an unexpected level collection.");
        }
        const storageMessage = collection.storage === "vercel_blob"
            ? `Saved to the server as ${collection.saved_file};`
            : `Saved to data/sokoban/collections/${collection.saved_file}`;
        collectionsStatusElement.textContent = `${storageMessage}`;
        activateCollection(
            collection,
            `${collection.levels.length} levels downloaded and ready to play.`,
        );
        await loadSavedCollections();
    } catch (error) {
        collectionsStatusElement.textContent = error.message;
    } finally {
        downloadCollectionButton.disabled = collections.length === 0;
    }
}

async function openSavedCollection() {
    const id = savedCollectionSelect.value;
    if (!id) return;
    openSavedCollectionButton.disabled = true;
    try {
        const response = await fetch(
            `/api/sokoban/saved-collections/${encodeURIComponent(id)}`,
        );
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || "Could not open this saved collection.");
        }
        const collection = await response.json();
        activateCollection(
            collection,
            `${collection.levels.length} saved levels loaded.`,
        );
    } catch (error) {
        savedCollectionsStatusElement.textContent = error.message;
    } finally {
        openSavedCollectionButton.disabled = savedCollections.length === 0;
    }
}

async function deleteSavedCollection() {
    const id = savedCollectionSelect.value;
    if (!id) return;
    const collection = savedCollections.find(
        (entry) => entry.collection_id === id,
    );
    const name = collection?.name ?? `Collection ${id}`;
    if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return;

    deleteSavedCollectionButton.disabled = true;
    try {
        const response = await fetch(
            `/api/sokoban/saved-collections/${encodeURIComponent(id)}`,
            { method: "DELETE" },
        );
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || "Could not delete this collection.");
        }

        savedCollectionsStatusElement.textContent = `${name} was deleted.`;
        if (collectionId === id) {
            activateCollection(
                {
                    collection_id: "",
                    name: PRACTICE_LEVEL.name,
                    levels: [PRACTICE_LEVEL],
                },
                "Built-in practice level.",
            );
        }
        await loadSavedCollections();
    } catch (error) {
        savedCollectionsStatusElement.textContent = error.message;
    } finally {
        deleteSavedCollectionButton.disabled = savedCollections.length === 0;
    }
}

showMoreButton.addEventListener("click", () => {
    visibleLevelCount += LEVEL_PAGE_SIZE;
    renderLevelList();
});
document.getElementById("previous-button").addEventListener("click", () => {
    if (selectedLevelIndex > 0) selectLevel(selectedLevelIndex - 1);
});
document.getElementById("undo-button").addEventListener("click", undoMove);
document.getElementById("restart-button").addEventListener("click", () => {
    if (selectedLevelIndex >= 0) selectLevel(selectedLevelIndex);
});
nextButton.addEventListener("click", () => {
    if (selectedLevelIndex < levels.length - 1) selectLevel(selectedLevelIndex + 1);
});
collectionSelect.addEventListener("change", () => {
    const collection = collections.find((entry) => entry.id === collectionSelect.value);
    if (collection) renderCollectionDescription(collection);
});
downloadCollectionButton.addEventListener("click", downloadSelectedCollection);
openSavedCollectionButton.addEventListener("click", openSavedCollection);
deleteSavedCollectionButton.addEventListener("click", deleteSavedCollection);
fullscreenButton.addEventListener("click", async () => {
    try {
        if (document.fullscreenElement === gamePanelElement) {
            await document.exitFullscreen();
        } else if (gamePanelElement.requestFullscreen) {
            await gamePanelElement.requestFullscreen();
        } else {
            throw new Error("Fullscreen is not supported by this browser.");
        }
        updateFullscreenButton();
        requestAnimationFrame(() => centerPlayer("auto"));
    } catch (error) {
        gameStatusElement.textContent = `Could not enter fullscreen: ${error.message}`;
    }
});
document.addEventListener("fullscreenchange", () => {
    updateFullscreenButton();
    requestAnimationFrame(() => centerPlayer("auto"));
});
window.addEventListener("resize", () => centerPlayer("auto"));
document.querySelectorAll("[data-move]").forEach((button) => {
    button.addEventListener("click", () => movePlayer(button.dataset.move));
});
document.addEventListener("keydown", (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey
        || event.target instanceof HTMLInputElement
        || event.target instanceof HTMLTextAreaElement
        || event.target instanceof HTMLSelectElement) return;

    const key = event.key.toLowerCase();
    const direction = {
        arrowup: "up", w: "up",
        arrowdown: "down", s: "down",
        arrowleft: "left", a: "left",
        arrowright: "right", d: "right",
    }[key];
    if (direction) {
        event.preventDefault();
        movePlayer(direction);
    } else if (key === "z") {
        undoMove();
    } else if (key === "r" && selectedLevelIndex >= 0) {
        selectLevel(selectedLevelIndex);
    }
});

levels = [PRACTICE_LEVEL];
selectedLevelIndex = 0;
levelNameElement.textContent = PRACTICE_LEVEL.name;
levelListHeading.textContent = PRACTICE_LEVEL.name;
levelTotalElement.textContent = "Practice level";
selectLevel(0);
loadLetsLogicCollections();
loadSavedCollections();
