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
        logger.info(f"🎯 [Flux] Starting generation. Prompt: '{prompt[:50]}...', Size: {width}x{height}")
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else None
        logger.debug(f"🔑 [Flux] Token present: {bool(self.token)}, Space: {self.space_id}")
        client = Client(self.space_id, headers=headers)

        try:
            logger.info(f"⏳ [Flux] Submitting job (Timeout: 30s)...")

            job = client.submit(
                prompt, [], "Distilled (4 steps)", 0, True, width, height, 4, 3.5, False,
                api_name="/generate"
            )
            logger.debug(f"📤 [Flux] Job submitted, waiting for result...")

            try:
                result = job.result(timeout=30)
                logger.info(f"✅ [Flux] Job result received. Type: {type(result).__name__}, Value: {result}")
            except Exception as e:
                logger.warning(f"⚠️ [Flux] Timeout: {e}")
                raise TimeoutError("Flux Queue timeout (30s limit)")

            image_path = None

            try:
                image_obj = result[0]
                logger.debug(f"📦 [Flux] image_obj type: {type(image_obj).__name__}, content: {image_obj}")

                if isinstance(image_obj, dict):
                    if 'path' in image_obj:
                        image_path = image_obj['path']
                    elif 'url' in image_obj:
                        image_path = image_obj['url']
                    logger.debug(f"📦 [Flux] Parsed dict, image_path: {image_path}")
                elif isinstance(image_obj, str):
                    image_path = image_obj
                    logger.debug(f"📦 [Flux] Parsed string, image_path: {image_path}")

            except Exception as e:
                logger.warning(f"⚠️ [Flux] Parse error: {e}")

            logger.debug(f"📂 [Flux] Resolved image_path: {image_path}")

            if image_path and os.path.exists(image_path):
                logger.info(f"📖 [Flux] Reading file: {image_path}")
                with open(image_path, "rb") as img_file:
                    image_bytes = img_file.read()
                logger.info(f"✅ [Flux] File read OK. Size: {len(image_bytes)} bytes")
                try:
                    os.remove(image_path)
                    logger.debug(f"🗑️ [Flux] Temp file deleted: {image_path}")
                except:
                    pass
                return image_bytes

            logger.error(f"❌ [Flux] Image path not found or doesn't exist. Path: {image_path}")
            raise ValueError(f"Flux Klein не вернул файл. Ответ: {result}")
        finally:
            client.close()
            logger.debug(f"🔌 [Flux] Client closed")