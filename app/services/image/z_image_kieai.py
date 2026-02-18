from .kieai_base import KieAIProvider


class ZImageKieAIProvider(KieAIProvider):
    # Поддерживаемые aspect_ratio: 1:1, 4:3, 3:4, 16:9, 9:16
    _RATIOS = {"1:1": 1/1, "4:3": 4/3, "3:4": 3/4, "16:9": 16/9, "9:16": 9/16}

    @property
    def name(self) -> str:
        return "Z-Image (kie.ai)"

    @property
    def model_id(self) -> str:
        return "z-image"

    def _build_input(self, prompt: str, negative_prompt: str, width: int, height: int) -> dict:
        ratio = width / height if height else 1
        aspect_ratio = min(self._RATIOS, key=lambda k: abs(self._RATIOS[k] - ratio))
        return {"prompt": prompt, "aspect_ratio": aspect_ratio}
