from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from encryption import encrypt_string
from decryption import decrypt_string



app = FastAPI()
app.mount("/static",StaticFiles(directory="static"), name="static")

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

@app.get("/bible")
def bible_home():
    return FileResponse("templates/bible_reader.html")


@app.get("/api/bible/books")
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

@app.get("/{book_id}/{chapter_id}")
def read_page(book_id:str,chapter_id:str):
    if book_id not in BOOK_NAMES or not chapter_id.isdigit():
        raise HTTPException(status_code=404, detail="Bible chapter not found")
    chapter_path = Path("templates/bible") / book_id / f"{book_id}_{chapter_id}.html"
    if not chapter_path.is_file():
        raise HTTPException(status_code=404, detail="Bible chapter not found")
    return FileResponse("templates/bible_reader.html")


@app.get("/api/bible/{book_id}/{chapter_id}")
def bible_chapter(book_id:str,chapter_id:str):
    if book_id not in BOOK_NAMES or not chapter_id.isdigit():
        raise HTTPException(status_code=404, detail="Bible chapter not found")
    chapter_path = Path("templates/bible") / book_id / f"{book_id}_{chapter_id}.html"
    if not chapter_path.is_file():
        raise HTTPException(status_code=404, detail="Bible chapter not found")
    return FileResponse(chapter_path)


class encryption_payload(BaseModel):
    plain_text:str

class decryption_payload(BaseModel):
    ciphertext:str

@app.get("/encryption")
def home():
    return FileResponse("templates/encryption.html")

@app.post("/encryption")
def encryption(payload:encryption_payload):
    post=payload.plain_text
    response = encrypt_string(post)
    return response   

@app.get("/decryption")
def home():
    return FileResponse("templates/decryption.html")

@app.post("/decryption")
def decryption(payload:decryption_payload):
    post=payload.ciphertext
    response = decrypt_string(post)
    return response   


if __name__=="__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0",port=8000)

