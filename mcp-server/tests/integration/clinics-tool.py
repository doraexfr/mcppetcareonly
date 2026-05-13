"""
TC-04 · Инструмент «clinics» — реальные данные из PostgreSQL

Проверяем, что:
  - поиск клиник по городу тянет данные из vet_clinics
  - поиск по геолокации правильно фильтрует и сортирует по расстоянию
  - фильтр по доступности проверяет working_hours
  - контакты клиники по ID возвращают phone/website
  - локация по имени возвращает координаты
"""

from __future__ import annotations

from datetime import datetime

import pytest

from tests.integration.conftest import TEST_CLINIC_CITY, TEST_CLINIC_NAME


@pytest.mark.asyncio
async def test_search_clinics_by_city(client, seed_data):
    """GET /mcp/clinics/city?vet_city=... — живые данные из vet_clinics."""
    resp = await client.get(
        "/mcp/clinics/city",
        params={"vet_city": TEST_CLINIC_CITY},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["error"] is None

    clinics = body["data"]
    assert isinstance(clinics, list)
    assert len(clinics) >= 1

    names = [c["vet_name"] for c in clinics]
    assert TEST_CLINIC_NAME in names, (
        f"Клиника {TEST_CLINIC_NAME!r} не найдена в результатах: {names}"
    )


@pytest.mark.asyncio
async def test_search_clinics_city_case_insensitive(client, seed_data):
    """Поиск по городу регистронезависимый (LOWER в запросе)."""
    resp_upper = await client.get(
        "/mcp/clinics/city",
        params={"vet_city": TEST_CLINIC_CITY.upper()},
    )
    resp_lower = await client.get(
        "/mcp/clinics/city",
        params={"vet_city": TEST_CLINIC_CITY.lower()},
    )
    assert resp_upper.status_code == 200
    assert resp_lower.status_code == 200
    # Оба запроса должны вернуть одинаковые данные
    assert resp_upper.json()["data"] == resp_lower.json()["data"]


@pytest.mark.asyncio
async def test_search_clinics_city_not_found(client):
    """Город без клиник — пустой список, не ошибка."""
    resp = await client.get(
        "/mcp/clinics/city",
        params={"vet_city": "CityThatDoesNotExist12345"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_search_clinics_by_location(client, seed_data):
    """
    GET /mcp/clinics/location — геопоиск через haversine.

    Клиника засеяна в координатах Москвы (55.7558, 37.6176).
    Запрос с радиусом 5 км от тех же координат — она должна попасть в результат.
    """
    resp = await client.get(
        "/mcp/clinics/location",
        params={"user_lat": 55.7558, "user_lon": 37.6176, "radius_km": 5.0},
    )
    assert resp.status_code == 200, resp.text
    clinics = resp.json()["data"]
    assert isinstance(clinics, list)

    names = [c["vet_name"] for c in clinics]
    assert TEST_CLINIC_NAME in names

    # Результаты отсортированы по distance_km
    distances = [c["distance_km"] for c in clinics]
    assert distances == sorted(distances), "Клиники не отсортированы по расстоянию"

    # Засеянная клиника в 0 км от себя
    our = next(c for c in clinics if c["vet_name"] == TEST_CLINIC_NAME)
    assert our["distance_km"] < 0.1


@pytest.mark.asyncio
async def test_search_clinics_by_location_outside_radius(client, seed_data):
    """Клиника за пределами радиуса — не попадает в результат."""
    # Координаты Владивостока — ~6400 км от Москвы
    resp = await client.get(
        "/mcp/clinics/location",
        params={"user_lat": 43.1155, "user_lon": 131.8855, "radius_km": 10.0},
    )
    assert resp.status_code == 200
    names = [c["vet_name"] for c in resp.json()["data"]]
    assert TEST_CLINIC_NAME not in names


@pytest.mark.asyncio
async def test_filter_available_clinics_open_now(client, seed_data):
    """
    POST /mcp/clinics/filter-available — фильтрует клиники по working_hours.

    Клиника работает 09:00-18:00. Проверяем с временем 12:00 — она должна быть в результате.
    """
    resp = await client.post(
        "/mcp/clinics/filter-available",
        json={
            "vet_city": TEST_CLINIC_CITY,
            "current_datetime": "2026-05-08T12:00:00",
        },
    )
    assert resp.status_code == 200, resp.text
    clinics = resp.json()["data"]
    names = [c["vet_name"] for c in clinics]
    assert TEST_CLINIC_NAME in names


@pytest.mark.asyncio
async def test_filter_available_clinics_closed(client, seed_data):
    """
    Та же клиника в 23:00 — она закрыта, не должна попасть в результат
    (если только не vet_is_24_7).
    """
    resp = await client.post(
        "/mcp/clinics/filter-available",
        json={
            "vet_city": TEST_CLINIC_CITY,
            "current_datetime": "2026-05-08T23:00:00",
        },
    )
    assert resp.status_code == 200
    clinics = resp.json()["data"]
    names = [c["vet_name"] for c in clinics]
    assert TEST_CLINIC_NAME not in names


@pytest.mark.asyncio
async def test_get_vet_contacts(client, seed_data):
    """GET /mcp/clinics/{id}/contacts — возвращает phone и website из БД."""
    clinic_id = seed_data["clinic_id"]
    resp = await client.get(f"/mcp/clinics/{clinic_id}/contacts")

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["vet_phone"] == "+7-999-000-00-01"
    assert data["vet_website"] == "https://integration-vet.example.com"


@pytest.mark.asyncio
async def test_get_vet_contacts_not_found(client):
    """Несуществующий vet_id — 404 NOT_FOUND."""
    resp = await client.get("/mcp/clinics/999999/contacts")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_vet_location_by_name(client, seed_data):
    """GET /mcp/clinics/location-by-name — координаты клиники по имени и городу."""
    resp = await client.get(
        "/mcp/clinics/location-by-name",
        params={"vet_name": TEST_CLINIC_NAME, "vet_city": TEST_CLINIC_CITY},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert abs(float(data["vet_lat"]) - 55.7558) < 0.001
    assert abs(float(data["vet_lon"]) - 37.6176) < 0.001


@pytest.mark.asyncio
async def test_get_vet_location_not_found(client):
    """Клиника с таким именем не существует — 404."""
    resp = await client.get(
        "/mcp/clinics/location-by-name",
        params={"vet_name": "NoSuchClinic", "vet_city": "NoSuchCity"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"
