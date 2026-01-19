from fastapi import APIRouter, UploadFile, File
from app.services.speech import speech_to_text, text_to_speech

router = APIRouter()

@router.post("/speech-to-text")
async def speech_to_text(file: UploadFile = File(...)):
    temp_filename = f"/tmp/{uuid.uuid4()}.ogg"

    with open(temp_filename, "wb") as f:
        f.write(await file.read())

    try:
        text = transcribe_audio_with_chunks(temp_filename)
        return {"text": text}
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

@router.post("/text-to-speech")
async def text_to_speech_endpoint(text: str):
    audio_bytes = await text_to_speech(text)
    return {
        "audio_base64": audio_bytes
    }