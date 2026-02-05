import os
import time

from gradio_client import Client
from gradio_client.utils import TooManyRequestsError


# Настройки
SPACE_URL = "https://playgroundai-playground-v2-5.hf.space/"
MAX_WAIT_TIME = 600  # 10 минут ожидания (для n8n хватит)
RETRY_DELAY = 10  # Пауза между попытками


def generate_image_sync(prompt: str, negative_prompt: str, width: int, height: int) -> bytes:
    """
    Синхронная функция генерации с авторизацией по токену.
    """
    start_time = time.time()
    attempt = 1

    # 1. Получаем токен из .env (HF_TOKEN или API_KEY)
    hf_token = os.getenv("HF_TOKEN") or os.getenv("API_KEY")

    # 2. Формируем заголовки авторизации (для gradio_client 2.0+)
    headers = None
    if hf_token and hf_token.startswith("hf_"):
        headers = {"Authorization": f"Bearer {hf_token}"}

    print(f"[Image Gen] Start: {prompt[:50]}...")

    while True:
        elapsed = time.time() - start_time
        if elapsed > MAX_WAIT_TIME:
            raise TimeoutError("Превышено время ожидания генерации")

        try:
            # 3. Подключаемся, передавая заголовки с токеном
            client = Client(SPACE_URL, headers=headers)

            # Параметры Playground v2.5
            result = client.predict(
                prompt,  # prompt
                negative_prompt,  # negative_prompt
                True,  # use_negative_prompt
                0,  # seed
                width,  # width
                height,  # height
                3,  # guidance_scale (Жестко задано 3, как в твоем коде)
                True,  # randomize_seed
                api_name="/run"
            )

            # Разбор ответа
            image_path = None
            if result and isinstance(result, (list, tuple)):
                try:
                    # Обычно это result[0][0]['image']
                    image_path = result[0][0]['image']
                except (KeyError, IndexError, TypeError):
                    if isinstance(result[0], str):
                        image_path = result[0]

            if image_path and os.path.exists(image_path):
                # Читаем файл в память
                with open(image_path, "rb") as img_file:
                    image_bytes = img_file.read()

                # Удаляем временный файл
                try:
                    os.remove(image_path)
                except:
                    pass

                print(f"[Image Gen] Success on attempt {attempt}")
                return image_bytes

        # 4. Ловим ошибку перегрузки (429)
        except TooManyRequestsError:
            print(f"⚠️ [Image Gen] Server is busy (429). Cooling down for 30s...")
            time.sleep(30)  # Ждем дольше обычного

        except Exception as e:
            print(f"[Image Gen] Attempt {attempt} failed: {e}. Retrying...")
            time.sleep(RETRY_DELAY)

        attempt += 1