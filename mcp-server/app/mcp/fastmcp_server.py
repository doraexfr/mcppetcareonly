from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import AsyncIterator

from fastmcp import FastMCP

from app.core.config import settings
from app.infrastructure.db.session import AsyncSessionLocal
from app.infrastructure.storage.s3_client import S3StorageClient
from app.repository.clinics_repo import ClinicsRepository
from app.repository.documents_repo import DocumentsRepository
from app.repository.pets_repo import PetsRepository
from app.services.assistant_service import AssistantService
from app.services.clinics_service import ClinicsService
from app.services.documents_service import DocumentsService
from app.services.pets_service import PetsService


@asynccontextmanager
async def _service_scope() -> AsyncIterator[dict[str, object]]:
    async with AsyncSessionLocal() as db:
        storage_client = S3StorageClient()
        pets_repo = PetsRepository(db)
        documents_repo = DocumentsRepository(db)
        clinics_repo = ClinicsRepository(db)
        pets_service = PetsService(pets_repo)
        documents_service = DocumentsService(documents_repo, pets_repo, storage_client)
        clinics_service = ClinicsService(clinics_repo)
        assistant_service = AssistantService(pets_service, documents_service, clinics_service)
        yield {
            "pets": pets_service,
            "documents": documents_service,
            "clinics": clinics_service,
            "assistant": assistant_service,
        }


def create_fastmcp_server() -> FastMCP:
    mcp = FastMCP(
        name=f"{settings.APP_NAME} MCP",
        instructions=(
            "Use these tools only for pet-care workflows. "
            "Pets and documents are protected by user ownership. "
            "Clinics data includes only active veterinary clinics."
        ),
    )

    @mcp.tool(name="pets_get_pet_details")
    async def pets_get_pet_details(pet_id: int, user_id: str) -> dict:
        """Get detailed pet information for a specific owner."""
        async with _service_scope() as services:
            return await services["pets"].get_pet_details(pet_id, user_id)  # type: ignore[union-attr]

    @mcp.tool(name="pets_get_pet_short_info")
    async def pets_get_pet_short_info(pet_id: int, user_id: str) -> dict:
        """Get short pet information for a specific owner."""
        async with _service_scope() as services:
            return await services["pets"].get_pet_short_info(pet_id, user_id)  # type: ignore[union-attr]

    @mcp.tool(name="documents_get_pet_documents")
    async def documents_get_pet_documents(pet_id: int, user_id: str) -> list[dict]:
        """List documents for a pet owned by the specified user."""
        async with _service_scope() as services:
            return await services["documents"].get_pet_documents(pet_id, user_id)  # type: ignore[union-attr]

    @mcp.tool(name="documents_get_pet_documents_by_upload_date")
    async def documents_get_pet_documents_by_upload_date(
        pet_id: int,
        user_id: str,
        uploaded_at: str,
    ) -> list[dict]:
        """List pet documents filtered by upload date."""
        async with _service_scope() as services:
            return await services["documents"].get_pet_documents_by_upload_date(  # type: ignore[union-attr]
                pet_id,
                user_id,
                date.fromisoformat(uploaded_at),
            )

    @mcp.tool(name="documents_extract_pet_document_text_by_custom_name")
    async def documents_extract_pet_document_text_by_custom_name(
        pet_id: int,
        user_id: str,
        custom_name: str,
    ) -> dict:
        """Download a pet document from storage and return decoded text."""
        async with _service_scope() as services:
            return await services["documents"].extract_pet_document_text_by_custom_name(  # type: ignore[union-attr]
                pet_id,
                user_id,
                custom_name,
            )

    @mcp.tool(name="clinics_search_vet_clinics_by_city")
    async def clinics_search_vet_clinics_by_city(vet_city: str) -> list[dict]:
        """Search active veterinary clinics by city."""
        async with _service_scope() as services:
            return await services["clinics"].search_vet_clinics_by_city(vet_city)  # type: ignore[union-attr]

    @mcp.tool(name="clinics_search_vet_clinics_by_location")
