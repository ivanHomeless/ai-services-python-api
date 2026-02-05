import os
import time
import shutil
from gradio_client import Client
from fastapi import HTTPException

# Настройки
SPACE_URL = "https://playgroundai-playground-v2-5.hf.space/"
MAX_WAIT_TIME = 600  # 10 минут ожидания (для n8n хватит)
RETRY_DELAY = 10  # Пауза между попытками


def generate_image_sync(prompt: str, negative_prompt: str, width: int, height: int) -> bytes:
    """
    Синхронная функция генерации.
    FastAPI запустит её в отдельном потоке, чтобы не блокировать сервер.
    """
    start_time = time.time()
    attempt = 1

    # Временное имя файла для сохранения результата gradio
    temp_filename = f"temp_{int(time.time())}.png"

    print(f"[Image Gen] Start: {prompt[:50]}...")

    while True:
        elapsed = time.time() - start_time
        if elapsed > MAX_WAIT_TIME:
            raise TimeoutError("Превышено время ожидания генерации")

        try:
            # Пересоздаем клиент каждый раз для надежности соединения
            client = Client(SPACE_URL)

            # Параметры конкретно для Playground v2.5
            result = client.predict(
                prompt,  # prompt
                negative_prompt,  # negative_prompt
                True,  # use_negative_prompt
                0,  # seed
                width,  # width
                height,  # height
                3,  # guidance_scale
                True,  # randomize_seed
                api_name="/run"
            )

            # Разбор ответа (Gallery format)
            image_path = None
            if result and isinstance(result, (list, tuple)):
                try:
                    # Пытаемся достать путь (обычно result[0][0]['image'])
                    image_path = result[0][0]['image']
                except (KeyError, IndexError, TypeError):
                    # Запасной вариант
                    if isinstance(result[0], str):
                        image_path = result[0]

            if image_path and os.path.exists(image_path):
                # Читаем файл в память
                with open(image_path, "rb") as img_file:
                    image_bytes = img_file.read()

                # Удаляем временный файл, который создал Gradio
                try:
                    os.remove(image_path)
                except:
                    pass

                print(f"[Image Gen] Success on attempt {attempt}")
                return image_bytes

        except Exception as e:
            print(f"[Image Gen] Attempt {attempt} failed: {e}. Retrying...")

        # Ждем перед следующей попыткой
        time.sleep(RETRY_DELAY)
        attempt += 1