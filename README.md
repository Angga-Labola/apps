# Bible Reader

The Bible reader is a FastAPI page that loads chapter text from the local HTML
files in `templates/bible/`. The page and the chapter content are separate:
chapter URLs display the reader interface, while a chapter API route serves
the HTML that the reader inserts into the page.

## Sokoban

The Sokoban game is served at `/sokoban`. It lists collections from LetsLogic
through the FastAPI backend, so the LetsLogic API key is never sent to the
browser. Choose a collection and click **Import & play** to persist it and
immediately load its levels into the game. Local runs save JSON files in
`data/sokoban/collections/`; Vercel deployments save them to Vercel Blob.
Descriptions and authors are shown when available from LetsLogic. Saved
collections appear in the **Saved collections** selector and can be reopened
or deleted. Use the **Fullscreen** button to expand the game to the browser
view; the board follows the player as you move or undo. A built-in practice
board remains available when the API key is missing or LetsLogic cannot be
reached.

Set `SOKOBAN_KEY` in the local `.env` file for development or as an environment
variable in Vercel. `SOKOBAN_COLLECTION_ID` sets the default collection for the
legacy `/api/sokoban/levels` endpoint; it defaults to `550`.
`SOKOBAN_COLLECTIONS_DIR` can override the local saved-collection directory.
The `/api/sokoban/health` endpoint reports whether the LetsLogic key is
configured without returning the key.

For Vercel deployments, create a Blob store and connect it to the project.
The Vercel Blob Python SDK uses the connected store's Vercel credentials; a
`BLOB_READ_WRITE_TOKEN` can also be configured when needed. Set
`SOKOBAN_BLOB_ACCESS` to match the store's access mode (`public` or `private`);
it defaults to `public`. The delete button asks for confirmation, but any
visitor to the public site can delete a saved collection.

Run the app locally with:

```powershell
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000/sokoban` to play. Vercel detects the FastAPI app
through the `tool.vercel.entrypoint` setting in `pyproject.toml`; add
`SOKOBAN_KEY` in the Vercel project's environment variables before deploying.
Local development stores collection files in the project folder; game progress
remains in the browser.

## Main pieces

- `templates/bible_reader.html` provides the reader layout, selectors, buttons,
  status area, and chapter-content container. It loads
  `static/bible-reader.js` and the Giscus client.
- `static/bible-reader.js` loads the book catalog, fetches chapter HTML, updates
  the controls, opens selected commentary in a new tab, and handles navigation.
- `templates/bible/<BOOK>/<BOOK>_<CHAPTER>.html` contains the source HTML for
  each chapter. For example, Genesis chapter 2 is
  `templates/bible/GEN/GEN_2.html`.
- `app.py` provides the reader page, book catalog, and chapter-content routes.

## Routes and requests

| Route | Purpose |
| --- | --- |
| `/bible` | Opens the reader. If no passage is specified, the reader redirects to the first available chapter URL. |
| `/{book_id}/{chapter_id}` | Validates that the book and chapter exist, then serves `templates/bible_reader.html`. For example, `/GEN/2` is the Genesis 2 reader page. |
| `/api/bible/books` | Scans the chapter files and returns the available books and chapter numbers as JSON. |
| `/api/bible/{book_id}/{chapter_id}` | Validates the requested passage and returns its source chapter HTML. The reader fetches this route to display the chapter. |
| `/api/bible/commentary/{commentary_id}/{book_id}/{chapter_id}` | Fetches chapter commentary from the Free Use Bible API for an allowed commentary. |
| `/commentary/{commentary_id}/{book_id}/{chapter_id}` | Serves the commentary page opened from the reader's commentary selector, with chapter navigation. |

The two chapter-shaped routes have distinct roles. `/GEN/2` is the actual page
URL; `/api/bible/GEN/2` is a data request made by the reader's JavaScript.
Keeping the page URL specific to each passage also lets Giscus use the
pathname to identify a chapter's discussion.

## What happens when a reader opens

1. The browser requests `/GEN/2` (or another chapter URL). FastAPI checks the
   book ID, numeric chapter ID, and matching file. It serves the shared reader
   page rather than returning the chapter file directly.
2. The browser loads `static/bible-reader.js`. Its `startReader()` function
   requests `/api/bible/books` and builds the book selector from the returned
   catalog.
3. The script reads the book and chapter from the URL path. It also reads an
   optional `verse` query parameter. If the path is not a valid chapter path,
   it chooses the first available chapter and redirects to that chapter's URL.
4. `loadChapter()` requests the corresponding `/api/bible/{book}/{chapter}`
   route. It parses the returned HTML, removes the chapter's image, line
   breaks, and source heading, then inserts the verse content into the reader.
5. The script enables the commentary selector and the Previous and Next
   buttons as appropriate for the first and last available chapters.

## Navigation and URLs

- Selecting a book opens its first available chapter.
- Selecting a chapter, or using Previous/Next, navigates to that chapter's
  page URL. Moving past the beginning or end of a book continues to the
  previous or next book when one exists.
- Browser back and forward navigation reloads the passage indicated by the
  current URL.
- A request counter prevents an older, slower chapter request from replacing
  content from a newer request.

## Chapter commentaries

The selector offers John Calvin, John Gill, Matthew Henry, and
Jamieson-Fausset-Brown. Choose an author and click **Open** to open its
dedicated commentary page in a new tab for the current book and chapter. The page
has Previous/Next chapter controls and a Back to top link. The
separate button avoids browsers blocking a new tab opened directly by a
dropdown change. That page fetches commentary through the backend API route.
The backend uses the Free Use Bible API
(`https://bible.helloao.org`) and only accepts the four configured commentary
IDs. It returns commentary text and source/license links; the browser renders
the text as plain text rather than inserting HTML.

Commentary coverage differs between authors. If a commentary has no entry for
the selected chapter, the new tab displays an availability message instead of
commentary text. Source and license links are shown with the loaded commentary.

## Giscus discussions

Giscus is embedded once in `templates/bible_reader.html` and configured with
`data-mapping="pathname"`. Because every chapter has its own page path (such
as `/GEN/1` and `/GEN/2`), Giscus receives a different pathname for each
chapter and associates each path with its own GitHub Discussion. Chapter
navigation performs a full page navigation so Giscus initializes with the new
pathname. Changing the selected verse does not change the pathname, so all
verses in one chapter share that chapter's discussion.

Giscus creates a discussion when a visitor first comments or reacts if it
cannot find one for the chapter pathname. Existing comments in another
discussion are not automatically moved.

## Errors

Unknown books or missing chapters return HTTP 404. If the catalog or chapter
request fails in the browser, the reader displays an error in its status area
and disables controls that cannot work without the chapter.
