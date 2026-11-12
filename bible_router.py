from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests

bible_router=APIRouter()

BOOK_NAMES = {
    "GEN": "Genesis", "EXO": "Exodus", "LEV": "Leviticus", "NUM": "Numbers",
    "DEU": "Deuteronomy", "JOS": "Joshua", "JDG": "Judges", "RUT": "Ruth",
    "1SA": "1 Samuel", "2SA": "2 Samuel", "1KI": "1 Kings", "2KI": "2 Kings",
    "1CH": "1 Chronicles", "2CH": "2 Chronicles", "EZR": "Ezra", "NEH": "Nehemiah",
    "EST": "Esther", "JOB": "Job", "PSA": "Psalms", "PRO": "Proverbs",
    "ECC": "Ecclesiastes", "SNG": "Song of Solomon", "ISA": "Isaiah", "JER": "Jeremiah",
    "LAM": "Lamentations", "EZK": "Ezekiel", "DAN": "Daniel", "HOS": "Hosea",
    "JOL": "Joel", "AMO": "Amos", "OBA": "Obadiah", "JON": "Jonah",
    "MIC": "Micah", "NAM": "Nahum", "HAB": "Habakkuk", "ZEP": "Zephaniah",
    "HAG": "Haggai", "ZEC": "Zechariah", "MAL": "Malachi", "MAT": "Matthew",
    "MRK": "Mark", "LUK": "Luke", "JHN": "John", "ACT": "Acts",
    "ROM": "Romans", "1CO": "1 Corinthians", "2CO": "2 Corinthians",
    "GAL": "Galatians", "EPH": "Ephesians", "PHP": "Philippians",
    "COL": "Colossians", "1TH": "1 Thessalonians", "2TH": "2 Thessalonians",
    "1TI": "1 Timothy", "2TI": "2 Timothy", "TIT": "Titus", "PHM": "Philemon",
    "HEB": "Hebrews", "JAS": "James", "1PE": "1 Peter", "2PE": "2 Peter",
    "1JN": "1 John", "2JN": "2 John", "3JN": "3 John", "JUD": "Jude",
    "REV": "Revelation",
}

COMMENTARIES = {
    "john-calvin": "John Calvin",
    "john-gill": "John Gill",
    "matthew-henry": "Matthew Henry",
    "jamieson-fausset-brown": "Jamieson-Fausset-Brown",
}

@bible_router.get("/bible")
def bible_home():
    return FileResponse("templates/bible_reader.html")


@bible_router.get("/api/bible/books")
def bible_books():
    bible_dir = Path("templates/bible")
    books = []
    for book_id, name in BOOK_NAMES.items():
        book_dir = bible_dir / book_id
        chapters = sorted(
            int(path.stem.removeprefix(f"{book_id}_"))
            for path in book_dir.glob(f"{book_id}_*.html")
            if path.stem.removeprefix(f"{book_id}_").isdigit()
        )
        if chapters:
            books.append({"id": book_id, "name": name, "chapters": chapters})
    return {"books": books}

@bible_router.get("/{book_id}/{chapter_id}")
def read_page(book_id:str,chapter_id:str):
    if book_id not in BOOK_NAMES or not chapter_id.isdigit():
        raise HTTPException(status_code=404, detail="Bible chapter not found")
    chapter_path = Path("templates/bible") / book_id / f"{book_id}_{chapter_id}.html"
    if not chapter_path.is_file():
        raise HTTPException(status_code=404, detail="Bible chapter not found")
    return FileResponse("templates/bible_reader.html")


@bible_router.get("/api/bible/{book_id}/{chapter_id}")
def bible_chapter(book_id:str,chapter_id:str):
    if book_id not in BOOK_NAMES or not chapter_id.isdigit():
        raise HTTPException(status_code=404, detail="Bible chapter not found")
    chapter_path = Path("templates/bible") / book_id / f"{book_id}_{chapter_id}.html"
    if not chapter_path.is_file():
        raise HTTPException(status_code=404, detail="Bible chapter not found")
    return FileResponse(chapter_path)


@bible_router.get("/api/bible/commentary/{commentary_id}/{book_id}/{chapter_id}")
def bible_commentary(commentary_id:str,book_id:str,chapter_id:str):
    if commentary_id not in COMMENTARIES:
        raise HTTPException(status_code=404, detail="Commentary not found")
    if book_id not in BOOK_NAMES or not chapter_id.isdigit():
        raise HTTPException(status_code=404, detail="Bible chapter not found")

    chapter_path = Path("templates/bible") / book_id / f"{book_id}_{chapter_id}.html"
    if not chapter_path.is_file():
        raise HTTPException(status_code=404, detail="Bible chapter not found")

    try:
        response = requests.get(
            f"https://bible.helloao.org/api/c/{commentary_id}/{book_id}/{int(chapter_id)}.json",
            timeout=15,
        )
    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail="The commentary service could not be reached",
        ) from error

    if response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail="This commentary is not available for the selected chapter",
        )
    if not response.ok:
        raise HTTPException(
            status_code=502,
            detail="The commentary service returned an error",
        )

    try:
        data = response.json()
    except ValueError as error:
        raise HTTPException(
            status_code=502,
            detail="The commentary service returned invalid data",
        ) from error

    chapter = data.get("chapter") if isinstance(data, dict) else None
    commentary = data.get("commentary") if isinstance(data, dict) else None
    if not isinstance(chapter, dict) or not isinstance(chapter.get("content"), list):
        raise HTTPException(
            status_code=502,
            detail="The commentary service returned an unexpected response",
        )

    return {
        "commentary_id": commentary_id,
        "commentary_name": commentary.get("name", COMMENTARIES[commentary_id])
        if isinstance(commentary, dict)
        else COMMENTARIES[commentary_id],
        "website": commentary.get("website") if isinstance(commentary, dict) else None,
        "license_url": commentary.get("licenseUrl") if isinstance(commentary, dict) else None,
        "book": BOOK_NAMES[book_id],
        "chapter": chapter,
    }


@bible_router.get("/commentary/{commentary_id}/{book_id}/{chapter_id}")
def commentary_page(commentary_id:str,book_id:str,chapter_id:str):
    if commentary_id not in COMMENTARIES:
        raise HTTPException(status_code=404, detail="Commentary not found")
    if book_id not in BOOK_NAMES or not chapter_id.isdigit():
        raise HTTPException(status_code=404, detail="Bible chapter not found")

    chapter_path = Path("templates/bible") / book_id / f"{book_id}_{chapter_id}.html"
    if not chapter_path.is_file():
        raise HTTPException(status_code=404, detail="Bible chapter not found")
    return FileResponse("templates/commentary_reader.html")
