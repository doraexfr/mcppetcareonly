from typing import Any, Dict

from app.mcp.registry import ToolDependencies
from app.services.pets_service import PetsService


class PetsTool:
    name = "pets"

    def __init__(self, pets_service: PetsService) -> None:
        self.pets_service = pets_service

    async def get_pet_details(self, pet_id: int, user_id: str) -> Dict[str, Any]:
        return await self.pets_service.get_pet_details(pet_id, user_id)

    async def get_pet_short_info(self, pet_id: int, user_id: str) -> Dict[str, Any]:
        return await self.pets_service.get_pet_short_info(pet_id, user_id)


def create_tool(dependencies: ToolDependencies) -> PetsTool:
    return PetsTool(PetsService(dependencies.pets_repo))
