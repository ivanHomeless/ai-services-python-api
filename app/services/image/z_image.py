import os
import logging
from gradio_client import Client
from .base import ImageProvider

# Инициализируем логгер для этого файла
logger = logging.getLogger(__name__)

class ZImageProvider(ImageProvider):
    def __init__(self):
        self.space_id = "Tongyi-MAI/Z-Image"
        self.token = os.getenv("HF_TOKEN")

    @property
    def name(self):
        return "Z-Image (Tongyi-MAI)"

    def _get_best_resolution(self, width: int, height: int) -> str:
        ratio = width / height
        if 0.95 < ratio < 1.05:
            return '1024x1024 ( 1:1 )'
        elif ratio > 1:
            return '1248x832 ( 3:2 )'
        else:
            return '832x1248 ( 2:3 )'

    def generate(self, prompt: str, negative_prompt: str, width: int, height: int) -> bytes:
        resolution_str = self._get_best_resolution(width, height)
        logger.info(f"🎯 [Z-Image] Starting generation. Prompt: '{prompt[:50]}...', Resolution: {resolution_str}")

        headers = {"Authorization": f"Bearer {self.token}"} if self.token else None
        logger.debug(f"🔑 [Z-Image] Token present: {bool(self.token)}, Space: {self.space_id}")
        client = Client(self.space_id, headers=headers)

        try:
            logger.info(f"⏳ [Z-Image] Submitting job (Timeout: 45s)...")

            try:
                # 1. Отправляем задачу в очередь
                job = client.submit(
                    prompt,  # prompt
                    negative_prompt,  # negative_prompt
                    resolution_str,  # resolution
                    0,  # seed
                    30,  # steps
                    4.0,  # guidance
                    False,  # cfg_norm
                    True,  # random_seed
                    [],  # gallery
                    api_name="/generate"
                )
                logger.debug(f"📤 [Z-Image] Job submitted, waiting for result...")

                # 2. Ждем 45 секунд
                result = job.result(timeout=45)
                logger.info(f"✅ [Z-Image] Job result received. Type: {type(result).__name__}, Value: {result}")

            except Exception as e:
                logger.warning(f"⚠️ [Z-Image] Timeout or Error: {e}")
                raise TimeoutError(f"Z-Image failed/timeout: {e}")

            image_path = None

            try:
                # result[0] — это список словарей вида [{'image': '...', 'caption': ...}]
                gallery = result[0]
                logger.debug(f"📦 [Z-Image] Gallery type: {type(gallery).__name__}, content: {gallery}")

                if gallery and isinstance(gallery, list):
                    first_item = gallery[0]
                    logger.debug(f"📦 [Z-Image] First item type: {type(first_item).__name__}, content: {first_item}")

                    # Проверяем, есть ли ключ 'image'
                    if 'image' in first_item:
                        img_data = first_item['image']
                        logger.debug(f"🖼️ [Z-Image] img_data type: {type(img_data).__name__}, value: {img_data}")

                        # Вариант 1: Просто строка
                        if isinstance(img_data, str):
                            image_path = img_data

                        # Вариант 2: Словарь {'path': ...} (бывает в других версиях Gradio)
                        elif isinstance(img_data, dict) and 'path' in img_data:
                            image_path = img_data['path']
                    else:
                        logger.warning(f"⚠️ [Z-Image] No 'image' key in first_item. Keys: {first_item.keys()}")
                else:
                    logger.warning(f"⚠️ [Z-Image] Gallery is empty or not a list: {gallery}")

            except Exception as e:
                logger.error(f"⚠️ [Z-Image] Parse error. Raw result: {result}. Error: {e}")
                raise ValueError(f"Z-Image не смог распарсить ответ. Сырой ответ: {result}")

            logger.debug(f"📂 [Z-Image] Resolved image_path: {image_path}")

            # Читаем файл и потом чистим
            if image_path and os.path.exists(image_path):
                logger.info(f"📖 [Z-Image] Reading file: {image_path}")
                with open(image_path, "rb") as img_file:
                    image_bytes = img_file.read()
                logger.info(f"✅ [Z-Image] File read OK. Size: {len(image_bytes)} bytes")

                # Удаляем временный файл ПОСЛЕ чтения
                try:
                    os.remove(image_path)
                    logger.debug(f"🗑️ [Z-Image] Temp file deleted: {image_path}")
                except Exception as cleanup_e:
                    logger.warning(f"⚠️ [Z-Image] Failed to delete temp file {image_path}: {cleanup_e}")

                return image_bytes

            # Если дошли сюда — значит файл не нашли
            logger.error(f"❌ [Z-Image] Image path not found or doesn't exist. Path: {image_path}")
            raise ValueError(f"Z-Image не вернул корректный путь. Сырой ответ: {result}")
        finally:
            client.close()
            logger.debug(f"🔌 [Z-Image] Client closed")