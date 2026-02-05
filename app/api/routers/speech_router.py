import os

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Header, Response

from app.services.speech import speech_to_text
from app.services.audio_ai import text_to_speech_edge

router = APIRouter()

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

    # Читаем байты один раз здесь
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        # Просто передаем байты и имя файла в сервис
        text = await speech_to_text(contents, file.filename)

        return {
            "status": "success",
            "filename": file.filename,
            "text": text
        }
    except Exception as e:
        # Любая ошибка внутри сервиса вернется сюда
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


# ----------------------------
# Text-to-Speech (Edge TTS)
# ----------------------------
@router.post("/text-to-speech", summary="Синтез речи (Edge TTS - High Quality)")
async def text_to_speech_endpoint(
        text: str = Query(..., description="Текст для озвучки"),
        voice: str = Query("ru-RU-DmitryNeural", description="ru-RU-DmitryNeural или ru-RU-SvetlanaNeural"),
        x_token: str = Header(..., description="API Key")
):
    try:
        # Edge TTS - это асинхронная библиотека, await работает нативно
        # Генерируем файл
        output_path = await text_to_speech_edge(text, voice)

        # Читаем его в память
        with open(output_path, "rb") as f:
            audio_bytes = f.read()

        # Удаляем файл с диска
        os.remove(output_path)

        # Отдаем как файл
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",  # Edge TTS выдает mp3
            headers={"Content-Disposition": "attachment; filename=voice.mp3"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")

