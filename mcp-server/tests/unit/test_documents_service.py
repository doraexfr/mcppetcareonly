"""Юнит-тесты: DocumentsService."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ForbiddenError, NotFoundError
from app.infrastructure.storage.s3_client import S3Object
from app.services.documents_service import DocumentsService
from tests.unit.conftest import (
    make_document_row,
    make_s3_object,
    mock_documents_repo,
    mock_pets_repo,
    mock_s3_client,
)


def make_service(
    documents=None,
    document=None,
    pet_exists=True,
    owner_id="user-1",
    s3_obj=None,
):
    return DocumentsService(
        documents_repo=mock_documents_repo(documents=documents, document=document),
        pets_repo=mock_pets_repo(pet_exists=pet_exists, owner_id=owner_id),
        storage_client=mock_s3_client(s3_obj=s3_obj),
    )


# ── get_pet_documents ─────────────────────────────────────────────────────────

class TestGetPetDocuments:
    @pytest.mark.asyncio
    async def test_returns_list_from_repo(self):
        docs = [make_document_row(), make_document_row(document_id=2, custom_name="passport")]
        service = make_service(documents=docs)

        result = await service.get_pet_documents(pet_id=1, user_id="user-1")

        assert len(result) == 2
        assert result[0]["custom_name"] == "vaccine-cert"
        assert result[1]["custom_name"] == "passport"

    @pytest.mark.asyncio
    async def test_empty_list_when_no_documents(self):
        service = make_service(documents=[])

        result = await service.get_pet_documents(pet_id=1, user_id="user-1")

        assert result == []

    @pytest.mark.asyncio
    async def test_forbidden_when_not_owner(self):
        service = make_service(pet_exists=False, owner_id="other-user")

        with pytest.raises(ForbiddenError):
            await service.get_pet_documents(pet_id=1, user_id="user-1")

    @pytest.mark.asyncio
    async def test_not_found_when_pet_missing(self):
        service = make_service(pet_exists=False, owner_id=None)

        with pytest.raises(NotFoundError):
            await service.get_pet_documents(pet_id=999, user_id="user-1")

    @pytest.mark.asyncio
    async def test_ownership_checked_before_db_query(self):
        """_ensure_pet_owner вызывается до запроса к documents_repo."""
        pets_repo = mock_pets_repo(pet_exists=False, owner_id=None)
        docs_repo = mock_documents_repo()
        service = DocumentsService(docs_repo, pets_repo, mock_s3_client())

        with pytest.raises(NotFoundError):
            await service.get_pet_documents(pet_id=999, user_id="user-1")

        docs_repo.get_pet_documents.assert_not_awaited()


# ── get_pet_documents_by_upload_date ─────────────────────────────────────────

class TestGetDocumentsByDate:
    @pytest.mark.asyncio
    async def test_passes_date_to_repo(self):
        docs_repo = mock_documents_repo(documents=[])
        service = DocumentsService(
            docs_repo,
            mock_pets_repo(pet_exists=True),
            mock_s3_client(),
        )
        target_date = date(2025, 1, 15)

        await service.get_pet_documents_by_upload_date(
            pet_id=1, user_id="user-1", uploaded_at=target_date
        )

        docs_repo.get_pet_documents_by_upload_date.assert_awaited_once_with(
            1, "user-1", target_date
        )

    @pytest.mark.asyncio
    async def test_forbidden_before_date_query(self):
        docs_repo = mock_documents_repo()
        service = DocumentsService(
            docs_repo,
            mock_pets_repo(pet_exists=False, owner_id="other"),
            mock_s3_client(),
        )

        with pytest.raises(ForbiddenError):
            await service.get_pet_documents_by_upload_date(
                pet_id=1, user_id="user-1", uploaded_at=date.today()
            )

        docs_repo.get_pet_documents_by_upload_date.assert_not_awaited()


# ── extract_pet_document_text_by_custom_name ──────────────────────────────────

class TestExtractDocumentText:
    @pytest.mark.asyncio
    async def test_returns_text_from_s3(self):
        content = b"Vaccine: Rabies\nDate: 2025-01-15"
        doc = make_document_row(object_key="pets/1/doc.txt")
        service = make_service(document=doc, s3_obj=make_s3_object(content))

        result = await service.extract_pet_document_text_by_custom_name(
            pet_id=1, user_id="user-1", custom_name="vaccine-cert"
        )

        assert result["custom_name"] == "vaccine-cert"
        assert result["parsed_text"] == content.decode("utf-8")

    @pytest.mark.asyncio
    async def test_uses_object_key_from_db(self):
        """S3-клиент вызывается с object_key из записи в БД."""
        doc = make_document_row(object_key="pets/1/special-path.pdf")
        s3 = mock_s3_client()
        service = DocumentsService(
            mock_documents_repo(document=doc),
            mock_pets_repo(pet_exists=True),
            s3,
        )

        await service.extract_pet_document_text_by_custom_name(
            pet_id=1, user_id="user-1", custom_name="vaccine-cert"
        )

        s3.download_object.assert_awaited_once_with("pets/1/special-path.pdf")

    @pytest.mark.asyncio
    async def test_document_not_found_in_db(self):
        """Запись в БД отсутствует → NotFoundError, S3 не вызывается."""
        s3 = mock_s3_client()
        service = DocumentsService(
            mock_documents_repo(document=None),
            mock_pets_repo(pet_exists=True),
            s3,
        )

        with pytest.raises(NotFoundError, match="Document not found"):
            await service.extract_pet_document_text_by_custom_name(
                pet_id=1, user_id="user-1", custom_name="no-such-doc"
            )

        s3.download_object.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_non_utf8_bytes_decoded_with_replace(self):
        """Байты с ошибками декодируются с errors='replace', не падают."""
        bad_content = b"Valid text \xff\xfe more text"
        doc = make_document_row()
        service = make_service(document=doc, s3_obj=make_s3_object(bad_content))

        result = await service.extract_pet_document_text_by_custom_name(
            pet_id=1, user_id="user-1", custom_name="vaccine-cert"
        )

        assert isinstance(result["parsed_text"], str)
        assert "Valid text" in result["parsed_text"]

    @pytest.mark.asyncio
    async def test_forbidden_for_other_user(self):
        service = make_service(pet_exists=False, owner_id="other-user")

        with pytest.raises(ForbiddenError):
            await service.extract_pet_document_text_by_custom_name(
                pet_id=1, user_id="user-1", custom_name="vaccine-cert"
            )
