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

        headers = {"Authorization": f"Bearer {self.token}"} if self.token else None
        client = Client(self.space_id, headers=headers)

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

            # 2. Ждем 45 секунд
            result = job.result(timeout=45)

        except Exception as e:
            logger.warning(f"⚠️ [Z-Image] Timeout or Error: {e}")
            raise TimeoutError(f"Z-Image failed/timeout: {e}")

        # --- ИСПРАВЛЕННЫЙ ПАРСИНГ ---
        image_path = None

        try:
            # result[0] — это список словарей вида [{'image': '...', 'caption': ...}]
            gallery = result[0]

            if gallery and isinstance(gallery, list):
                first_item = gallery[0]

                # Проверяем, есть ли ключ 'image'
                if 'image' in first_item:
                    img_data = first_item['image']

                    # Вариант 1: Просто строка (как у тебя в ошибке)
                    if isinstance(img_data, str):
                        image_path = img_data

                    # Вариант 2: Словарь {'path': ...} (бывает в других версиях Gradio)
                    elif isinstance(img_data, dict) and 'path' in img_data:
                        image_path = img_data['path']

        except Exception as e:
            print(f"⚠️ Ошибка парсинга Z-Image: {e}")

        # Проверяем файл
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                image_bytes = img_file.read()
            # Удаляем временный файл
            try:
                os.remove(image_path)
            except:
                pass

            return image_bytes

        # Если дошли сюда — значит файл не нашли
        raise ValueError(f"Z-Image не вернул корректный путь. Сырой ответ: {result}")