import os
import time
import json
import logging
import requests
from abc import abstractmethod
from .base import ImageProvider

logger = logging.getLogger(__name__)

_CREATE_URL = "https://api.kie.ai/api/v1/jobs/createTask"
_POLL_URL = "https://api.kie.ai/api/v1/jobs/recordInfo"


class KieAIProvider(ImageProvider):
    """
    Базовый провайдер для kie.ai.
    Общая логика: создание задачи → поллинг → скачивание результата.

    Подклассы обязаны реализовать:
      - name: str
      - model_id: str  — значение поля "model" в запросе
      - _build_input(prompt, negative_prompt, width, height) -> dict
    """

    poll_timeout: int = 120  # секунд, можно переопределить в подклассе

    def __init__(self):
        self.api_key = os.getenv("KIEAI_API_KEY")

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Идентификатор модели для поля 'model' в запросе к kie.ai"""
        pass

    @abstractmethod
    def _build_input(self, prompt: str, negative_prompt: str, width: int, height: int) -> dict:
        """Сформировать словарь 'input' специфичный для модели"""
        pass

    def generate(self, prompt: str, negative_prompt: str, width: int, height: int) -> bytes:
        if not self.api_key:
            raise ValueError("KIEAI_API_KEY not set")

        logger.info(f"🎯 [{self.name}] Starting. Prompt: '{prompt[:50]}...'")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # 1. Создаём задачу
        payload = {
            "model": self.model_id,
            "input": self._build_input(prompt, negative_prompt, width, height),
        }

        resp = requests.post(_CREATE_URL, json=payload, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise Exception(f"[{self.name}] Create error {resp.status_code}: {resp.text}")

        data = resp.json()
        task_id = data.get("data", {}).get("taskId")
        if not task_id:
            raise ValueError(f"[{self.name}] No taskId in response: {data}")

        logger.info(f"🆔 [{self.name}] Task created: {task_id}")

        # 2. Поллинг результата
        start = time.time()
        image_url = None

        while time.time() - start < self.poll_timeout:
            time.sleep(3)

            poll_resp = requests.get(_POLL_URL, params={"taskId": task_id}, headers=headers, timeout=15)
            if poll_resp.status_code != 200:
                logger.warning(f"⚠️ [{self.name}] Poll error {poll_resp.status_code}")
                continue

            poll_data = poll_resp.json().get("data", {})
            state = poll_data.get("state")
            logger.debug(f"🔄 [{self.name}] State: {state}")

            if state == "success":
                result_json = poll_data.get("resultJson", "{}")
                urls = json.loads(result_json).get("resultUrls", [])
                if not urls:
                    raise ValueError(f"[{self.name}] Success but no resultUrls")
                image_url = urls[0]
                logger.info(f"✅ [{self.name}] Done. Downloading...")
                break

            if state == "fail":
                raise Exception(f"[{self.name}] Generation failed: {poll_data.get('failMsg', 'unknown')}")

        if not image_url:
            raise TimeoutError(f"[{self.name}] Polling timed out after {self.poll_timeout}s")

        # 3. Скачиваем изображение
        img_resp = requests.get(image_url, timeout=60)
        if img_resp.status_code != 200:
            raise Exception(f"[{self.name}] Download failed: {img_resp.status_code}")

        logger.info(f"✅ [{self.name}] Downloaded {len(img_resp.content)} bytes")
        return img_resp.content
