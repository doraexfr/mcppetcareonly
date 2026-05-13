import inspect
from typing import Any, Dict

from app.core.exceptions import ValidationAppError
from app.mcp.registry import ToolRegistry


class MCPRouter:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    async def execute(self, tool: str, method: str, payload: Dict[str, Any]) -> Any:
        instance = self.registry.get(tool)
        handler = getattr(instance, method, None)
        if handler is None or not callable(handler) or method.startswith("_"):
            raise ValidationAppError(f"Method '{method}' is not available on tool '{tool}'")
        try:
            inspect.signature(handler).bind(**payload)
        except TypeError as exc:
            raise ValidationAppError(f"Invalid payload for '{tool}.{method}': {exc}") from exc

        result = handler(**payload)
        if inspect.isawaitable(result):
            return await result
        return result
