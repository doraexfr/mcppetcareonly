from app.core.config import settings
from app.core.exceptions import ValidationAppError
from app.llm.base import LLMAdapter
from app.llm.gemma_adapter import GemmaAdapter


class LLMSelector:
    def __init__(self) -> None:
        self._adapters: dict[str, LLMAdapter] = {}
        self.register(GemmaAdapter())

    def register(self, adapter: LLMAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def select(self, name: str | None = None) -> LLMAdapter:
        adapter_name = name or settings.DEFAULT_LLM
        adapter = self._adapters.get(adapter_name)
        if adapter is None:
            raise ValidationAppError(f"LLM adapter '{adapter_name}' is not registered")
        return adapter


llm_selector = LLMSelector()

