from datetime import datetime
from typing import Any, Dict, List

from app.core.exceptions import ValidationAppError
from app.mcp.registry import ToolDependencies
from app.repository.clinics_repo import ClinicsRepository
from app.services.clinics_service import ClinicsService


class ClinicsTool:
    name = "clinics"

    def __init__(self, clinics_service: ClinicsService) -> None:
        self.clinics_service = clinics_service

    async def search_vet_clinics_by_city(self, vet_city: str) -> List[Dict[str, Any]]:
        return await self.clinics_service.search_vet_clinics_by_city(vet_city)

    async def search_vet_clinics_by_location(
        self,
        user_lat: float,
        user_lon: float,
        radius_km: float,
    ) -> List[Dict[str, Any]]:
        return await self.clinics_service.search_vet_clinics_by_location(user_lat, user_lon, radius_km)

    async def filter_available_vet_clinics(
        self,
        current_datetime: datetime | str,
        vet_city: str | None = None,
        user_lat: float | None = None,
        user_lon: float | None = None,
        radius_km: float | None = None,
    ) -> List[Dict[str, Any]]:
        if isinstance(current_datetime, str):
            try:
                current_datetime = datetime.fromisoformat(current_datetime)
            except ValueError as exc:
                raise ValidationAppError("current_datetime must be an ISO datetime") from exc
        return await self.clinics_service.filter_available_vet_clinics(
            current_datetime=current_datetime,
            vet_city=vet_city,
            user_lat=user_lat,
            user_lon=user_lon,
            radius_km=radius_km,
        )

    async def get_vet_contacts_by_address(self, vet_id: int) -> Dict[str, Any]:
        return await self.clinics_service.get_vet_contacts_by_address(vet_id)

    async def get_vet_location_by_name(self, vet_name: str, vet_city: str) -> Dict[str, Any]:
        return await self.clinics_service.get_vet_location_by_name(vet_name, vet_city)


def create_tool(dependencies: ToolDependencies) -> ClinicsTool:
    return ClinicsTool(ClinicsService(ClinicsRepository(dependencies.db)))
