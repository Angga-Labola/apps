from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests
from encryption import encrypt_string
from decryption import decrypt_string
from sokoban_router import router as sokoban_router
from bible_router import bible_router

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
# Feature routers keep the Bible reader and Sokoban APIs separate from the
# general application routes while sharing this FastAPI app and static mount.
app.include_router(sokoban_router)
app.include_router(bible_router)



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
