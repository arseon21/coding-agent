import os
import time
import logging
import requests
import json
from typing import Optional

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.api_key = os.environ.get("YANDEX_API_KEY")
        self.folder_id = os.environ.get("YANDEX_FOLDER_ID")
        
        if not self.api_key or not self.folder_id:
            raise ValueError("Проверьте YANDEX_API_KEY и YANDEX_FOLDER_ID в .env")

        self.model_name = os.environ.get("YANDEX_MODEL", "yandexgpt")
        self.temperature = float(os.environ.get("LLM_TEMPERATURE", "0.3"))
        self.max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "2000"))
        
        self.retries = int(os.environ.get("LLM_RETRIES", "3"))
        self.timeout = int(os.environ.get("LLM_TIMEOUT", "60"))
        self.url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    def get_response(self, prompt: str, system_role: str = "Ты — Python разработчик.") -> str:
        model_uri = f"gpt://{self.folder_id}/{self.model_name}/latest"
        
        payload = {
            "modelUri": model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": self.temperature,
                "maxTokens": str(self.max_tokens)
            },
            "messages": [
                {"role": "system", "text": system_role},
                {"role": "user", "text": prompt}
            ]
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {self.api_key}",
            "x-folder-id": self.folder_id
        }

        attempt = 0
        while attempt < self.retries:
            try:
                response = requests.post(
                    self.url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get('message', response.text)
                    logger.error(f"Yandex API Error {response.status_code}: {error_msg}")
                    
                    if response.status_code == 400:
                        raise ValueError(f"Ошибка в параметрах запроса: {error_msg}")
                    
                    response.raise_for_status()

                result = response.json()
                return result['result']['alternatives'][0]['message']['text']

            except Exception as e:
                attempt += 1
                if attempt == self.retries:
                    raise e
                time.sleep(2 ** attempt)
        return ""