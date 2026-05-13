"""
TC-03 · Инструмент «documents» — реальные данные из PostgreSQL + MinIO

Проверяем, что:
  - /mcp/pets/{id}/documents возвращает список документов из БД
  - /mcp/pets/{id}/documents/by-date фильтрует по дате загрузки
  - POST /mcp/documents/extract скачивает файл из MinIO и возвращает текст
  - содержимое документа совпадает с тем, что мы загрузили в S3
  - несуществующий документ — 404
  - чужой питомец — 403
"""

from __future__ import annotations

import pytest

from tests.integration.conftest import (
    TEST_DOCUMENT_CONTENT,
    TEST_DOCUMENT_CUSTOM_NAME,
    TEST_PET_NAME,
)


@pytest.mark.asyncio
async def test_get_pet_documents_from_db(client, seed_data):
    """GET /mcp/pets/{id}/documents — список документов тянется из pet_documents."""
    pet_id = seed_data["pet_id"]
    resp = await client.get(f"/mcp/pets/{pet_id}/documents")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["error"] is None

    docs = body["data"]
    assert isinstance(docs, list)
    assert len(docs) >= 1

    # Засеянный документ должен быть в списке
    names = [d["custom_name"] for d in docs]
    assert TEST_DOCUMENT_CUSTOM_NAME in names, (
        f"Документ {TEST_DOCUMENT_CUSTOM_NAME!r} не найден в списке: {names}"
    )

    # Каждый документ содержит нужные поля
    our_doc = next(d for d in docs if d["custom_name"] == TEST_DOCUMENT_CUSTOM_NAME)
    assert "document_type" in our_doc


@pytest.mark.asyncio
async def test_get_pet_documents_by_date(client, seed_data):
    """GET /mcp/pets/{id}/documents/by-date — фильтрация по дате загрузки."""
    pet_id = seed_data["pet_id"]
    from datetime import date
    today = date.today().isoformat()

    resp = await client.get(
        f"/mcp/pets/{pet_id}/documents/by-date",
        params={"uploaded_at": today},
    )
    assert resp.status_code == 200, resp.text
    docs = resp.json()["data"]
    assert isinstance(docs, list)
    # Документ засеян сейчас — должен попасть в результат
    names = [d["custom_name"] for d in docs]
    assert TEST_DOCUMENT_CUSTOM_NAME in names


@pytest.mark.asyncio
async def test_get_pet_documents_by_date_wrong_format(client, seed_data):
    """Невалидный формат даты — 422."""
    pet_id = seed_data["pet_id"]
    resp = await client.get(
        f"/mcp/pets/{pet_id}/documents/by-date",
        params={"uploaded_at": "not-a-date"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_extract_document_text_from_s3(client, seed_data):
    """
    POST /mcp/documents/extract — сервер скачивает файл из MinIO
    и возвращает текстовое содержимое.

    Это ключевой тест интеграции с S3: содержимое в ответе
    должно совпадать с тем, что мы загрузили в conftest.
    """
    pet_id = seed_data["pet_id"]
    resp = await client.post(
        "/mcp/documents/extract",
        json={"pet_id": pet_id, "custom_name": TEST_DOCUMENT_CUSTOM_NAME},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["error"] is None

    data = body["data"]
    assert data["custom_name"] == TEST_DOCUMENT_CUSTOM_NAME
    assert "parsed_text" in data

    # Текст должен совпадать с тем, что лежит в MinIO
    expected_text = TEST_DOCUMENT_CONTENT.decode("utf-8")
    assert data["parsed_text"] == expected_text, (
        f"Содержимое документа не совпадает с S3-объектом.\n"
        f"Ожидали: {expected_text!r}\n"
        f"Получили: {data['parsed_text']!r}"
    )


@pytest.mark.asyncio
async def test_extract_document_not_found(client, seed_data):
    """Запрос несуществующего документа — 404 NOT_FOUND."""
    pet_id = seed_data["pet_id"]
    resp = await client.post(
        "/mcp/documents/extract",
        json={"pet_id": pet_id, "custom_name": "does-not-exist-at-all"},
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["data"] is None


@pytest.mark.asyncio
async def test_extract_document_wrong_pet(client, seed_data):
    """Запрос документа для чужого питомца — 403 или 404, никогда не 200."""
    our_pet_id = seed_data["pet_id"]
    other_pet_id = 999999
    resp = await client.post(
        "/mcp/documents/extract",
        json={"pet_id": other_pet_id, "custom_name": TEST_DOCUMENT_CUSTOM_NAME},
    )
    assert resp.status_code in (403, 404), (
        f"Ожидали 403/404 для чужого питомца, получили {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_documents_list_empty_for_past_date(client, seed_data):
    """Дата в прошлом (до засева данных) — список пустой, не ошибка."""
    pet_id = seed_data["pet_id"]
    resp = await client.get(
        f"/mcp/pets/{pet_id}/documents/by-date",
        params={"uploaded_at": "2000-01-01"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == []
