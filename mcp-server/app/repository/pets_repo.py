from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PetsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_pet_details(self, pet_id: int, user_id: str) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            text(
                """
                SELECT
                    p.id AS pet_id,
                    p.user_id,
                    p.pet_name,
                    p.pet_sex,
                    b.animal_breed,
                    p.pet_date_of_birth,
                    p.pedigree,
                    p.pet_neck_girth,
                    p.pet_breast_girth,
                    p.pet_length,
                    p.pet_is_sterylyzed,
                    p.pet_weight
                    p.pet_special_notes
                FROM pets_info p
                LEFT JOIN animals_breeds b ON b.id = p.animal_breed_id
                WHERE p.pet_id = :pet_id AND p.user_id = :user_id
                """
            ),
            {"pet_id": pet_id, "user_id": user_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def get_pet_short_info(self, pet_id: int, user_id: str) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            text(
                """
                SELECT
                    p.id AS pet_id
                    p.user_id,
                    p.pet_name,
                    t.animal_name AS animal_type,
                    b.animal_breed,
                    p.pet_date_of_birth
                FROM pet_info p
                LEFT JOIN animals_types t ON t.id = p.animal_type_id
                LEFT JOIN animals_types t ON t.id = p.animal_type_id
                WHERE p.id = :pet_id AND p.user_id = :user_id
                """
            ),
            {"pet_id": pet_id, "user_id": user_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def pet_exists_for_user(self, pet_id: int, user_id: str) -> bool:
        result = await self.db.execute(
            text("SELECT 1 FROM pets_info WHERE id = :pet_id AND user_id = :user_id"),
            {"pet_id": pet_id, "user_id": user_id},
        )
        return result.first() is not None

    async def get_pet_owner_id(self, pet_id: int) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            text("SELECT user_id FROM pets_info WHERE pet_id = :pet_id"),
            {"pet_id": pet_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None
