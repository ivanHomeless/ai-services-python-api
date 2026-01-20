import os
import uuid
import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from app.services.speech import speech_to_text, text_to_speech

router = APIRouter()
TMP_DIR = "/tmp"

@router.post("/speech-to-text")
async def speech_to_text_endpoint(file: UploadFile = File(...)):
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
        text = await asyncio.to_thread(speech_to_text, temp_filename)
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
async def text_to_speech_endpoint(
    text: str,
    voice_name: str = Query("Oleg:master", description="Voice to use for TTS ")
):
    if not text:
        raise HTTPException(status_code=400, detail="Text is empty")
    try:
        # Передаём голос в функцию
        audio_base64 = await text_to_speech(text, voice_name)
        return {"audio_base64": audio_base64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {e}")
