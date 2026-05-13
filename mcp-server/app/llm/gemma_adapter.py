import asyncio
import json
from urllib.error import URLError
from urllib.request import Request, urlopen
from typing import Any, Dict

from app.core.config import settings
from app.core.exceptions import ValidationAppError
from app.llm.base import LLMAdapter


class GemmaAdapter(LLMAdapter):
    name = "gemma"

    async def complete(self, prompt: str, context: Dict[str, Any] | None = None) -> str:
        if not settings.GEMMA_ENDPOINT:
            raise ValidationAppError("Gemma endpoint is not configured")
        payload = {"prompt": prompt, "context": context or {}}
        return await asyncio.to_thread(self._complete_sync, payload)

    def _complete_sync(self, payload: Dict[str, Any]) -> str:
        headers = {"Content-Type": "application/json"}
        if settings.GEMMA_API_KEY:
            headers["Authorization"] = f"Bearer {settings.GEMMA_API_KEY}"

        request = Request(
            settings.GEMMA_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=settings.GEMMA_TIMEOUT_SECONDS) as response:
                raw_body = response.read()
        except URLError as exc:
            raise ValidationAppError(f"Gemma request failed: {exc.reason}") from exc

        body = json.loads(raw_body.decode("utf-8"))
        for key in ("text", "completion", "response", "generated_text"):
            value = body.get(key)
            if isinstance(value, str):
                return value
        raise ValidationAppError("Gemma response did not contain generated text")
