import os
import time
import logging
import requests
import random
from .base import ImageProvider

logger = logging.getLogger(__name__)

class LeonardoProvider(ImageProvider):
    def __init__(self):
        self.api_key = os.getenv('LEONARDO_API_KEY')
        # Default model: GPT Image-1.5
        # Available models:
        # - gpt-image-1.5 (default)
        # - gemini-2.5-flash-image (Nano Banana)
        # - seedream-4.5
        self.model_id = os.getenv('LEONARDO_MODEL_ID', 'gpt-image-1.5')
        self.base_url = "https://cloud.leonardo.ai/api/rest/v2/generations"

    @property
    def name(self):
        return f"Leonardo.AI ({self.model_id})"

    def _get_seedream_resolution(self, width: int, height: int) -> tuple[int, int]:
        """
        Seedream-4.5 supports width/height between 256 and 1440.
        Must be multiples of 8.
        """
        def clamp_and_align(val):
            val = max(256, min(1440, val))
            return (val // 8) * 8
        
        return clamp_and_align(width), clamp_and_align(height)

    def generate(self, prompt: str, negative_prompt: str, width: int, height: int) -> bytes:
        logger.info(f"🎯 [Leonardo] Starting generation. Prompt: '{prompt[:50]}...', Size: {width}x{height}, Model: {self.model_id}")
        logger.debug(f"🔑 [Leonardo] API key present: {bool(self.api_key)}")

        if not self.api_key:
             raise ValueError("LEONARDO_API_KEY not set")

        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.api_key}",
            "content-type": "application/json"
        }

        # Parameter logic based on model
        gen_width, gen_height = width, height
        
        # Adjust dimensions for Seedream if needed
        if "seedream" in self.model_id.lower():
             gen_width, gen_height = self._get_seedream_resolution(width, height)
             if gen_width != width or gen_height != height:
                 logger.info(f"📐 [Leonardo] Adjusted size for Seedream: {width}x{height} -> {gen_width}x{gen_height}")
        
        # GPT-1.5 only supports 3 fixed resolutions: 1024x1024, 1024x1536, 1536x1024
        if self.model_id == 'gpt-image-1.5':
            gpt_resolutions = [(1024, 1024), (1536, 1024), (1024, 1536)]
            ratio = width / height if height else 1
            gen_width, gen_height = min(gpt_resolutions, key=lambda r: abs(r[0] / r[1] - ratio))
            logger.info(f"📐 [Leonardo] Mapped size for GPT-1.5: {width}x{height} -> {gen_width}x{gen_height}")

        payload = {
            "model": self.model_id,
            "public": False,
            "parameters": {
                "prompt": prompt,
                "width": gen_width,
                "height": gen_height,
                "quantity": 1,
                "prompt_enhance": "OFF",
                # "seed": random.randint(0, 2**32 - 1)
            }
        }
        
        # GPT-1.5 specific: set mode
        if self.model_id == 'gpt-image-1.5':
            payload["parameters"]["mode"] = "QUALITY"

        if negative_prompt:
             payload["parameters"]["negative_prompt"] = negative_prompt

        # 1. Submit Generation
        logger.info(f"⏳ [Leonardo] Submitting job (Timeout: 60s)...")
        logger.debug(f"📤 [Leonardo] Request payload: {payload}")
        try:
            response = requests.post(self.base_url, json=payload, headers=headers, timeout=60)
            logger.debug(f"📤 [Leonardo] Submit response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"❌ [Leonardo] API Error: {response.text}")
                raise Exception(f"Leonardo API Error {response.status_code}: {response.text}")
            
            data = response.json()
            logger.info(f"📦 [Leonardo] Submit raw response: {data}") # Changed to INFO to definitely see it

            if isinstance(data, list):
                 logger.warning(f"⚠️ [Leonardo] Submit response is a LIST. Trying to parse first item...")
                 if data:
                     data = data[0]
                 else:
                     raise ValueError("Leonardo returned empty list")

            generation_id = (
                data.get('generationId')
                or data.get('generate', {}).get('generationId')
                or data.get('sdGenerationJob', {}).get('generationId')
            )
            
            if not generation_id:
                 logger.error(f"❌ [Leonardo] No generationId in response: {data}")
                 raise ValueError(f"Leonardo API did not return generationId. Response: {data}")
                 
            logger.info(f"🆔 [Leonardo] Job submitted. ID: {generation_id}")

        except Exception as e:
            logger.error(f"❌ [Leonardo] Submit failed: {e}")
            raise e

        # 2. Poll for Result
        start_time = time.time()
        timeout = 90 # 90 seconds polling timeout
        image_url = None

        while time.time() - start_time < timeout:
            try:
                poll_url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}" # Note: Polling is often v1 methods in docs, but let's check correct endpoint. 
                # Docs said GET /generations/{id} returns generation info.
                # Actually, standard pattern is checking v1/generations/{id} or similar. 
                # Let's verify polling endpoint from my research task... I read 'Get a Single Generation'.
                # The endpoint is `GET https://cloud.leonardo.ai/api/rest/v1/generations/{id}` usually.
                
                poll_response = requests.get(poll_url, headers=headers, timeout=30)
                
                if poll_response.status_code != 200:
                    logger.warning(f"⚠️ [Leonardo] Poll error {poll_response.status_code}: {poll_response.text}")
                    time.sleep(2)
                    continue
                
                poll_data = poll_response.json()
                # logger.debug(f"📦 [Leonardo] Poll data: {poll_data}") # Uncomment for deep debug
                
                generation_info = poll_data.get('generations_by_pk')
                
                if not generation_info:
                     logger.warning(f"⚠️ [Leonardo] Poll response missing 'generations_by_pk'. Keys: {list(poll_data.keys())}")
                     time.sleep(2)
                     continue
                
                # Fix for "list object has no attribute get"
                # Sometimes it returns a list?
                if isinstance(generation_info, list):
                    if not generation_info:
                        logger.warning(f"⚠️ [Leonardo] 'generations_by_pk' is an empty list")
                        time.sleep(2)
                        continue
                    generation_info = generation_info[0]

                status = generation_info.get('status')
                logger.debug(f"🔄 [Leonardo] Poll status: {status}")
                
                if status == 'COMPLETE':
                    generated_images = generation_info.get('generated_images', [])
                    if generated_images:
                        image_url = generated_images[0].get('url')
                        logger.info(f"✅ [Leonardo] Generation COMPLETE. Image URL found.")
                        break
                    else:
                        logger.error(f"❌ [Leonardo] Status COMPLETE but no images found.")
                        raise ValueError("Leonardo generation failed (no images)")
                elif status == 'FAILED':
                     logger.error(f"❌ [Leonardo] Generation FAILED.")
                     raise ValueError("Leonardo generation status: FAILED")
                
                time.sleep(2)

            except Exception as e:
                logger.warning(f"⚠️ [Leonardo] Polling exception: {e}")
                time.sleep(2)

        if not image_url:
            raise TimeoutError("Leonardo generation timed out while polling")

        # 3. Download Image
        logger.info(f"⬇️ [Leonardo] Downloading image...")
        try:
            img_response = requests.get(image_url, timeout=60)
            if img_response.status_code == 200:
                logger.info(f"✅ [Leonardo] Image downloaded OK. Size: {len(img_response.content)} bytes")
                return img_response.content
            else:
                 raise Exception(f"Download failed with status {img_response.status_code}")
        except Exception as e:
            logger.error(f"❌ [Leonardo] Download failed: {e}")
            raise e
