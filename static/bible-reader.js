const bookSelect = document.getElementById("book-select");
const chapterSelect = document.getElementById("chapter-select");
const commentarySelect = document.getElementById("commentary-select");
const openCommentaryLink = document.getElementById("open-commentary-link");
const previousButton = document.getElementById("previous-button");
const nextButton = document.getElementById("next-button");
const chapterHeading = document.getElementById("chapter-heading");
const chapterContent = document.getElementById("chapter-content");
const readerStatus = document.getElementById("reader-status");

let books = [];
let currentBook;
let currentChapter;
let requestNumber = 0;

function chapterUrl(book, chapter) {
    return new URL(`/${book.id}/${chapter}`, window.location.origin);
}

function navigateToChapter(book, chapter) {
    window.location.assign(chapterUrl(book, chapter));
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

function findBook(bookId) {
    return books.find((book) => book.id === bookId) || books[0];
}

function updateCommentaryLink() {
    const commentaryId = commentarySelect.value;
    if (!commentaryId) {
        openCommentaryLink.href = "#";
        openCommentaryLink.setAttribute("aria-disabled", "true");
        openCommentaryLink.tabIndex = -1;
        return;
    }

    openCommentaryLink.href = new URL(
        `/commentary/${encodeURIComponent(commentaryId)}/${encodeURIComponent(currentBook.id)}/${currentChapter}`,
        window.location.origin,
    ).href;
    openCommentaryLink.removeAttribute("aria-disabled");
    openCommentaryLink.tabIndex = 0;
}

async function loadChapter(book, chapter, verse = null) {
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
    commentarySelect.disabled = true;
    commentarySelect.value = "";
    updateCommentaryLink();

    try {
        const response = await fetch(
            `/api/bible/${encodeURIComponent(book.id)}/${chapter}`,
        );
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

        if (verse !== null) {
            const verseElement = chapterContent.querySelector(
                `.v[data-number="${CSS.escape(String(verse))}"]`,
            );
            verseElement?.closest("p")?.classList.add("is-selected");
            verseElement?.scrollIntoView({ behavior: "smooth", block: "center" });
        }

        readerStatus.textContent = "";
        commentarySelect.disabled = false;
        previousButton.disabled = book.chapters[0] === chapter && books[0].id === book.id;
        nextButton.disabled = book.chapters.at(-1) === chapter && books.at(-1).id === book.id;
    } catch (error) {
        if (thisRequest !== requestNumber) {
            return;
        }
        readerStatus.textContent = error.message;
        chapterHeading.textContent = "Unable to open this chapter";
        commentarySelect.disabled = true;
        previousButton.disabled = true;
        nextButton.disabled = true;
    }
}

function moveChapter(direction) {
    const bookIndex = books.indexOf(currentBook);
    const chapterIndex = currentBook.chapters.indexOf(currentChapter) + direction;
    if (chapterIndex >= 0 && chapterIndex < currentBook.chapters.length) {
        navigateToChapter(currentBook, currentBook.chapters[chapterIndex]);
        return;
    }

    const nextBook = books[bookIndex + direction];
    if (nextBook) {
        const chapter = direction > 0 ? nextBook.chapters[0] : nextBook.chapters.at(-1);
        navigateToChapter(nextBook, chapter);
    }
}

bookSelect.addEventListener("change", () => {
    const book = findBook(bookSelect.value);
    navigateToChapter(book, book.chapters[0]);
});

chapterSelect.addEventListener("change", () => {
    navigateToChapter(currentBook, Number(chapterSelect.value));
});

commentarySelect.addEventListener("change", () => {
    updateCommentaryLink();
});

previousButton.addEventListener("click", () => moveChapter(-1));
nextButton.addEventListener("click", () => moveChapter(1));

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

        const path = window.location.pathname.match(/^\/([A-Z0-9]{3})\/(\d+)\/?$/);
        const book = findBook(path?.[1]);
        const requestedChapter = Number(path?.[2]);
        const chapter = book.chapters.includes(requestedChapter)
            ? requestedChapter
            : book.chapters[0];
        const verse = Number(new URLSearchParams(window.location.search).get("verse")) || null;
        const url = chapterUrl(book, chapter);
        if (window.location.pathname !== url.pathname) {
            window.location.replace(url);
            return;
        }
        currentBook = book;
        currentChapter = chapter;
        loadChapter(book, chapter, verse);
    } catch (error) {
        readerStatus.textContent = error.message;
        chapterHeading.textContent = "The reader could not be opened";
    }
}

startReader();
