import os
import logging
from gradio_client import Client
from .base import ImageProvider

# Инициализируем логгер для этого файла
logger = logging.getLogger(__name__)

class QwenProvider(ImageProvider):
    def __init__(self):
        self.space_id = "Qwen/Qwen-Image-2512"
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
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else None

        # Определяем соотношение
        ar_string = self._get_aspect_ratio(width, height)
        logger.info(f"📐 [Qwen] Size {width}x{height} -> Aspect Ratio '{ar_string}'")

        client = Client(self.space_id, headers=headers)

        job = client.submit(
            prompt, 0, True, ar_string, 4.0, 50, True,
            api_name="/infer"
        )

        try:
            # Qwen медленный, дадим ему 60 секунд
            result = job.result(timeout=60)
        except Exception:
            raise TimeoutError("Qwen Queue timeout (60s limit)")
        # --- Разбор ответа ---
        # Returns: (result, seed)
        # result: dict(path: str, url: str, ...)

        image_path = None
        try:
            # Gradio возвращает кортеж, первый элемент - результат
            output_obj = result[0]

            # Это может быть путь-строка или словарь
            if isinstance(output_obj, str):
                image_path = output_obj
            elif isinstance(output_obj, dict):
                if 'path' in output_obj:
                    image_path = output_obj['path']
                elif 'url' in output_obj:
                    # Некоторые версии возвращают url вместо пути
                    image_path = output_obj['url']

        except Exception as e:
            print(f"⚠️ Ошибка парсинга Qwen: {e}")

        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                image_bytes = img_file.read()
            try:
                os.remove(image_path)
            except:
                pass
            return image_bytes

        raise ValueError(f"Qwen не вернул файл. Ответ: {result}")