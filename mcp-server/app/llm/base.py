from abc import ABC, abstractmethod
from typing import Any, Dict


class LLMAdapter(ABC):
    name: str

    @abstractmethod
    async def complete(self, prompt: str, context: Dict[str, Any] | None = None) -> str:
        ...
