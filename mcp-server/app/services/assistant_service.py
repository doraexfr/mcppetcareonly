from typing import Any, Dict, List

from app.core.exceptions import ValidationAppError
from app.llm.selector import llm_selector
from app.services.clinics_service import ClinicsService
from app.services.documents_service import DocumentsService
from app.services.pets_service import PetsService


class AssistantService:
    def __init__(
        self,
        pets_service: PetsService,
        documents_service: DocumentsService,
        clinics_service: ClinicsService,
    ) -> None:
        self.pets_service = pets_service
        self.documents_service = documents_service
        self.clinics_service = clinics_service

    async def ask_petcare_assistant(
        self,
        question: str,
        user_id: str | None = None,
        pet_id: int | None = None,
        vet_city: str | None = None,
        include_documents: bool = True,
        llm_name: str | None = None,
    ) -> Dict[str, Any]:
        self._validate_domain(question, pet_id=pet_id, vet_city=vet_city)

        context: Dict[str, Any] = {"question": question}
        if pet_id is not None:
            if not user_id:
                raise ValidationAppError("user_id is required when pet_id is provided")
            context["pet"] = await self.pets_service.get_pet_details(pet_id, user_id)
            if include_documents:
                context["documents"] = await self.documents_service.get_pet_documents(pet_id, user_id)

        if vet_city:
            context["clinics"] = await self.clinics_service.search_vet_clinics_by_city(vet_city)

        prompt = self._build_prompt(question, context)
        adapter = llm_selector.select(llm_name)
        answer = await adapter.complete(prompt=prompt, context=context)
        return {
            "model": adapter.name,
            "question": question,
            "answer": answer,
            "context": context,
        }

    def _validate_domain(self, question: str, pet_id: int | None, vet_city: str | None) -> None:
        if pet_id is not None or vet_city:
            return
        petcare_keywords = (
            "питом",
            "pet",
            "собак",
            "кошк",
            "вет",
            "клиник",
            "документ",
            "привив",
            "animal",
            "breed",
        )
        if any(keyword in question.lower() for keyword in petcare_keywords):
            return
        raise ValidationAppError("Assistant tool only supports pet-care related questions")

    def _build_prompt(self, question: str, context: Dict[str, Any]) -> str:
        return (
            "You are a pet-care assistant. "
            "Answer only using pet-care context provided by the MCP backend. "
            "If context is incomplete, say what data is missing.\n\n"
            f"User question: {question}\n"
            f"Structured context: {context}"
        )
