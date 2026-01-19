import os
import speech_recognition as sr
from pydub import AudioSegment


def speech_to_text(
    ogg_path: str,
    lang: str = "ru-RU",
    chunk_length_ms: int = 30000
) -> str:
    wav_path = ogg_path.replace(".ogg", ".wav")

    AudioSegment.from_file(ogg_path)\
        .set_channels(1)\
        .set_frame_rate(16000)\
        .export(wav_path, format="wav")

    audio = AudioSegment.from_wav(wav_path)
    recognizer = sr.Recognizer()
    full_text = ""

    for i, start_ms in enumerate(range(0, len(audio), chunk_length_ms)):
        chunk = audio[start_ms:start_ms + chunk_length_ms]
        chunk_file = f"{wav_path}_{i}.wav"
        chunk.export(chunk_file, format="wav")

        with sr.AudioFile(chunk_file) as source:
            audio_data = recognizer.record(source)

        try:
            part = recognizer.recognize_google(audio_data, language=lang)
            full_text += " " + part
        except sr.UnknownValueError:
            pass
        except sr.RequestError:
            pass

        os.remove(chunk_file)

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