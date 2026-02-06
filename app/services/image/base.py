from abc import ABC, abstractmethod


class ImageProvider(ABC):
    """
    Базовый абстрактный класс.
    Определяет правила: каждый провайдер ОБЯЗАН иметь имя и метод generate.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Вернуть понятное имя сервиса для логов"""
        pass

    @abstractmethod
    def generate(self, prompt: str, negative_prompt: str, width: int, height: int) -> bytes:
        """Сгенерировать картинку и вернуть байты"""
        pass