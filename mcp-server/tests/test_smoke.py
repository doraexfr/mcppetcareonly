import asyncio
import unittest
from datetime import date, datetime

from app.core.exceptions import ErrorCode, error_response, success_response
from app.mcp.registry import build_tool_registry
from app.mcp.router import MCPRouter
from app.services.clinics_service import is_open_at
from app.services.pets_service import calculate_age


class DummyTool:
    name = "dummy"

    async def echo(self, value: str) -> dict[str, str]:
        return {"value": value}


class DummyRegistry:
    def get(self, name: str) -> DummyTool:
        if name != "dummy":
            raise AssertionError("Unexpected tool name")
        return DummyTool()


class SmokeTests(unittest.TestCase):
    def test_response_format(self) -> None:
        self.assertEqual(success_response({"ok": True}), {"data": {"ok": True}, "error": None})
        self.assertEqual(
            error_response(ErrorCode.NOT_FOUND, "Missing"),
            {"data": None, "error": {"code": "NOT_FOUND", "message": "Missing"}},
        )

    def test_dynamic_tool_registry_discovers_required_tools(self) -> None:
        registry = build_tool_registry(object())
        self.assertEqual(registry.list_tools(), ["clinics", "documents", "pets"])

    def test_mcp_router_executes_registered_tool(self) -> None:
        router = MCPRouter(DummyRegistry())
        result = asyncio.run(router.execute("dummy", "echo", {"value": "pet-care"}))
        self.assertEqual(result, {"value": "pet-care"})

    def test_pet_age_calculation(self) -> None:
        today = date.today()
        self.assertEqual(calculate_age(today), 0)

    def test_clinic_working_hours(self) -> None:
        self.assertTrue(is_open_at("09:00-18:00", datetime(2026, 5, 4, 12, 30)))
        self.assertFalse(is_open_at("09:00-18:00", datetime(2026, 5, 4, 20, 30)))
        self.assertTrue(is_open_at("22:00-06:00", datetime(2026, 5, 4, 23, 30)))


if __name__ == "__main__":
    unittest.main()
