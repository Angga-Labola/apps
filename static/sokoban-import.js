// The importer talks only to this app's backend; LetsLogic credentials and
// collection persistence are handled server-side.
const collectionSelect = document.getElementById("collection-select");
const downloadCollectionButton = document.getElementById("download-collection-button");
const collectionsStatusElement = document.getElementById("collections-status");
const importStatusElement = document.getElementById("import-status");
const levelTotalElement = document.getElementById("level-total");
const collectionDescriptionElement = document.getElementById("collection-description");
const collectionAuthorElement = document.getElementById("collection-author");

let collections = [];

function renderCollectionDescription(collection) {
    const description = typeof collection.description === "string"
        ? collection.description.trim()
        : "";
    const author = typeof collection.author === "string"
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
    levelTotalElement.textContent = `${collections.length} collections`;
    if (collections.length) {
        renderCollectionDescription(collections[0]);
    } else {
        levelTotalElement.textContent = "No collections";
        collectionDescriptionElement.textContent = "LetsLogic returned no collections.";
        collectionAuthorElement.textContent = "";
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
    } catch (error) {
        collectionsStatusElement.textContent = error.message;
        collectionSelect.disabled = true;
        downloadCollectionButton.disabled = true;
        levelTotalElement.textContent = "Unavailable";
    }
}

async function downloadSelectedCollection() {
    const selected = collections.find(
        (collection) => collection.id === collectionSelect.value,
    );
    if (!selected) return;

    downloadCollectionButton.disabled = true;
    importStatusElement.textContent = `Importing ${selected.name}…`;
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
            throw new Error(error.detail || "Could not import this collection.");
        }

        const collection = await response.json();
        if (!Array.isArray(collection.levels)) {
            throw new Error("LetsLogic returned an unexpected level collection.");
        }

        importStatusElement.textContent =
            `${selected.name} imported. Return to the game and open it under Saved collections.`;
    } catch (error) {
        importStatusElement.textContent = error.message;
    } finally {
        downloadCollectionButton.disabled = collections.length === 0;
    }
}

collectionSelect.addEventListener("change", () => {
    const collection = collections.find((entry) => entry.id === collectionSelect.value);
    if (collection) renderCollectionDescription(collection);
});
downloadCollectionButton.addEventListener("click", downloadSelectedCollection);

loadLetsLogicCollections();
