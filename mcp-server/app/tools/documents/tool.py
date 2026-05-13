from datetime import date
from typing import Any, Dict, List

from app.core.exceptions import ValidationAppError
from app.mcp.registry import ToolDependencies
from app.repository.documents_repo import DocumentsRepository
from app.services.documents_service import DocumentsService


class DocumentsTool:
    name = "documents"

    def __init__(self, documents_service: DocumentsService) -> None:
        self.documents_service = documents_service

    async def get_pet_documents(self, pet_id: int, user_id: str) -> List[Dict[str, Any]]:
        return await self.documents_service.get_pet_documents(pet_id, user_id)

    async def get_pet_documents_by_upload_date(
        self,
        pet_id: int,
        user_id: str,
        uploaded_at: date | str,
    ) -> List[Dict[str, Any]]:
        if isinstance(uploaded_at, str):
            try:
                uploaded_at = date.fromisoformat(uploaded_at)
            except ValueError as exc:
                raise ValidationAppError("uploaded_at must be an ISO date") from exc
        return await self.documents_service.get_pet_documents_by_upload_date(pet_id, user_id, uploaded_at)

    async def extract_pet_document_text_by_custom_name(
        self,
        pet_id: int,
        user_id: str,
        custom_name: str,
    ) -> Dict[str, Any]:
        return await self.documents_service.extract_pet_document_text_by_custom_name(pet_id, user_id, custom_name)


def create_tool(dependencies: ToolDependencies) -> DocumentsTool:
    documents_repo = DocumentsRepository(dependencies.db)
    return DocumentsTool(DocumentsService(documents_repo, dependencies.pets_repo, dependencies.storage_client))
