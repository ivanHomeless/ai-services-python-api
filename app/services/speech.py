import os
import speech_recognition as sr
from pydub import AudioSegment

# Словарь поддерживаемых форматов
SUPPORTED_FORMATS = {
    "wav": "wav",
    "mp3": "mp3",
    "ogg": "ogg",
    "oga": "ogg",  # oga — это Ogg контейнер с Opus
}

def transcribe_audio_with_chunks(
    file_path: str,
    lang: str = "ru-RU",
    chunk_length_ms: int = 30000
) -> str:
    # Определяем формат по расширению
    ext = file_path.split(".")[-1].lower()
    format_for_pydub = SUPPORTED_FORMATS.get(ext)
    if not format_for_pydub:
        raise ValueError(f"Unsupported audio format: {ext}")

    wav_path = f"{file_path}.wav"

    try:
        # Конвертируем в WAV
        audio_segment = AudioSegment.from_file(file_path, format=format_for_pydub)\
                                   .set_channels(1)\
                                   .set_frame_rate(16000)
        audio_segment.export(wav_path, format="wav")
    except Exception as e:
        raise RuntimeError(f"Failed to convert audio to WAV: {e}")

    recognizer = sr.Recognizer()
    audio = AudioSegment.from_wav(wav_path)
    full_text = ""

    for i, start_ms in enumerate(range(0, len(audio), chunk_length_ms)):
        chunk = audio[start_ms:start_ms + chunk_length_ms]
        chunk_file = f"{wav_path}_{i}.wav"

        try:
            chunk.export(chunk_file, format="wav")
            with sr.AudioFile(chunk_file) as source:
                audio_data = recognizer.record(source)
            try:
                part = recognizer.recognize_google(audio_data, language=lang)
                full_text += " " + part
            except sr.UnknownValueError:
                full_text += " [неразборчиво] "
            except sr.RequestError as e:
                full_text += f" [ошибка сервиса: {e}] "
        finally:
            # Удаляем chunk файл
            if os.path.exists(chunk_file):
                os.remove(chunk_file)

    # Удаляем WAV файл после обработки
    if os.path.exists(wav_path):
        os.remove(wav_path)

    return full_text.strip()




async def text_to_speech(text: str):
    """
    1. Получить текст
    2. Отправить в TTS
    3. Получить аудиобайты
    4. Вернуть bytes / base64
    """
    audio_bytes = b"..."
    return audio_bytes