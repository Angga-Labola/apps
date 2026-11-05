const commentaryHeading = document.getElementById("commentary-heading");
const commentaryStatus = document.getElementById("commentary-status");
const commentaryContent = document.getElementById("commentary-content");
const backToChapter = document.getElementById("back-to-chapter");

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
    backToChapter.href = `/${encodeURIComponent(bookId)}/${chapter}`;

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
