import json
import os
import re
import tempfile
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
import requests
from vercel.blob import BlobCredentialsError, BlobError, BlobNotFoundError
from vercel.blob import sync as vercel_blob

from sokoban_solver import find_sokoban_solution, solve_sokoban_level


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

router = APIRouter()

SOKOBAN_COLLECTION_ID = os.getenv("SOKOBAN_COLLECTION_ID", "550")
LETSLOGIC_API_URL = "https://letslogic.com/api/v1"
VERCEL_BLOB_COLLECTIONS_PREFIX = "sokoban-collections/"
SOKOBAN_COLLECTIONS_DIR = Path(
    os.getenv(
        "SOKOBAN_COLLECTIONS_DIR",
        BASE_DIR / "data" / "sokoban" / "collections",
    )
)


@router.get("/sokoban")
def sokoban_home():
    return FileResponse(BASE_DIR / "templates" / "sokoban.html")

@router.get("/api/sokoban/health")
def sokoban_health():
    return {"status": "ok", "letslogic_configured": bool(os.getenv("SOKOBAN_KEY"))}

@router.get("/sokoban/import_collections")
def sokoban_import_collections():
    return FileResponse(BASE_DIR / "templates" / "sokoban_import.html")

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


def vercel_blob_access() -> Literal["public", "private"]:
    access = os.getenv("SOKOBAN_BLOB_ACCESS", "public").strip().lower()
    if access not in {"public", "private"}:
        raise HTTPException(
            status_code=500,
            detail="SOKOBAN_BLOB_ACCESS must be either 'public' or 'private'.",
        )
    return access


def vercel_blob_error_detail(action: str, error: BlobError) -> str:
    status = error.status_code if error.status_code is not None else "unknown status"
    code = error.code or "unknown error"
    return f"Vercel Blob {action} failed ({status}, {code}): {error}"


def read_vercel_collection(collection_id: str) -> dict[str, object]:
    try:
        result = vercel_blob.get_blob(
            vercel_collection_path(collection_id),
            access=vercel_blob_access(),
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
            detail=vercel_blob_error_detail("read", error),
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


@router.get("/api/sokoban/collections")
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


@router.post("/api/sokoban/collections/{collection_id}/download")
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
                access=vercel_blob_access(),
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
                detail=vercel_blob_error_detail("upload", error),
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


@router.get("/api/sokoban/saved-collections")
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
                detail=vercel_blob_error_detail("list", error),
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


@router.get("/api/sokoban/saved-collections/{collection_id}")
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


@router.get(
    "/api/sokoban/saved-collections/{collection_id}/levels/{level_index}/solve"
)
def solve_saved_sokoban_level(
    collection_id: str,
    level_index: int,
    show_solution: bool = False,
):
    collection = get_saved_sokoban_collection(collection_id)
    if level_index < 0 or level_index >= len(collection["levels"]):
        raise HTTPException(status_code=404, detail="Saved level not found.")

    level = collection["levels"][level_index]
    if show_solution:
        status, solution = find_sokoban_solution(level)
    else:
        status, solution = solve_sokoban_level(level), None
    return {
        "status": status,
        "solution": solution,
    }


@router.delete("/api/sokoban/saved-collections/{collection_id}")
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


@router.get("/api/sokoban/levels")
def sokoban_levels():
    return {
        "collection_id": SOKOBAN_COLLECTION_ID,
        "levels": fetch_sokoban_levels(),
    }


@router.get("/api/sokoban/levels/download")
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