import json
import os
import re
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests
from vercel.blob import BlobCredentialsError, BlobError, BlobNotFoundError
from vercel.blob import sync as vercel_blob
from encryption import encrypt_string
from decryption import decrypt_string


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = FastAPI()
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

SOKOBAN_COLLECTION_ID = os.getenv("SOKOBAN_COLLECTION_ID", "550")
LETSLOGIC_API_URL = "https://letslogic.com/api/v1"
VERCEL_BLOB_COLLECTIONS_PREFIX = "sokoban-collections/"
SOKOBAN_COLLECTIONS_DIR = Path(
    os.getenv(
        "SOKOBAN_COLLECTIONS_DIR",
        BASE_DIR / "data" / "sokoban" / "collections",
    )
)


@app.get("/sokoban")
def sokoban_home():
    return FileResponse(BASE_DIR / "templates" / "sokoban.html")


@app.get("/api/sokoban/health")
def sokoban_health():
    return {"status": "ok", "letslogic_configured": bool(os.getenv("SOKOBAN_KEY"))}


def post_to_letslogic(endpoint: str) -> object:
    api_key = os.getenv("SOKOBAN_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="LetsLogic is not configured. Set the SOKOBAN_KEY environment variable.",
        )

    try:
        response = requests.post(
            f"{LETSLOGIC_API_URL}/{endpoint}",
            data={"key": api_key},
            timeout=8,
        )
    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail="The LetsLogic service could not be reached.",
        ) from error

    if not response.ok:
        raise HTTPException(
            status_code=502,
            detail="The LetsLogic service returned an error.",
        )

    try:
        payload = response.json()
    except ValueError as error:
        raise HTTPException(
            status_code=502,
            detail="The LetsLogic service returned invalid JSON.",
        ) from error

    return payload


def fetch_sokoban_collections() -> list[object]:
    collections = post_to_letslogic("collections")
    if isinstance(collections, dict) and isinstance(collections.get("collections"), list):
        collections = collections["collections"]
    if not isinstance(collections, list):
        raise HTTPException(
            status_code=502,
            detail="The LetsLogic service returned an unexpected collection list.",
        )
    return collections


def fetch_sokoban_levels(collection_id: str = SOKOBAN_COLLECTION_ID) -> list[object]:
    levels = post_to_letslogic(f"collection/{collection_id}")
    if isinstance(levels, dict) and isinstance(levels.get("levels"), list):
        levels = levels["levels"]
    if not isinstance(levels, list):
        raise HTTPException(
            status_code=502,
            detail="The LetsLogic service returned an unexpected level collection.",
        )
    return levels


def collection_id_from_entry(collection: object) -> str | None:
    if isinstance(collection, dict):
        value = (
            collection.get("collection_id")
            or collection.get("collectionId")
            or collection.get("id")
        )
    elif isinstance(collection, (int, str)):
        value = collection
    else:
        return None

    identifier = str(value) if value is not None else ""
    return identifier if re.fullmatch(r"\d{1,12}", identifier) else None


def collection_name(collection: object, collection_id: str) -> str:
    if isinstance(collection, dict):
        for field in ("name", "title", "collection_name"):
            value = collection.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return f"Collection {collection_id}"


def collection_text(collection: object, field: str) -> str:
    if isinstance(collection, dict):
        value = collection.get(field)
        if isinstance(value, str):
            return value.strip()
    return ""


def saved_collections_directory() -> Path:
    try:
        SOKOBAN_COLLECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="The Sokoban collections folder could not be created.",
        ) from error
    return SOKOBAN_COLLECTIONS_DIR


def uses_vercel_blob() -> bool:
    return bool(os.getenv("VERCEL"))


def vercel_collection_path(collection_id: str) -> str:
    return f"{VERCEL_BLOB_COLLECTIONS_PREFIX}{collection_id}.json"


