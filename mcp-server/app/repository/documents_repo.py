from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class DocumentsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_pet_documents(self, pet_id: int, user_id: str) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            text(
                """
                SELECT d.custom_name, dt.document_type
                FROM pet_documents d
                JOIN pets_info p ON p.pet_id = d.pet_id
                LEFT JOIN documents_types dt ON dt.document_type_id = d.document_type_id
                WHERE d.pet_id = :pet_id AND p.user_id = :user_id
                ORDER BY d.uploaded_at DESC
                """
            ),
            {"pet_id": pet_id, "user_id": user_id},
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_pet_documents_by_upload_date(
        self,
        pet_id: int,
        user_id: str,
        uploaded_at: date,
    ) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            text(
                """
                SELECT d.custom_name, dt.document_type
                FROM pet_documents d
                JOIN pets_info p ON p.pet_id = d.pet_id
                LEFT JOIN documents_types dt ON dt.document_type_id = d.document_type_id
                WHERE d.pet_id = :pet_id
                  AND p.user_id = :user_id
                  AND DATE(d.uploaded_at) = :uploaded_at
                ORDER BY d.uploaded_at DESC
                """
            ),
            {"pet_id": pet_id, "user_id": user_id, "uploaded_at": uploaded_at},
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_document_for_pet_by_custom_name(
        self,
        pet_id: int,
        user_id: str,
        custom_name: str,
    ) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            text(
                """
                SELECT
                    d.document_id,
                    d.pet_id,
                    d.custom_name,
                    d.object_key,
                    d.content_type,
                    d.size_bytes,
                    d.etag,
                    d.uploaded_at,
                    d.document_type_id
                FROM pet_documents d
                JOIN pets_info p ON p.pet_id = d.pet_id
                WHERE d.pet_id = :pet_id
                  AND p.user_id = :user_id
                  AND d.custom_name = :custom_name
                """
            ),
            {"pet_id": pet_id, "user_id": user_id, "custom_name": custom_name},
        )
        row = result.mappings().first()
        return dict(row) if row else None

