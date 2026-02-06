from typing import List
from .base import ImageProvider
from .huggingface import HuggingFaceProvider
from .pixazo import PixazoProvider


def generate_image_sync(
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int
) -> bytes:
    """
    Оркестратор: управляет порядком вызова провайдеров.
    """

    # НАСТРОЙКА ПРИОРИТЕТОВ
    providers: List[ImageProvider] = [
        HuggingFaceProvider(),  # 1. Сначала пробуем HF
        PixazoProvider()  # 2. Если упал - Pixazo
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
            errors.append(f"{provider.name}: {err_msg}")
            continue

    raise Exception(f"Все сервисы недоступны. Детали: {'; '.join(errors)}")