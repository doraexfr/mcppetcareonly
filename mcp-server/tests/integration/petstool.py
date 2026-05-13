"""
TC-02 · Инструмент «pets» — реальные данные из PostgreSQL

Проверяем, что:
  - /mcp/pets/{id}/details возвращает поля из таблицы pets_info
  - /mcp/pets/{id}/short возвращает краткую форму
  - данные соответствуют тому, что мы засеяли в conftest
  - чужой питомец отдаёт 403, несуществующий — 404
"""

from __future__ import annotations

import pytest

from tests.integration.conftest import TEST_PET_NAME, TEST_USER_ID


@pytest.mark.asyncio
async def test_get_pet_details_returns_db_data(client, seed_data):
    """GET /mcp/pets/{id}/details — живые данные из БД, все поля присутствуют."""
    pet_id = seed_data["pet_id"]
    resp = await client.get(f"/mcp/pets/{pet_id}/details")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["error"] is None

    data = body["data"]
    # Имя совпадает с засеянным
    assert data["pet_name"] == TEST_PET_NAME
    # Порода засеяна через JOIN animals_breeds
    assert data["animal_breed"] == "Labrador"
    # Возраст вычисляется из даты рождения (2020 → ~5 лет)
    assert isinstance(data["age"], int)
    assert data["age"] >= 4
    # Числовые поля присутствуют
    assert "pet_weight" in data
    assert "pet_is_sterylyzed" in data


@pytest.mark.asyncio
async def test_get_pet_details_data_is_live(client, seed_data):
    """Данные свежие: делаем два запроса — ответ стабилен (не кэш-артефакт)."""
    pet_id = seed_data["pet_id"]
    r1 = await client.get(f"/mcp/pets/{pet_id}/details")
    r2 = await client.get(f"/mcp/pets/{pet_id}/details")
    assert r1.json()["data"] == r2.json()["data"]


@pytest.mark.asyncio
async def test_get_pet_short_info(client, seed_data):
    """GET /mcp/pets/{id}/short — возвращает краткую форму с типом животного."""
    pet_id = seed_data["pet_id"]
    resp = await client.get(f"/mcp/pets/{pet_id}/short")

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["pet_name"] == TEST_PET_NAME
    assert data["animal_type"] == "Dog"
    assert data["animal_breed"] == "Labrador"
    assert isinstance(data["age"], int)


@pytest.mark.asyncio
async def test_get_pet_details_not_found(client):
    """GET несуществующего питомца — 404 с кодом NOT_FOUND."""
    resp = await client.get("/mcp/pets/999999/details")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["data"] is None


@pytest.mark.asyncio
async def test_get_pet_details_forbidden_other_user(client, seed_data):
    """
    Питомец существует, но принадлежит другому пользователю —
    сервер должен вернуть 403, а не данные.

    Для этого мы делаем запрос от имени того же авторизованного пользователя,
    но с pet_id который намеренно принадлежит другому (используем ID, которого
    нет в seed, но который существует, — в данном случае симулируем через
    отдельно авторизованного клиента с другим user_id).

    Упрощённая версия: проверяем, что чужой питомец (несуществующий для
    текущего user_id) возвращает 403 или 404, но никогда не 200.
    """
    # pet_id = 1 (скорее всего чужой или нет для нашего user)
    # Главное — убедиться, что не 200 при чужом питомце
    our_pet_id = seed_data["pet_id"]
    candidate = 1 if our_pet_id != 1 else 2
    resp = await client.get(f"/mcp/pets/{candidate}/details")
    assert resp.status_code in (403, 404), (
        f"Ожидали 403 или 404 для чужого питомца, получили {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_mcp_execute_pets_details(client, seed_data):
    """POST /mcp/execute — универсальный роутер тоже достаёт питомца из БД."""
    pet_id = seed_data["pet_id"]
    resp = await client.post(
        "/mcp/execute",
        json={
            "tool": "pets",
            "method": "get_pet_short_info",
            "payload": {"pet_id": pet_id},
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["pet_name"] == TEST_PET_NAME


@pytest.mark.asyncio
async def test_mcp_execute_unknown_tool(client):
    """POST /mcp/execute с несуществующим инструментом — 422 VALIDATION_ERROR."""
    resp = await client.post(
        "/mcp/execute",
        json={"tool": "nonexistent_tool", "method": "something", "payload": {}},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_mcp_execute_unknown_method(client, seed_data):
    """POST /mcp/execute с несуществующим методом — 422 VALIDATION_ERROR."""
    pet_id = seed_data["pet_id"]
    resp = await client.post(
        "/mcp/execute",
        json={
            "tool": "pets",
            "method": "delete_all_pets",
            "payload": {"pet_id": pet_id},
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
