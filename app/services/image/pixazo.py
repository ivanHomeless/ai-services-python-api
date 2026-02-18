import os
import random
import logging
import requests
from .base import ImageProvider

logger = logging.getLogger(__name__)

class PixazoProvider(ImageProvider):
    def __init__(self):
        self.api_key = os.getenv('API_KEY_PIXAZO')
        self.url = os.getenv('URL_PIXAZO', "https://gateway.pixazo.ai/flux-1-schnell/v1/getData")

    @property
    def name(self):
        return "Pixazo (Flux Schnell)"

    def generate(self, prompt: str, negative_prompt: str, width: int, height: int) -> bytes:
        logger.info(f"🎯 [Pixazo] Starting generation. Prompt: '{prompt[:50]}...', Size: {width}x{height}")
        logger.debug(f"🔑 [Pixazo] API key present: {bool(self.api_key)}, URL: {self.url}")

        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Ocp-Apim-Subscription-Key": self.api_key
        }

        seed = random.randint(1, 9999999)
        data = {
            "prompt": prompt,
            "num_steps": 4,
            "seed": seed,
            "height": height,
            "width": width
        }
        logger.debug(f"📤 [Pixazo] Request data: seed={seed}, steps=4")

        # 1. Запрос ссылки
        logger.info(f"⏳ [Pixazo] Sending API request (Timeout: 60s)...")
        response = requests.post(self.url, json=data, headers=headers, timeout=60)
        logger.info(f"📥 [Pixazo] API response status: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"❌ [Pixazo] API Error {response.status_code}: {response.text}")
            raise Exception(f"API Error {response.status_code}: {response.text}")

        json_data = response.json()
        image_url = json_data.get('output')
        logger.debug(f"📦 [Pixazo] Response keys: {list(json_data.keys())}, image_url: {image_url}")

        if not image_url:
            logger.error(f"❌ [Pixazo] No 'output' in response: {json_data}")
            raise ValueError(f"Нет ссылки в ответе: {json_data}")

        # 2. Скачивание
        logger.info(f"⬇️ [Pixazo] Downloading image from URL...")
        img_response = requests.get(image_url)
        if img_response.status_code == 200:
            logger.info(f"✅ [Pixazo] Image downloaded OK. Size: {len(img_response.content)} bytes")
            return img_response.content
        else:
            logger.error(f"❌ [Pixazo] Download failed. Status: {img_response.status_code}")
            raise Exception("Ошибка скачивания файла Pixazo")