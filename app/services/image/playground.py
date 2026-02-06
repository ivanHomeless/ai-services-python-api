import os
import logging

from gradio_client import Client
from .base import ImageProvider

# Инициализируем логгер для этого файла
logger = logging.getLogger(__name__)

class PlaygroundProvider(ImageProvider):
    def __init__(self):
        self.token = os.getenv("HF_TOKEN")
        self.url = os.getenv("HF_URL", "https://playgroundai-playground-v2-5.hf.space/")

    @property
    def name(self):
        return "Hugging Face (Playground v2.5)"

    def generate(self, prompt: str, negative_prompt: str, width: int, height: int) -> bytes:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else None
        client = Client(self.url, headers=headers)

        # Логируем начало
        logger.info(f"⏳ [Playground] Submitting job (Timeout: 45s)...")

        job = client.submit(
            prompt, negative_prompt, True, 0, width, height, 3, True,
            api_name="/run"
        )

        try:
            # Ждем результат ровно 45 секунд
            result = job.result(timeout=45)
        except Exception as e:
            # Если время вышло, отменяем задание, чтобы не грузить сервер зря
            # (метод cancel есть у job, но в блоке except лучше просто кинуть ошибку)
            raise TimeoutError(f"Too slow! Queue is long. ({str(e)})")

        # Дальше парсинг тот же самый...
        image_path = None
        if isinstance(result, (list, tuple)):
            try:
                if isinstance(result[0], list) and isinstance(result[0][0], dict):
                    image_path = result[0][0]['image']
                elif isinstance(result[0], str):
                    image_path = result[0]
            except:
                pass
        elif isinstance(result, str):
            image_path = result

        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                image_bytes = img_file.read()
            try:
                os.remove(image_path)
            except:
                pass
            return image_bytes

        raise ValueError(f"HF не вернул файл. Ответ: {result}")