def read_vercel_collection(collection_id: str) -> dict[str, object]:
    try:
        result = vercel_blob.get_blob(
            vercel_collection_path(collection_id),
            access="public",
        )
    except BlobNotFoundError as error:
        raise HTTPException(status_code=404, detail="Saved collection not found.") from error
    except BlobCredentialsError as error:
        raise HTTPException(
            status_code=503,
            detail="Vercel Blob is not configured for this deployment.",
        ) from error
    except BlobError as error:
        raise HTTPException(
            status_code=502,
            detail="The saved collection could not be read from Vercel Blob.",
        ) from error

    try:
        collection = json.loads(result.body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=500,
            detail="The saved collection file is invalid.",
        ) from error
    if not isinstance(collection, dict) or not isinstance(collection.get("levels"), list):
        raise HTTPException(status_code=500, detail="The saved collection file is invalid.")
    return collection


@app.get("/api/sokoban/collections")
def sokoban_collections():
    collections = []
    for collection in fetch_sokoban_collections():
        identifier = collection_id_from_entry(collection)
        if identifier is None:
            continue
        entry = {
            "id": identifier,
            "name": collection_name(collection, identifier),
            "description": collection_text(collection, "description"),
            "author": collection_text(collection, "author"),
        }
        if isinstance(collection, dict):
            for field in ("level_count", "count", "levels"):
                value = collection.get(field)
                if field == "levels" and isinstance(value, list):
                    entry["level_count"] = len(value)
                    break
                if field != "levels" and isinstance(value, (int, str)):
                    entry["level_count"] = value
                    break
        collections.append(entry)
    return {"collections": collections}


class CollectionDownloadRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    author: str | None = None


@app.post("/api/sokoban/collections/{collection_id}/download")
def save_sokoban_collection(
    collection_id: str,
    payload: CollectionDownloadRequest | None = None,
):
    if not re.fullmatch(r"\d{1,12}", collection_id):
        raise HTTPException(status_code=400, detail="Invalid LetsLogic collection ID.")

    levels = fetch_sokoban_levels(collection_id)
    collection = {
        "collection_id": collection_id,
        "name": collection_name(
            {"name": payload.name} if payload and payload.name else {},
            collection_id,
        ),
        "description": payload.description.strip() if payload and payload.description else "",
        "author": payload.author.strip() if payload and payload.author else "",
        "levels": levels,
    }
    if uses_vercel_blob():
        pathname = vercel_collection_path(collection_id)
        try:
            result = vercel_blob.put_blob(
                pathname,
                json.dumps(collection, ensure_ascii=False, indent=2).encode("utf-8"),
                access="public",
                content_type="application/json",
                allow_overwrite=True,
            )
        except BlobCredentialsError as error:
            raise HTTPException(
                status_code=503,
                detail="Vercel Blob is not configured for this deployment.",
            ) from error
        except BlobError as error:
            raise HTTPException(
                status_code=502,
                detail="The downloaded collection could not be saved to Vercel Blob.",
            ) from error
        return {
            **collection,
            "saved_file": result.pathname,
            "storage": "vercel_blob",
        }

    destination = saved_collections_directory() / f"{collection_id}.json"
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{collection_id}-",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(collection, temporary_file, ensure_ascii=False, indent=2)
        temporary_path.replace(destination)
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="The downloaded collection could not be saved.",
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return {
        **collection,
        "saved_file": destination.name,
        "storage": "local",
    }


