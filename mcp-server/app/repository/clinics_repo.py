from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class ClinicsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search_by_city(self, vet_city: str) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            text(
                """
                SELECT *
                FROM vet_clinics
                WHERE vet_status = 'active'
                  AND LOWER(vet_city) = LOWER(:vet_city)
                ORDER BY vet_name
                """
            ),
            {"vet_city": vet_city},
        )
        return [dict(row) for row in result.mappings().all()]

    async def list_active(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            text(
                """
                SELECT *
                FROM vet_clinics
                WHERE vet_status = 'active'
                """
            )
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_active_by_id(self, vet_id: int) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            text(
                """
                SELECT *
                FROM vet_clinics
                WHERE vet_status = 'active'
                  AND vet_id = :vet_id
                """
            ),
            {"vet_id": vet_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def get_active_location_by_name(self, vet_name: str, vet_city: str) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            text(
                """
                SELECT
                    vet_city,
                    vet_streets,
                    vet_building_number,
                    vet_lat,
                    vet_lon
                FROM vet_clinics
                WHERE vet_status = 'active'
                  AND LOWER(vet_name) = LOWER(:vet_name)
                  AND LOWER(vet_city) = LOWER(:vet_city)
                """
            ),
            {"vet_name": vet_name, "vet_city": vet_city},
        )
        row = result.mappings().first()
        return dict(row) if row else None

