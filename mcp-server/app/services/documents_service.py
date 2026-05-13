from datetime import date
from typing import Any, Dict, List

from app.core.exceptions import ForbiddenError, NotFoundError
from app.infrastructure.storage.s3_client import S3StorageClient
from app.repository.documents_repo import DocumentsRepository
from app.repository.pets_repo import PetsRepository


class DocumentsService:
    def __init__(
        self,
        documents_repo: DocumentsRepository,
        pets_repo: PetsRepository,
        storage_client: S3StorageClient,
    ) -> None:
        self.documents_repo = documents_repo
        self.pets_repo = pets_repo
        self.storage_client = storage_client

    async def _ensure_pet_owner(self, pet_id: int, user_id: str) -> None:
        if await self.pets_repo.pet_exists_for_user(pet_id, user_id):
            return
        owner = await self.pets_repo.get_pet_owner_id(pet_id)
        if owner is None:
            raise NotFoundError("Pet not found")
        if owner["user_id"] is None:
            raise ForbiddenError("This pet is not assigned to any owner")
        raise ForbiddenError("You do not own this pet")

    async def get_pet_documents(self, pet_id: int, user_id: str) -> List[Dict[str, Any]]:
        await self._ensure_pet_owner(pet_id, user_id)
        return await self.documents_repo.get_pet_documents(pet_id, user_id)

    async def get_pet_documents_by_upload_date(
        self,
        pet_id: int,
        user_id: str,
        uploaded_at: date,
    ) -> List[Dict[str, Any]]:
        await self._ensure_pet_owner(pet_id, user_id)
        return await self.documents_repo.get_pet_documents_by_upload_date(pet_id, user_id, uploaded_at)

    async def extract_pet_document_text_by_custom_name(
        self,
        pet_id: int,
        user_id: str,
        custom_name: str,
    ) -> Dict[str, Any]:
        await self._ensure_pet_owner(pet_id, user_id)
        document = await self.documents_repo.get_document_for_pet_by_custom_name(pet_id, user_id, custom_name)
        if document is None:
            raise NotFoundError("Document not found")

        s3_object = await self.storage_client.download_object(document["object_key"])
        parsed_text = s3_object.body.decode("utf-8", errors="replace")
        return {"custom_name": document["custom_name"], "parsed_text": parsed_text}
