import os
import logging
from gradio_client import Client
from .base import ImageProvider

# Инициализируем логгер для этого файла
logger = logging.getLogger(__name__)

class QwenProvider(ImageProvider):
    def __init__(self):
        self.space_id = "https://qwen-qwen-image-2512.hf.space"
        self.token = os.getenv("HF_TOKEN")

    @property
    def name(self):
        return "Qwen-Image (Alibaba Cloud)"

    def _get_aspect_ratio(self, width: int, height: int) -> str:
        """
        Превращает размеры в пикселях в строку соотношения сторон,
        которую требует Qwen API.
        """
        ratio = width / height

        # Список доступных опций из твоего лога
        # '1:1', '16:9', '9:16', '4:3', '3:4', '3:2', '2:3'

        if 0.9 <= ratio <= 1.1:
            return '1:1'

        elif ratio > 1:  # Горизонтальные
            if ratio >= 1.6: return '16:9'  # Широкий экран
            if ratio >= 1.4: return '3:2'  # Фото (твой стандарт 1024/680 как раз тут)
            return '4:3'  # Старый монитор

        else:  # Вертикальные
            if ratio <= 0.6: return '9:16'  # Сторис
            if ratio <= 0.7: return '2:3'  # Портрет
            return '3:4'

    def generate(self, prompt: str, negative_prompt: str, width: int, height: int) -> bytes:
        logger.info(f"🎯 [Qwen] Starting generation. Prompt: '{prompt[:50]}...', Size: {width}x{height}")
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else None
        logger.debug(f"🔑 [Qwen] Token present: {bool(self.token)}, Space: {self.space_id}")

        ar_string = self._get_aspect_ratio(width, height)
        logger.info(f"📐 [Qwen] Size {width}x{height} -> Aspect Ratio '{ar_string}'")

        client = Client(self.space_id, headers=headers)

        try:
            logger.info(f"⏳ [Qwen] Submitting job (Timeout: 60s)...")
            job = client.submit(
                prompt, 0, True, ar_string, 4.0, 50, True,
                api_name="/infer"
            )
            logger.debug(f"📤 [Qwen] Job submitted, waiting for result...")

            try:
                result = job.result(timeout=60)
                logger.info(f"✅ [Qwen] Job result received. Type: {type(result).__name__}, Value: {result}")
            except Exception as e:
                logger.warning(f"⚠️ [Qwen] Timeout: {e}")
                raise TimeoutError("Qwen Queue timeout (60s limit)")

            image_path = None
            try:
                output_obj = result[0]
                logger.debug(f"📦 [Qwen] output_obj type: {type(output_obj).__name__}, content: {output_obj}")

                if isinstance(output_obj, str):
                    image_path = output_obj
                    logger.debug(f"📦 [Qwen] Parsed string, image_path: {image_path}")
                elif isinstance(output_obj, dict):
                    if 'path' in output_obj:
                        image_path = output_obj['path']
                    elif 'url' in output_obj:
                        image_path = output_obj['url']
                    logger.debug(f"📦 [Qwen] Parsed dict, image_path: {image_path}")

            except Exception as e:
                logger.warning(f"⚠️ [Qwen] Parse error: {e}")

            logger.debug(f"📂 [Qwen] Resolved image_path: {image_path}")

            if image_path and os.path.exists(image_path):
                logger.info(f"📖 [Qwen] Reading file: {image_path}")
                with open(image_path, "rb") as img_file:
                    image_bytes = img_file.read()
                logger.info(f"✅ [Qwen] File read OK. Size: {len(image_bytes)} bytes")
                try:
                    os.remove(image_path)
                    logger.debug(f"🗑️ [Qwen] Temp file deleted: {image_path}")
                except:
                    pass
                return image_bytes

            logger.error(f"❌ [Qwen] Image path not found or doesn't exist. Path: {image_path}")
            raise ValueError(f"Qwen не вернул файл. Ответ: {result}")
        finally:
            client.close()
            logger.debug(f"🔌 [Qwen] Client closed")