from datetime import date
from typing import Any, Dict

from app.core.exceptions import ForbiddenError, NotFoundError
from app.repository.pets_repo import PetsRepository


def calculate_age(birth_date: date | None) -> int | None:
    if birth_date is None:
        return None
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


class PetsService:
    def __init__(self, pets_repo: PetsRepository) -> None:
        self.pets_repo = pets_repo

    async def get_pet_details(self, pet_id: int, user_id: str) -> Dict[str, Any]:
        pet = await self.pets_repo.get_pet_details(pet_id, user_id)
        if pet is None:
            await self._raise_missing_or_forbidden(pet_id)
        return {
            "pet_name": pet["pet_name"],
            "pet_sex": pet["pet_sex"],
            "animal_breed": pet["animal_breed"],
            "age": calculate_age(pet["pet_date_of_birth"]),
            "pedigree": pet["pedigree"],
            "pet_neck_girth": pet["pet_neck_girth"],
            "pet_breast_girth": pet["pet_breast_girth"],
            "pet_length": pet["pet_length"],
            "pet_is_sterylyzed": pet["pet_is_sterylyzed"],
            "pet_weight": pet["pet_weight"],
            "pet_special_notes": pet["pet_special_notes"],
        }

    async def get_pet_short_info(self, pet_id: int, user_id: str) -> Dict[str, Any]:
        pet = await self.pets_repo.get_pet_short_info(pet_id, user_id)
        if pet is None:
            await self._raise_missing_or_forbidden(pet_id)
        return {
            "pet_name": pet["pet_name"],
            "animal_type": pet["animal_type"],
            "animal_breed": pet["animal_breed"],
            "age": calculate_age(pet["pet_date_of_birth"]),
        }

    async def _raise_missing_or_forbidden(self, pet_id: int) -> None:
        owner = await self.pets_repo.get_pet_own(pet_id)
        if owner is None:
            raise NotFoundError("Pet not found")
        if owner["user_id"] is None:
            raise ForbiddenError("This pet is not assigned to any owner") 
        raise ForbiddenError("You do not own this pet")