@app.get("/api/sokoban/saved-collections")
def list_saved_sokoban_collections():
    if uses_vercel_blob():
        try:
            files = vercel_blob.query_blobs(prefix=VERCEL_BLOB_COLLECTIONS_PREFIX)
            collections = []
            for file in files:
                match = re.fullmatch(
                    rf"{re.escape(VERCEL_BLOB_COLLECTIONS_PREFIX)}(\d{{1,12}})\.json",
                    file.pathname,
                )
                if match is None:
                    continue
                collection_id = match.group(1)
                collection = read_vercel_collection(collection_id)
                collections.append({
                    "collection_id": collection_id,
                    "name": collection_name(collection, collection_id),
                    "description": collection_text(collection, "description"),
                    "author": collection_text(collection, "author"),
                    "level_count": len(collection["levels"]),
                })
        except BlobCredentialsError as error:
            raise HTTPException(
                status_code=503,
                detail="Vercel Blob is not configured for this deployment.",
            ) from error
        except BlobError as error:
            raise HTTPException(
                status_code=502,
                detail="Saved Sokoban collections could not be listed from Vercel Blob.",
            ) from error
        return {"collections": collections, "storage": "vercel_blob"}

    directory = saved_collections_directory()
    try:
        files = sorted(directory.glob("*.json"), key=lambda file: file.name)
        collections = []
        for file in files:
            collection_id = file.stem
            if not re.fullmatch(r"\d{1,12}", collection_id):
                continue
            collection = json.loads(file.read_text(encoding="utf-8"))
            if isinstance(collection, dict) and isinstance(collection.get("levels"), list):
                collections.append({
                    "collection_id": collection_id,
                    "name": collection_name(collection, collection_id),
                    "description": collection_text(collection, "description"),
                    "author": collection_text(collection, "author"),
                    "level_count": len(collection["levels"]),
                })
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=500,
            detail="Saved Sokoban collections could not be read.",
        ) from error

    return {
        "collections": collections,
        "storage": "local",
    }


@app.get("/api/sokoban/saved-collections/{collection_id}")
def get_saved_sokoban_collection(collection_id: str):
    if not re.fullmatch(r"\d{1,12}", collection_id):
        raise HTTPException(status_code=400, detail="Invalid collection ID.")
    if uses_vercel_blob():
        return read_vercel_collection(collection_id)

    path = SOKOBAN_COLLECTIONS_DIR / f"{collection_id}.json"
    try:
        collection = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Saved collection not found.") from error
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=500,
            detail="The saved collection could not be read.",
        ) from error
    if not isinstance(collection, dict) or not isinstance(collection.get("levels"), list):
        raise HTTPException(status_code=500, detail="The saved collection file is invalid.")
    return collection


@app.delete("/api/sokoban/saved-collections/{collection_id}")
def delete_saved_sokoban_collection(collection_id: str):
    if not re.fullmatch(r"\d{1,12}", collection_id):
        raise HTTPException(status_code=400, detail="Invalid collection ID.")

    if uses_vercel_blob():
        try:
            vercel_blob.delete_blob(vercel_collection_path(collection_id))
        except BlobCredentialsError as error:
            raise HTTPException(
                status_code=503,
                detail="Vercel Blob is not configured for this deployment.",
            ) from error
        except BlobError as error:
            raise HTTPException(
                status_code=502,
                detail="The saved collection could not be deleted from Vercel Blob.",
            ) from error
        return {"deleted": collection_id, "storage": "vercel_blob"}

    path = SOKOBAN_COLLECTIONS_DIR / f"{collection_id}.json"
    try:
        path.unlink()
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Saved collection not found.") from error
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="The saved collection could not be deleted.",
        ) from error
    return {"deleted": collection_id, "storage": "local"}


@app.get("/api/sokoban/levels")
def sokoban_levels():
    return {
        "collection_id": SOKOBAN_COLLECTION_ID,
        "levels": fetch_sokoban_levels(),
    }


@app.get("/api/sokoban/levels/download")
def download_sokoban_collection():
    collection = {
        "collection_id": SOKOBAN_COLLECTION_ID,
        "levels": fetch_sokoban_levels(),
    }
    return Response(
        content=json.dumps(collection, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f'attachment; filename="letslogic-collection-{SOKOBAN_COLLECTION_ID}.json"'
            )
        },
    )

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


@app.get("/api/bible/commentary/{commentary_id}/{book_id}/{chapter_id}")
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


@app.get("/commentary/{commentary_id}/{book_id}/{chapter_id}")
def commentary_page(commentary_id:str,book_id:str,chapter_id:str):
    if commentary_id not in COMMENTARIES:
        raise HTTPException(status_code=404, detail="Commentary not found")
    if book_id not in BOOK_NAMES or not chapter_id.isdigit():
        raise HTTPException(status_code=404, detail="Bible chapter not found")

    chapter_path = Path("templates/bible") / book_id / f"{book_id}_{chapter_id}.html"
    if not chapter_path.is_file():
        raise HTTPException(status_code=404, detail="Bible chapter not found")
    return FileResponse("templates/commentary_reader.html")


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
