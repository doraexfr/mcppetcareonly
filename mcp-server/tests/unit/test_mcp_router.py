"""Юнит-тесты: MCPRouter — маршрутизация вызовов инструментов."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ValidationAppError
from app.mcp.router import MCPRouter


# ── Вспомогательные классы ────────────────────────────────────────────────────

class EchoTool:
    name = "echo"

    async def ping(self, value: str) -> dict:
        return {"pong": value}

    async def add(self, a: int, b: int) -> dict:
        return {"result": a + b}

    def sync_method(self, x: int) -> dict:
        return {"x": x}

    async def _private_method(self) -> None:
        pass


class BrokenTool:
    name = "broken"

    async def fail(self) -> None:
        raise RuntimeError("S3 is down")


def make_registry(tool) -> MagicMock:
    registry = MagicMock()
    registry.get = MagicMock(return_value=tool)
    return registry


# ── Успешные вызовы ───────────────────────────────────────────────────────────

class TestMCPRouterSuccess:
    @pytest.mark.asyncio
    async def test_executes_async_method(self):
        router = MCPRouter(make_registry(EchoTool()))

        result = await router.execute("echo", "ping", {"value": "hello"})

        assert result == {"pong": "hello"}

    @pytest.mark.asyncio
    async def test_executes_sync_method(self):
        """Синхронный метод тоже должен работать (не awaitable → возвращается напрямую)."""
        router = MCPRouter(make_registry(EchoTool()))

        result = await router.execute("echo", "sync_method", {"x": 42})

        assert result == {"x": 42}

    @pytest.mark.asyncio
    async def test_passes_payload_as_kwargs(self):
        router = MCPRouter(make_registry(EchoTool()))

        result = await router.execute("echo", "add", {"a": 3, "b": 4})

        assert result["result"] == 7

    @pytest.mark.asyncio
    async def test_calls_registry_get_with_tool_name(self):
        registry = make_registry(EchoTool())
        router = MCPRouter(registry)

        await router.execute("echo", "ping", {"value": "x"})

        registry.get.assert_called_once_with("echo")


# ── Ошибки валидации ──────────────────────────────────────────────────────────

class TestMCPRouterValidation:
    @pytest.mark.asyncio
    async def test_unknown_method_raises_validation_error(self):
        router = MCPRouter(make_registry(EchoTool()))

        with pytest.raises(ValidationAppError, match="not available"):
            await router.execute("echo", "nonexistent_method", {})

    @pytest.mark.asyncio
    async def test_private_method_blocked(self):
        """Методы начинающиеся с _ недоступны."""
        router = MCPRouter(make_registry(EchoTool()))

        with pytest.raises(ValidationAppError):
            await router.execute("echo", "_private_method", {})

    @pytest.mark.asyncio
    async def test_wrong_payload_raises_validation_error(self):
        """Передаём неверные аргументы — TypeError превращается в ValidationAppError."""
        router = MCPRouter(make_registry(EchoTool()))

        with pytest.raises(ValidationAppError, match="Invalid payload"):
            await router.execute("echo", "ping", {"wrong_arg": "x"})

    @pytest.mark.asyncio
    async def test_missing_required_arg_raises_validation_error(self):
        router = MCPRouter(make_registry(EchoTool()))

        with pytest.raises(ValidationAppError):
            await router.execute("echo", "add", {"a": 1})  # b отсутствует


# ── Пробрасывание ошибок инструмента ─────────────────────────────────────────

class TestMCPRouterErrorPropagation:
    @pytest.mark.asyncio
    async def test_tool_exception_propagates(self):
        """Ошибка внутри инструмента прокидывается наружу без обёртки."""
        router = MCPRouter(make_registry(BrokenTool()))

        with pytest.raises(RuntimeError, match="S3 is down"):
            await router.execute("broken", "fail", {})

    @pytest.mark.asyncio
    async def test_logging_called_on_tool_call(self):
        """Проверяем что логгер вызывается при успешном вызове."""
        router = MCPRouter(make_registry(EchoTool()))

        with patch("app.mcp.router.logger") as mock_logger:
            await router.execute("echo", "ping", {"value": "test"})

        # Должно быть два вызова info: tool call + tool result
        assert mock_logger.info.call_count == 2

    @pytest.mark.asyncio
    async def test_error_logged_on_exception(self):
        """При ошибке логгер вызывает exception()."""
        router = MCPRouter(make_registry(BrokenTool()))

        with patch("app.mcp.router.logger") as mock_logger:
            with pytest.raises(RuntimeError):
                await router.execute("broken", "fail", {})

        mock_logger.exception.assert_called_once()
