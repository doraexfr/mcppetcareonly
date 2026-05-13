from datetime import datetime, time
from math import asin, cos, radians, sin, sqrt
from typing import Any, Dict, List

from app.core.exceptions import NotFoundError
from app.repository.clinics_repo import ClinicsRepository


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * radius * asin(sqrt(a))


def _parse_time(value: str) -> time:
    return datetime.strptime(value.strip(), "%H:%M").time()


def is_open_at(working_hours: str | None, current: datetime) -> bool:
    if not working_hours:
        return False
    normalized = working_hours.strip().replace("–", "-")
    if normalized.lower() in {"круглосуточно", "24/7", "24x7"}:
        return True

    current_time = current.time()
    intervals = [part.strip() for part in normalized.replace(",", ";").split(";") if part.strip()]
    for interval in intervals:
        if "-" not in interval:
            continue
        start_text, end_text = interval.split("-", 1)
        start = _parse_time(start_text)
        end = _parse_time(end_text)
        if start <= end and start <= current_time <= end:
            return True
        if start > end and (current_time >= start or current_time <= end):
            return True
    return False


class ClinicsService:
    def __init__(self, clinics_repo: ClinicsRepository) -> None:
        self.clinics_repo = clinics_repo

    async def search_vet_clinics_by_city(self, vet_city: str) -> List[Dict[str, Any]]:
        return await self.clinics_repo.search_by_city(vet_city)

    async def search_vet_clinics_by_location(
        self,
        user_lat: float,
        user_lon: float,
        radius_km: float,
    ) -> List[Dict[str, Any]]:
        clinics = await self.clinics_repo.list_active()
        results: List[Dict[str, Any]] = []
        for clinic in clinics:
            if clinic.get("vet_lat") is None or clinic.get("vet_lon") is None:
                continue
            distance_km = haversine_km(user_lat, user_lon, float(clinic["vet_lat"]), float(clinic["vet_lon"]))
            if distance_km <= radius_km:
                item = dict(clinic)
                item["distance_km"] = round(distance_km, 3)
                results.append(item)
        return sorted(results, key=lambda item: item["distance_km"])

    async def filter_available_vet_clinics(
        self,
        current_datetime: datetime,
        vet_city: str | None = None,
        user_lat: float | None = None,
        user_lon: float | None = None,
        radius_km: float | None = None,
    ) -> List[Dict[str, Any]]:
        if user_lat is not None and user_lon is not None and radius_km is not None:
            clinics = await self.search_vet_clinics_by_location(user_lat, user_lon, radius_km)
        elif vet_city is not None:
            clinics = await self.search_vet_clinics_by_city(vet_city)
        else:
            clinics = await self.clinics_repo.list_active()

        return [
            clinic
            for clinic in clinics
            if clinic.get("vet_is_24_7") is True or is_open_at(clinic.get("vet_working_hours"), current_datetime)
        ]

    async def get_vet_contacts_by_address(self, vet_id: int) -> Dict[str, Any]:
        clinic = await self.clinics_repo.get_active_by_id(vet_id)
        if clinic is None:
            raise NotFoundError("Clinic not found")
        return {"vet_phone": clinic["vet_phone"], "vet_website": clinic["vet_website"]}

    async def get_vet_location_by_name(self, vet_name: str, vet_city: str) -> Dict[str, Any]:
        clinic = await self.clinics_repo.get_active_location_by_name(vet_name, vet_city)
        if clinic is None:
            raise NotFoundError("Clinic not found")
        return clinic
