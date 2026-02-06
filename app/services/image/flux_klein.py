import os
import logging

from gradio_client import Client
from .base import ImageProvider

# Инициализируем логгер для этого файла
logger = logging.getLogger(__name__)

class FluxKleinProvider(ImageProvider):
    def __init__(self):
        # Официальный (или полуофициальный) спейс
        self.space_id = "black-forest-labs/FLUX.2-klein-9B"
        self.token = os.getenv("HF_TOKEN")

    @property
    def name(self):
        return "Flux.2 Klein (9B Distilled)"

    def generate(self, prompt: str, negative_prompt: str, width: int, height: int) -> bytes:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else None
        client = Client(self.space_id, headers=headers)

        logger.info(f"⏳ [Flux] Submitting job (Timeout: 30s)...")

        # Используем submit + timeout
        job = client.submit(
            prompt, [], "Distilled (4 steps)", 0, True, width, height, 4, 3.5, False,
            api_name="/generate"
        )

        try:
            # Flux быстрый, 30 секунд ему за глаза. Если дольше - значит очередь.
            result = job.result(timeout=30)
        except Exception:
            raise TimeoutError("Flux Queue timeout (30s limit)")

        # --- Разбор ответа ---
        # Лог говорит: Returns (result: dict, seed: float)
        # result: dict(path: str, url: str, ...)

        image_path = None

        # Пробуем достать путь
        try:
            # result[0] - это объект картинки
            image_obj = result[0]

            # Вариант 1: Это словарь с ключом 'path' или 'url'
            if isinstance(image_obj, dict):
                if 'path' in image_obj:
                    image_path = image_obj['path']
                elif 'url' in image_obj:
                    # Если вернулась ссылка, можно добавить логику скачивания,
                    # но Gradio Client обычно сам качает файлы в /tmp/
                    image_path = image_obj['url']

                    # Вариант 2: Просто строка (путь)
            elif isinstance(image_obj, str):
                image_path = image_obj

        except Exception as e:
            print(f"⚠️ Ошибка парсинга Flux Klein: {e}")

        # Читаем файл
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                image_bytes = img_file.read()
            try:
                os.remove(image_path)
            except:
                pass
            return image_bytes

        raise ValueError(f"Flux Klein не вернул файл. Ответ: {result}")