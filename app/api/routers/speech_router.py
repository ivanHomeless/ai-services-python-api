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
        filename: str = Query("audio.mp3", description="Имя файла для Telegram"),
        voice: str = Query("ru-RU-DmitryNeural", description="ru-RU-DmitryNeural или ru-RU-SvetlanaNeural"),
        x_token: str = Header(..., description="API Key")
):
    temp_path = None
    try:
        # 1. Генерируем файл (сервис вернет путь к temp_....mp3)
        temp_path = await text_to_speech_edge(text, voice)

        # 2. Читаем байты в оперативную память
        with open(temp_path, "rb") as f:
            audio_bytes = f.read()

        # 3. УДАЛЯЕМ временный файл (Clean up)
        # Мы уже считали байты, файл на диске больше не нужен
        os.remove(temp_path)
        temp_path = None

        # 4. Проверяем, есть ли .mp3 в конце имени, если нет - добавляем
        if not filename.endswith(".mp3"):
            filename += ".mp3"

        # 5. Отдаем ответ с правильным заголовком
        # Именно здесь задается то имя, которое увидит Telegram!
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        # Если упала ошибка, но файл успел создаться - удаляем его, чтобы не мусорить
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")

