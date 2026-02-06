import os

from urllib.parse import quote
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Header, Response

from app.services.speech import speech_to_text, text_to_speech_edge

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
        voice: str = Query("ru-RU-DmitryNeural", description="Голос"),
        # Теперь можно писать по-русски: "История о вампире.mp3"
        filename: str = Query("audio.mp3", description="Имя файла (можно на русском)"),
        x_token: str = Header(..., description="API Key")
):
    temp_path = None
    try:
        # 1. Генерируем
        temp_path = await text_to_speech_edge(text, voice)

        # 2. Читаем
        with open(temp_path, "rb") as f:
            audio_bytes = f.read()

        # 3. Удаляем
        os.remove(temp_path)
        temp_path = None

        # 4. Проверка расширения
        if not filename.endswith(".mp3"):
            filename += ".mp3"

        # 5. КОДИРОВАНИЕ ИМЕНИ ФАЙЛА (Магия для поддержки русского языка)
        # Мы превращаем "Привет.mp3" в "%D0%9F%D1%80%D0%B8%D0%B2%D0%B5%D1%82.mp3"
        encoded_filename = quote(filename)

        # 6. Формируем правильный заголовок
        # filename*=UTF-8''... — это стандарт, который понимают современные системы (включая n8n и браузеры)
        content_disposition = f"attachment; filename*=UTF-8''{encoded_filename}"

        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": content_disposition}
        )

    except Exception as e:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")
