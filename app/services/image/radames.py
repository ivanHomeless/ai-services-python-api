import os
import random
import logging
from gradio_client import Client
from .base import ImageProvider

# Инициализируем логгер для этого файла
logger = logging.getLogger(__name__)

class RadamesProvider(ImageProvider):
    def __init__(self):
        # Твоя ссылка: https://huggingface.co/spaces/radames/Real-Time-Text-to-Image-SDXL-Lightning
        self.space_id = "radames/Real-Time-Text-to-Image-SDXL-Lightning"
        self.token = os.getenv("HF_TOKEN")

    @property
    def name(self):
        return "Radames SDXL-Lightning (Real-Time)"

    def generate(self, prompt: str, negative_prompt: str, width: int, height: int) -> bytes:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else None

        client = Client(self.space_id, headers=headers)

        # У этого спейса обычно очень простой интерфейс: Промпт + Сид.
        # Он "Real-Time", поэтому часто игнорирует настройки ширины/высоты (делает 1024x1024).

        # Генерируем случайный сид, чтобы картинки не повторялись
        seed = random.randint(0, 2147483647)

        logger.info(f"⚡ [Radames] Instant gen request (Timeout: 15s)...")

        try:
            job = client.submit(prompt, seed, api_name="/predict")
            # Lightning должен быть молниеносным. Если он думает > 15 сек, он мертв.
            result = job.result(timeout=15)
        except Exception as e:
            logger.warning(f"⚠️ [Radames] Timeout: {e}")
            raise TimeoutError(f"Radames timeout")

        # --- Разбор ответа ---
        # Обычно возвращает путь к файлу (строку)
        image_path = None

        if isinstance(result, str):
            image_path = result
        elif isinstance(result, (list, tuple)):
            # Если вернул кортеж (filepath, something_else)
            if isinstance(result[0], str):
                image_path = result[0]
            elif isinstance(result[0], dict) and 'image' in result[0]:
                # Если вернул галерею
                image_path = result[0]['image']

        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                image_bytes = img_file.read()
            try:
                os.remove(image_path)
            except:
                pass
            return image_bytes

        raise ValueError(f"Radames не вернул файл. Ответ: {result}")