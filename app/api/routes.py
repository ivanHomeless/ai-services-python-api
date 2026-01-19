import os
import uuid
import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.speech import transcribe_audio_with_chunks

router = APIRouter()
TMP_DIR = "/tmp"

@router.post("/speech-to-text")
async def speech_to_text(file: UploadFile = File(...)):
    if not file or file.filename == "":
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Создаём уникальный временный файл
    #temp_filename = f"{TMP_DIR}/{uuid.uuid4()}_{file.filename}"
    temp_filename = f"{TMP_DIR}/{uuid.uuid4()}.ogg"
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    with open(temp_filename, "wb") as f:
        f.write(contents)

    try:
        text = await asyncio.to_thread(transcribe_audio_with_chunks, temp_filename)
        return {
            "saved_as": temp_filename,
            "size_bytes": len(contents),
            "text": text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during transcription: {e}")
    finally:
        try:
            os.remove(temp_filename)
        except OSError:
            pass

@router.post("/text-to-speech")
async def text_to_speech_endpoint(text: str):
    audio_bytes = await text_to_speech(text)
    return {
        "audio_base64": audio_bytes
    }
