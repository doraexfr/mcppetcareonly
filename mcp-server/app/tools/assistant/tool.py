from typing import Any, Dict

from app.mcp.registry import ToolDependencies
from app.repository.clinics_repo import ClinicsRepository
from app.repository.documents_repo import DocumentsRepository
from app.services.assistant_service import AssistantService
from app.services.clinics_service import ClinicsService
from app.services.documents_service import DocumentsService
from app.services.pets_service import PetsService


class AssistantTool:
    name = "assistant"

    def __init__(self, assistant_service: AssistantService) -> None:
        self.assistant_service = assistant_service

    async def ask_petcare_assistant(
        self,
        question: str,
        user_id: str | None = None,
        pet_id: int | None = None,
        vet_city: str | None = None,
        include_documents: bool = True,
        llm_name: str | None = None,
    ) -> Dict[str, Any]:
        return await self.assistant_service.ask_petcare_assistant(
            question=question,
            user_id=user_id,
            pet_id=pet_id,
            vet_city=vet_city,
            include_documents=include_documents,
            llm_name=llm_name,
        )


def create_tool(dependencies: ToolDependencies) -> AssistantTool:
    pets_service = PetsService(dependencies.pets_repo)
    documents_service = DocumentsService(
        DocumentsRepository(dependencies.db),
        dependencies.pets_repo,
        dependencies.storage_client,
    )
    clinics_service = ClinicsService(ClinicsRepository(dependencies.db))
    return AssistantTool(AssistantService(pets_service, documents_service, clinics_service))
