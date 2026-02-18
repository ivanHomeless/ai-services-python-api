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
        logger.info(f"🎯 [Radames] Starting generation. Prompt: '{prompt[:50]}...', Size: {width}x{height}")
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else None
        logger.debug(f"🔑 [Radames] Token present: {bool(self.token)}, Space: {self.space_id}")

        client = Client(self.space_id, headers=headers)

        try:
            seed = random.randint(0, 2147483647)
            logger.info(f"⚡ [Radames] Instant gen request. Seed: {seed} (Timeout: 15s)...")

            try:
                job = client.submit(prompt, seed, api_name="/predict")
                logger.debug(f"📤 [Radames] Job submitted, waiting for result...")
                result = job.result(timeout=15)
                logger.info(f"✅ [Radames] Job result received. Type: {type(result).__name__}, Value: {result}")
            except Exception as e:
                logger.warning(f"⚠️ [Radames] Timeout: {e}")
                raise TimeoutError(f"Radames timeout")

            image_path = None
            if isinstance(result, str):
                image_path = result
                logger.debug(f"📦 [Radames] Result is plain string: {image_path}")
            elif isinstance(result, (list, tuple)):
                logger.debug(f"📦 [Radames] Result is {type(result).__name__}, len={len(result)}, content: {result}")
                if isinstance(result[0], str):
                    image_path = result[0]
                elif isinstance(result[0], dict) and 'image' in result[0]:
                    image_path = result[0]['image']

            logger.debug(f"📂 [Radames] Resolved image_path: {image_path}")

            if image_path and os.path.exists(image_path):
                logger.info(f"📖 [Radames] Reading file: {image_path}")
                with open(image_path, "rb") as img_file:
                    image_bytes = img_file.read()
                logger.info(f"✅ [Radames] File read OK. Size: {len(image_bytes)} bytes")
                try:
                    os.remove(image_path)
                    logger.debug(f"🗑️ [Radames] Temp file deleted: {image_path}")
                except:
                    pass
                return image_bytes

            logger.error(f"❌ [Radames] Image path not found or doesn't exist. Path: {image_path}")
            raise ValueError(f"Radames не вернул файл. Ответ: {result}")
        finally:
            client.close()
            logger.debug(f"🔌 [Radames] Client closed")