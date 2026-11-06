const commentaryHeading = document.getElementById("commentary-heading");
const commentaryStatus = document.getElementById("commentary-status");
const commentaryContent = document.getElementById("commentary-content");
const previousCommentary = document.getElementById("previous-commentary");
const nextCommentary = document.getElementById("next-commentary");
const navigationStatus = document.getElementById("commentary-navigation-status");

function setNavigationLink(link, passage, commentaryId, label) {
    if (!passage) {
        link.removeAttribute("href");
        link.setAttribute("aria-disabled", "true");
        link.tabIndex = -1;
        return;
    }

    link.href = `/commentary/${encodeURIComponent(commentaryId)}/${encodeURIComponent(passage.id)}/${passage.chapter}`;
    link.removeAttribute("aria-disabled");
    link.tabIndex = 0;
    link.setAttribute("aria-label", `${label}: ${passage.name} ${passage.chapter}`);
}

async function setupChapterNavigation(commentaryId, bookId, chapter) {
    const response = await fetch("/api/bible/books");
    if (!response.ok) {
        throw new Error("The chapter list could not be loaded.");
    }

    const catalog = await response.json();
    const passages = catalog.books.flatMap((book) => (
        book.chapters.map((chapterNumber) => ({
            id: book.id,
            name: book.name,
            chapter: chapterNumber,
        }))
    ));
    const currentIndex = passages.findIndex((passage) => (
        passage.id === bookId && passage.chapter === chapter
    ));
    if (currentIndex === -1) {
        throw new Error("This chapter is not in the available chapter list.");
    }

    setNavigationLink(
        previousCommentary,
        passages[currentIndex - 1],
        commentaryId,
        "Previous chapter",
    );
    setNavigationLink(
        nextCommentary,
        passages[currentIndex + 1],
        commentaryId,
        "Next chapter",
    );
}

function appendSourceLink(container, href, label) {
    if (typeof href !== "string" || !href.startsWith("https://")) {
        return;
    }
    const link = document.createElement("a");
    link.href = href;
    link.textContent = label;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    container.append(link);
}

function renderCommentary(data) {
    const chapter = data.chapter;
    commentaryHeading.textContent = `${data.commentary_name} — ${data.book} ${chapter.number}`;
    document.title = `${data.commentary_name} — ${data.book} ${chapter.number}`;
    commentaryStatus.textContent = "";
    commentaryContent.replaceChildren();

    const attribution = document.createElement("p");
    attribution.className = "commentary-attribution";
    attribution.append(document.createTextNode("Source: "));
    appendSourceLink(attribution, data.website, data.commentary_name);
    if (data.license_url) {
        attribution.append(document.createTextNode(" · "));
        appendSourceLink(attribution, data.license_url, "License");
    }
    commentaryContent.append(attribution);

    if (typeof chapter.introduction === "string" && chapter.introduction.trim()) {
        const introduction = document.createElement("p");
        introduction.className = "commentary-entry";
        introduction.textContent = chapter.introduction;
        commentaryContent.append(introduction);
    }

    for (const entry of chapter.content) {
        if (!entry || !Array.isArray(entry.content)) {
            continue;
        }
        const text = entry.content.filter((part) => typeof part === "string").join("\n\n");
        if (!text.trim()) {
            continue;
        }
        const section = document.createElement("section");
        section.className = "commentary-entry";
        if (entry.type === "verse" && Number.isInteger(entry.number)) {
            const heading = document.createElement("h2");
            heading.textContent = `Verse ${entry.number}`;
            section.append(heading);
        }
        const paragraph = document.createElement("p");
        paragraph.textContent = text;
        section.append(paragraph);
        commentaryContent.append(section);
    }
}

async function loadCommentary() {
    const match = window.location.pathname.match(
        /^\/commentary\/([a-z-]+)\/([A-Z0-9]{3})\/(\d+)\/?$/,
    );
    if (!match) {
        throw new Error("The commentary URL is invalid.");
    }
    const [, commentaryId, bookId, chapter] = match;
    const chapterNumber = Number(chapter);
    try {
        await setupChapterNavigation(commentaryId, bookId, chapterNumber);
    } catch (error) {
        navigationStatus.textContent = error.message;
    }

    try {
        const response = await fetch(
            `/api/bible/commentary/${encodeURIComponent(commentaryId)}/${encodeURIComponent(bookId)}/${chapter}`,
        );
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Could not load this commentary.");
        }
        renderCommentary(data);
    } catch (error) {
        commentaryHeading.textContent = "Commentary unavailable";
        commentaryStatus.textContent = error.message;
    }
}

loadCommentary();
