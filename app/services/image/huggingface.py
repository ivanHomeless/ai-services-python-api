import os
from gradio_client import Client
from .base import ImageProvider  # Импортируем наш интерфейс


class HuggingFaceProvider(ImageProvider):
    def __init__(self):
        self.token = os.getenv("HF_TOKEN")
        self.url = os.getenv("HF_URL", "https://playgroundai-playground-v2-5.hf.space/")

    @property
    def name(self):
        return "Hugging Face (Playground v2.5)"

    def generate(self, prompt: str, negative_prompt: str, width: int, height: int) -> bytes:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else None

        # Создаем клиента
        client = Client(self.url, headers=headers)

        # Один запрос (Strategy: Fail Fast)
        result = client.predict(
            prompt, negative_prompt, True, 0, width, height, 3, True,
            api_name="/run"
        )

        image_path = None
        # Пытаемся распарсить разные форматы ответа Gradio
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