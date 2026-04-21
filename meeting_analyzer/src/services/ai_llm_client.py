import json
import os
from typing import Any

import httpx


DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"


class LLMError(Exception):
    pass


class GroqLLM:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = (model or os.getenv("GROQ_MODEL") or DEFAULT_MODEL).strip()
        self.base_url = (base_url or os.getenv("GROQ_API_BASE_URL") or DEFAULT_BASE_URL).strip()
        self.timeout = timeout

        if not self.api_key:
            raise LLMError("GROQ_API_KEY tanimli degil.")

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        data = self._post(payload)
        content = self._extract_content(data)

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM gecerli JSON donmedi: {exc}") from exc

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = httpx.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise LLMError(f"Groq istegi basarisiz: {exc}") from exc

    @staticmethod
    def _extract_content(data: dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices:
            raise LLMError("Groq yanitinda choices alani bos.")

        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if not content:
            raise LLMError("Groq yanitinda content alani bos.")
        return content
