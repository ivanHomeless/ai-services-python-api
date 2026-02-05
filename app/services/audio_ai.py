import edge_tts
import time
from gradio_client import Client


# --- НАСТРОЙКИ ---
WHISPER_SPACE = "hf-audio/whisper-large-v3-turbo"

# Настройки надежности для Whisper
MAX_WAIT_TIME = 600  # 10 минут (хватит даже для длинных видео)
RETRY_DELAY = 10  # Пауза между попытками


async def text_to_speech_edge(text: str, voice: str = "ru-RU-DmitryNeural") -> str:
    """
    Генерирует речь через Microsoft Edge TTS.
    Здесь цикл не нужен, API отвечает мгновенно.
    """
    try:
        communicate = edge_tts.Communicate(text, voice)
        output_path = f"temp_tts_{int(time.time())}.mp3"
        await communicate.save(output_path)
        return output_path
    except Exception as e:
        # Если Microsoft недоступен, пробрасываем ошибку сразу
        raise RuntimeError(f"EdgeTTS failed: {e}")


def speech_to_text_whisper(filepath: str) -> str:
    """
    Распознает речь через Whisper с защитой от падений и очередей.
    """
    start_time = time.time()
    attempt = 1

    print(f"[Whisper] Start recognizing: {filepath}...")

    while True:
        elapsed = time.time() - start_time
        if elapsed > MAX_WAIT_TIME:
            raise TimeoutError("Whisper: Превышено время ожидания очереди.")

        try:
            # 1. Подключение (каждый раз новое, чтобы избежать протухших сессий)
            client = Client(WHISPER_SPACE)

            # 2. Отправка (predict сам ждет очереди, но может упасть по таймауту сети)
            result = client.predict(
                filepath,  # путь к файлу
                "transcribe",  # задача
                api_name="/predict"
            )

            # Результат Whisper Space - это просто строка текста
            if result and isinstance(result, str):
                print(f"[Whisper] Success on attempt {attempt}")
                return result
            else:
                print(f"[Whisper] Пустой или странный ответ: {result}")

        except Exception as e:
            # Ловим всё: перегрузку, разрыв сети, ошибки API
            print(f"[Whisper] Attempt {attempt} failed: {e}. Retrying...")

        # Ждем и пробуем снова
        time.sleep(RETRY_DELAY)
        attempt += 1