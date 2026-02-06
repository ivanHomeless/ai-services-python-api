import os
import random
import requests
from .base import ImageProvider

class PixazoProvider(ImageProvider):
    def __init__(self):
        self.api_key = os.getenv('API_KEY_PIXAZO')
        self.url = os.getenv('URL_PIXAZO', "https://gateway.pixazo.ai/flux-1-schnell/v1/getData")

    @property
    def name(self):
        return "Pixazo (Flux Schnell)"

    def generate(self, prompt: str, negative_prompt: str, width: int, height: int) -> bytes:
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Ocp-Apim-Subscription-Key": self.api_key
        }

        data = {
            "prompt": prompt,
            "num_steps": 4,
            "seed": random.randint(1, 9999999),
            "height": height,
            "width": width
        }

        # 1. Запрос ссылки
        response = requests.post(self.url, json=data, headers=headers, timeout=60)
        if response.status_code != 200:
            raise Exception(f"API Error {response.status_code}: {response.text}")

        json_data = response.json()
        image_url = json_data.get('output')

        if not image_url:
            raise ValueError(f"Нет ссылки в ответе: {json_data}")

        # 2. Скачивание
        img_response = requests.get(image_url)
        if img_response.status_code == 200:
            return img_response.content
        else:
            raise Exception("Ошибка скачивания файла Pixazo")