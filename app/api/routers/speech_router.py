import asyncio
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Header, Response
from app.services.speech import speech_to_text, text_to_speech

router = APIRouter()
TMP_DIR = "/tmp"

# Голоса
VOICES = {
    "Karina2:master": "Женский русский голос",
    "Alex2:master": "Мужской русский голос",
    "Anna:master": "Женский русский голос",
    "Oleg:master": "Мужской русский голос",
    "en_female:dev": "Женский английский голос",
    "en_male:dev": "Мужской английский голос"
}

# ----------------------------
# Speech-to-Text
# ----------------------------
@router.post("/speech-to-text", summary="Распознавание речи из файла")
async def speech_to_text_endpoint(
    file: UploadFile = File(...),
    x_token: str = Header(..., description="JWT токен авторизации")
):
    if not file or file.filename == "":
        raise HTTPException(status_code=400, detail="No file uploaded")

    temp_filename = f"{TMP_DIR}/{uuid.uuid4()}_{file.filename}"

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
            import os
            os.remove(temp_filename)
        except OSError:
            pass

# ----------------------------
# Text-to-Speech
# ----------------------------
@router.post("/text-to-speech", summary="Синтез речи из текста")
async def text_to_speech_endpoint(
        text: str = Query(..., description="Текст для синтеза речи"),
        voice_name: str = Query("Oleg:master", description="Голос для синтеза"),
        x_token: str = Header(..., description="JWT токен авторизации")
):
    if voice_name not in VOICES:
        raise HTTPException(status_code=400, detail=f"Unsupported voice_name.")

    try:
        # Получаем байты из сервиса
        audio_bytes = await text_to_speech(text, voice_name)

        # Отправляем как файл. n8n подхватит это как Binary Data
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=speech.wav"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")


# @router.post("/text-to-speech", summary="Синтез речи из текста")
# async def text_to_speech_endpoint(
#     text: str = Query(..., description="Текст для синтеза речи"),
#     voice_name: str = Query(
#         "Oleg:master",
#         description="Голос для синтеза. Возможные варианты: " + ", ".join(f"{k} ({v})" for k,v in VOICES.items())
#     ),
#     x_token: str = Header(..., description="JWT токен авторизации")
# ):
#     if voice_name not in VOICES:
#         raise HTTPException(status_code=400, detail=f"Unsupported voice_name. Supported: {list(VOICES.keys())}")
#
#     try:
#         audio_bytes = await text_to_speech(text, voice_name)
#         import base64
#         return {"audio_base64": base64.b64encode(audio_bytes).decode(), "voice_used": voice_name}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"TTS error: {e}")