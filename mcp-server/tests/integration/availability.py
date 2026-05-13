"""
TC-01 · Доступность MCP-эндпоинта

Проверяем, что:
  - сервер отвечает (не ECONNREFUSED)
  - /docs возвращает HTML (FastAPI жив)
  - /auth/login работает корректно
  - невалидный токен отклоняется с 403
  - отсутствие токена отклоняется с 403
"""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from tests.integration.conftest import (
    AUTH_PASSWORD,
    BASE_URL,
    TEST_USER_ID,
)


# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_server_is_reachable():
    """Сервер отвечает на любой запрос (не connection refused)."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=5) as c:
        # FastAPI отдаёт openapi docs по умолчанию
        resp = await c.get("/docs")
    assert resp.status_code == 200, (
        f"Сервер недоступен или вернул {resp.status_code}. "
        "Убедитесь, что docker compose запущен."
    )


@pytest.mark.asyncio
async def test_login_success():
    """POST /auth/login с правильным паролем — 200 + JWT в ответе."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=5) as c:
        resp = await c.post(
            "/auth/login",
            json={"user_id": TEST_USER_ID, "password": AUTH_PASSWORD},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    data = body["data"]
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert isinstance(data["expires_in_minutes"], int)
    # JWT выглядит как три части через точку
    parts = data["access_token"].split(".")
    assert len(parts) == 3, "access_token не похож на JWT"


@pytest.mark.asyncio
async def test_login_wrong_password():
    """POST /auth/login с неверным паролем — 422 + error в теле."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=5) as c:
        resp = await c.post(
            "/auth/login",
            json={"user_id": TEST_USER_ID, "password": "wrong-password"},
        )
    assert resp.status_code == 422
    body = resp.json()
    assert body["data"] is None
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_protected_endpoint_without_token():
    """GET /mcp/pets/1/details без токена — 403 Forbidden."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=5) as c:
        resp = await c.get("/mcp/pets/1/details")
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_protected_endpoint_with_bad_token():
    """GET /mcp/pets/1/details с невалидным токеном — 403."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=5) as c:
        resp = await c.get(
            "/mcp/pets/1/details",
            headers={"Authorization": "Bearer totally.invalid.token"},
        )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_openapi_schema_has_mcp_routes():
    """OpenAPI-схема содержит все MCP-пути — роутер зарегистрирован."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=5) as c:
        resp = await c.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json().get("paths", {})
    expected = [
        "/auth/login",
        "/mcp/pets/{pet_id}/details",
        "/mcp/pets/{pet_id}/short",
        "/mcp/pets/{pet_id}/documents",
        "/mcp/clinics/city",
        "/mcp/execute",
    ]
    for path in expected:
        assert path in paths, f"Путь {path!r} отсутствует в OpenAPI-схеме"
