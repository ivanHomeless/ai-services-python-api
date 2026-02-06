import os

import requests
import random

from dotenv import load_dotenv

load_dotenv()

# Твой ключ от Pixazo
API_KEY_PIXAZO = os.getenv('API_KEY_PIXAZO')
URL = "https://gateway.pixazo.ai/flux-1-schnell/v1/getData"


def generate_image_sync(
        prompt: str,
        negative_prompt: str,  # Оставляем аргумент, чтобы роутер не ругался (но Flux его не использует)
        width: int = 1024,
        height: int = 680
) -> bytes:
    print(f"[Pixazo Flux] Start: {prompt[:50]}...")

    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "Ocp-Apim-Subscription-Key": API_KEY_PIXAZO
    }

    # Параметры запроса
    data = {
        "prompt": prompt,
        "num_steps": 4,  # Оптимально для Flux Schnell
        "seed": random.randint(1, 9999999),  # Случайное зерно, чтобы картинки были разными
        "height": height,
        "width": width
    }

    try:
        # --- ШАГ 1: Получаем ссылку на картинку ---
        response = requests.post(URL, json=data, headers=headers, timeout=60)

        if response.status_code != 200:
            raise Exception(f"API Error: {response.text}")

        result = response.json()

        # Вот тут исправление под твой лог:
        # Ответ сервера: {'output': 'https://...'}
        image_url = result.get('output')

        if not image_url:
            raise ValueError(f"Сервер не вернул ссылку. Ответ: {result}")

        print(f"[Pixazo] URL received: {image_url}")

        # --- ШАГ 2: Скачиваем саму картинку ---
        # n8n нужен файл, а не ссылка, поэтому скачиваем её здесь
        img_response = requests.get(image_url)

        if img_response.status_code == 200:
            print("[Pixazo] Image downloaded successfully!")
            return img_response.content  # Возвращаем байты
        else:
            raise Exception(f"Не удалось скачать файл по ссылке. Code: {img_response.status_code}")

    except Exception as e:
        print(f"❌ Pixazo Error: {e}")
        # Прокидываем ошибку выше, чтобы роутер выдал 500
        raise e