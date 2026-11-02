const bookSelect = document.getElementById("book-select");
const chapterSelect = document.getElementById("chapter-select");
const verseSelect = document.getElementById("verse-select");
const previousButton = document.getElementById("previous-button");
const nextButton = document.getElementById("next-button");
const chapterHeading = document.getElementById("chapter-heading");
const chapterContent = document.getElementById("chapter-content");
const readerStatus = document.getElementById("reader-status");

let books = [];
let currentBook;
let currentChapter;
let requestNumber = 0;

function updateAddress(verse) {
    const url = new URL("/bible", window.location.origin);
    url.searchParams.set("book", currentBook.id);
    url.searchParams.set("chapter", String(currentChapter));
    if (verse) {
        url.searchParams.set("verse", String(verse));
    }
    window.history.pushState({}, "", url);
}

function setChapterOptions(book, selectedChapter) {
    chapterSelect.replaceChildren(...book.chapters.map((chapter) => {
        const option = document.createElement("option");
        option.value = String(chapter);
        option.textContent = String(chapter);
        option.selected = chapter === selectedChapter;
        return option;
    }));
    chapterSelect.disabled = false;
}

function setVerseOptions(verses, selectedVerse) {
    verseSelect.replaceChildren();
    const firstOption = document.createElement("option");
    firstOption.value = "";
    firstOption.textContent = "Choose a verse";
    verseSelect.append(firstOption);

    for (const verse of verses) {
        const option = document.createElement("option");
        option.value = String(verse);
        option.textContent = `Verse ${verse}`;
        option.selected = verse === selectedVerse;
        verseSelect.append(option);
    }
    verseSelect.disabled = verses.length === 0;
}

function findBook(bookId) {
    return books.find((book) => book.id === bookId) || books[0];
}

async function loadChapter(book, chapter, verse, addHistory = false) {
    const thisRequest = ++requestNumber;
    currentBook = book;
    currentChapter = chapter;
    setChapterOptions(book, chapter);
    bookSelect.value = book.id;
    previousButton.disabled = false;
    nextButton.disabled = false;
    readerStatus.textContent = "Opening your chapter...";
    chapterContent.replaceChildren();
    chapterHeading.textContent = `${book.name} ${chapter}`;
    verseSelect.disabled = true;

    try {
        const response = await fetch(`/${encodeURIComponent(book.id)}/${chapter}`);
        if (!response.ok) {
            throw new Error(`Could not load ${book.name} ${chapter}.`);
        }
        const html = await response.text();
        if (thisRequest !== requestNumber) {
            return;
        }

        const source = new DOMParser().parseFromString(html, "text/html");
        const content = [...source.body.children].filter((element) => (
            !element.matches("img, br, h2.c")
        ));
        chapterContent.replaceChildren(...content.map((element) => (
            document.importNode(element, true)
        )));

        const verseElements = [...chapterContent.querySelectorAll(".v[data-number]")];
        const verses = [...new Set(verseElements.map((element) => Number(element.dataset.number)))]
            .filter(Number.isInteger)
            .sort((left, right) => left - right);
        const selectedVerse = verses.includes(Number(verse)) ? Number(verse) : null;
        setVerseOptions(verses, selectedVerse);

        if (selectedVerse !== null) {
            const verseElement = verseElements.find((element) => (
                Number(element.dataset.number) === selectedVerse
            ));
            verseElement?.closest("p")?.classList.add("is-selected");
            verseElement?.scrollIntoView({ behavior: "smooth", block: "center" });
        }

        readerStatus.textContent = "";
        previousButton.disabled = book.chapters[0] === chapter && books[0].id === book.id;
        nextButton.disabled = book.chapters.at(-1) === chapter && books.at(-1).id === book.id;
        if (addHistory) {
            updateAddress(selectedVerse);
        }
    } catch (error) {
        if (thisRequest !== requestNumber) {
            return;
        }
        readerStatus.textContent = error.message;
        chapterHeading.textContent = "Unable to open this chapter";
        verseSelect.replaceChildren();
        verseSelect.disabled = true;
        previousButton.disabled = true;
        nextButton.disabled = true;
    }
}

function moveChapter(direction) {
    const bookIndex = books.indexOf(currentBook);
    const chapterIndex = currentBook.chapters.indexOf(currentChapter) + direction;
    if (chapterIndex >= 0 && chapterIndex < currentBook.chapters.length) {
        loadChapter(currentBook, currentBook.chapters[chapterIndex], null, true);
        return;
    }

    const nextBook = books[bookIndex + direction];
    if (nextBook) {
        const chapter = direction > 0 ? nextBook.chapters[0] : nextBook.chapters.at(-1);
        loadChapter(nextBook, chapter, null, true);
    }
}

bookSelect.addEventListener("change", () => {
    const book = findBook(bookSelect.value);
    loadChapter(book, book.chapters[0], null, true);
});

chapterSelect.addEventListener("change", () => {
    loadChapter(currentBook, Number(chapterSelect.value), null, true);
});

verseSelect.addEventListener("change", () => {
    const verse = Number(verseSelect.value);
    if (!verse) {
        chapterContent.querySelector("p.is-selected")?.classList.remove("is-selected");
        updateAddress(null);
        return;
    }
    loadChapter(currentBook, currentChapter, verse, true);
});

previousButton.addEventListener("click", () => moveChapter(-1));
nextButton.addEventListener("click", () => moveChapter(1));

window.addEventListener("popstate", () => {
    const params = new URLSearchParams(window.location.search);
    const book = findBook(params.get("book"));
    const requestedChapter = Number(params.get("chapter"));
    const chapter = book.chapters.includes(requestedChapter)
        ? requestedChapter
        : book.chapters[0];
    loadChapter(book, chapter, Number(params.get("verse")) || null);
});

async function startReader() {
    try {
        const response = await fetch("/api/bible/books");
        if (!response.ok) {
            throw new Error("The book list could not be loaded.");
        }
        const catalog = await response.json();
        books = catalog.books;
        if (books.length === 0) {
            throw new Error("No Bible chapters are available.");
        }

        bookSelect.replaceChildren(...books.map((book) => {
            const option = document.createElement("option");
            option.value = book.id;
            option.textContent = book.name;
            return option;
        }));
        bookSelect.disabled = false;

        const params = new URLSearchParams(window.location.search);
        const book = findBook(params.get("book"));
        const requestedChapter = Number(params.get("chapter"));
        const chapter = book.chapters.includes(requestedChapter)
            ? requestedChapter
            : book.chapters[0];
        loadChapter(book, chapter, Number(params.get("verse")) || null);
    } catch (error) {
        readerStatus.textContent = error.message;
        chapterHeading.textContent = "The reader could not be opened";
    }
}

startReader();
