from typing import List
from .base import ImageProvider
from .huggingface import HuggingFaceProvider
from .pixazo import PixazoProvider
from .z_image import ZImageProvider  # <--- 1. ИМПОРТИРУЕМ НОВЫЙ КЛАСС


def generate_image_sync(
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int
) -> bytes:
    # --- 2. ДОБАВЛЯЕМ В СПИСОК ---
    providers: List[ImageProvider] = [
        HuggingFaceProvider(),  # 1. Playground v2.5 (Топ качество)
        ZImageProvider(),  # 2. Z-Image (Новый! Хорошая альтернатива)
        PixazoProvider()  # 3. Pixazo (Flux) - Надежный резерв
    ]

    errors = []

    for provider in providers:
        print(f"🔄 [Orchestrator] Пробуем: {provider.name}...")
        try:
            result = provider.generate(prompt, negative_prompt, width, height)
            print(f"✅ [Orchestrator] Успех: {provider.name}")
            return result
        except Exception as e:
            err_msg = str(e)
            print(f"⚠️ [Orchestrator] {provider.name} error: {err_msg}")

            # Если это лимит GPU
            if "quota" in err_msg.lower() or "429" in err_msg:
                print("   -> (Лимит исчерпан, идем дальше)")

            errors.append(f"{provider.name}: {err_msg}")
            continue

    raise Exception(f"Все сервисы недоступны. Детали: {'; '.join(errors)}")