import os
import logging

from gradio_client import Client
from .base import ImageProvider

# Инициализируем логгер для этого файла
logger = logging.getLogger(__name__)

class PlaygroundProvider(ImageProvider):
    def __init__(self):
        self.token = os.getenv("HF_TOKEN")
        self.url = os.getenv("HF_URL") or "https://playgroundai-playground-v2-5.hf.space/"

    @property
    def name(self):
        return "Hugging Face (Playground v2.5)"

    def generate(self, prompt: str, negative_prompt: str, width: int, height: int) -> bytes:
        logger.info(f"🎯 [Playground] Starting generation. Prompt: '{prompt[:50]}...', Size: {width}x{height}")
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else None
        logger.debug(f"🔑 [Playground] Token present: {bool(self.token)}, URL: {self.url}")
        client = Client(self.url, headers=headers)

        try:
            logger.info(f"⏳ [Playground] Submitting job (Timeout: 45s)...")

            job = client.submit(
                prompt, negative_prompt, True, 0, width, height, 3, True,
                api_name="/run"
            )
            logger.debug(f"📤 [Playground] Job submitted, waiting for result...")

            try:
                result = job.result(timeout=45)
                logger.info(f"✅ [Playground] Job result received. Type: {type(result).__name__}, Value: {result}")
            except Exception as e:
                logger.warning(f"⚠️ [Playground] Timeout or Error: {e}")
                raise TimeoutError(f"Too slow! Queue is long. ({str(e)})")

            image_path = None
            if isinstance(result, (list, tuple)):
                logger.debug(f"📦 [Playground] Result is {type(result).__name__}, len={len(result)}")
                try:
                    if isinstance(result[0], list) and isinstance(result[0][0], dict):
                        image_path = result[0][0]['image']
                        logger.debug(f"📦 [Playground] Parsed nested dict, image_path: {image_path}")
                    elif isinstance(result[0], str):
                        image_path = result[0]
                        logger.debug(f"📦 [Playground] Parsed string, image_path: {image_path}")
                except Exception as e:
                    logger.warning(f"⚠️ [Playground] Parse failed: {e}")
            elif isinstance(result, str):
                image_path = result
                logger.debug(f"📦 [Playground] Result is plain string: {image_path}")

            logger.debug(f"📂 [Playground] Resolved image_path: {image_path}")

            if image_path and os.path.exists(image_path):
                logger.info(f"📖 [Playground] Reading file: {image_path}")
                with open(image_path, "rb") as img_file:
                    image_bytes = img_file.read()
                logger.info(f"✅ [Playground] File read OK. Size: {len(image_bytes)} bytes")
                try:
                    os.remove(image_path)
                    logger.debug(f"🗑️ [Playground] Temp file deleted: {image_path}")
                except:
                    pass
                return image_bytes

            logger.error(f"❌ [Playground] Image path not found or doesn't exist. Path: {image_path}")
            raise ValueError(f"HF не вернул файл. Ответ: {result}")
        finally:
            client.close()
            logger.debug(f"🔌 [Playground] Client closed")