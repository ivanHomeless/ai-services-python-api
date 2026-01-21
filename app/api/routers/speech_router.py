from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Header, Response
from app.services.speech import speech_to_text, text_to_speech
from app.services.speech import VOICES

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
# Text-to-Speech
# ----------------------------
@router.post("/text-to-speech", summary="Синтез речи из текста")
async def text_to_speech_endpoint(
        text: str = Query(..., description="Текст для синтеза речи"),
        voice_name: str = Query("Oleg:master", description=f"Доступные: {', '.join(VOICES.keys())}"),
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


