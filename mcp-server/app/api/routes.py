from datetime import date, datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import get_current_user_id
from app.core.config import settings
from app.core.exceptions import ValidationAppError, success_response
from app.core.security import create_access_token, verify_login_password
from app.infrastructure.db.session import get_db_session
from app.mcp.router import MCPRouter
from app.mcp.registry import build_tool_registry

router = APIRouter()


class LoginRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class MCPExecuteRequest(BaseModel):
    tool: str = Field(..., min_length=1)
    method: str = Field(..., min_length=1)
    payload: Dict[str, Any] = Field(default_factory=dict)


class DocumentExtractRequest(BaseModel):
    pet_id: int
    custom_name: str = Field(..., min_length=1)


class ClinicAvailabilityRequest(BaseModel):
    vet_city: Optional[str] = None
    user_lat: Optional[float] = None
    user_lon: Optional[float] = None
    radius_km: Optional[float] = Field(default=None, gt=0)
    current_datetime: datetime


async def get_mcp_router(db: AsyncSession = Depends(get_db_session)) -> MCPRouter:
    registry = build_tool_registry(db)
    return MCPRouter(registry)


@router.post("/auth/login")
async def login(request: LoginRequest) -> Dict[str, Any]:
    if not verify_login_password(request.password):
        raise ValidationAppError("Invalid credentials")
    token = create_access_token(subject=request.user_id)
    return success_response(
        {
            "access_token": token,
            "token_type": "bearer",
            "expires_in_minutes": settings.JWT_EXPIRE_MINUTES,
        }
    )


@router.get("/mcp/pets/{pet_id}/details")
async def get_pet_details(
    pet_id: int,
    user_id: str = Depends(get_current_user_id),
    mcp: MCPRouter = Depends(get_mcp_router),
) -> Dict[str, Any]:
    data = await mcp.execute("pets", "get_pet_details", {"pet_id": pet_id, "user_id": user_id})
    return success_response(data)


@router.get("/mcp/pets/{pet_id}/short")
async def get_pet_short_info(
    pet_id: int,
    user_id: str = Depends(get_current_user_id),
    mcp: MCPRouter = Depends(get_mcp_router),
) -> Dict[str, Any]:
    data = await mcp.execute("pets", "get_pet_short_info", {"pet_id": pet_id, "user_id": user_id})
    return success_response(data)


@router.get("/mcp/pets/{pet_id}/documents")
async def get_pet_documents(
    pet_id: int,
    user_id: str = Depends(get_current_user_id),
    mcp: MCPRouter = Depends(get_mcp_router),
) -> Dict[str, Any]:
    data = await mcp.execute("documents", "get_pet_documents", {"pet_id": pet_id, "user_id": user_id})
    return success_response(data)


@router.get("/mcp/pets/{pet_id}/documents/by-date")
async def get_pet_documents_by_upload_date(
    pet_id: int,
    uploaded_at: date = Query(...),
    user_id: str = Depends(get_current_user_id),
    mcp: MCPRouter = Depends(get_mcp_router),
) -> Dict[str, Any]:
    data = await mcp.execute(
        "documents",
        "get_pet_documents_by_upload_date",
        {"pet_id": pet_id, "user_id": user_id, "uploaded_at": uploaded_at},
    )
    return success_response(data)


@router.post("/mcp/documents/extract")
async def extract_pet_document_text(
    request: DocumentExtractRequest,
    user_id: str = Depends(get_current_user_id),
    mcp: MCPRouter = Depends(get_mcp_router),
) -> Dict[str, Any]:
    payload = request.model_dump()
    payload["user_id"] = user_id
    data = await mcp.execute("documents", "extract_pet_document_text_by_custom_name", payload)
    return success_response(data)


@router.get("/mcp/clinics/city")
async def search_vet_clinics_by_city(
    vet_city: str = Query(..., min_length=1),
    _: str = Depends(get_current_user_id),
    mcp: MCPRouter = Depends(get_mcp_router),
) -> Dict[str, Any]:
    data = await mcp.execute("clinics", "search_vet_clinics_by_city", {"vet_city": vet_city})
    return success_response(data)


@router.get("/mcp/clinics/location")
async def search_vet_clinics_by_location(
    user_lat: float = Query(...),
    user_lon: float = Query(...),
    radius_km: float = Query(..., gt=0),
    _: str = Depends(get_current_user_id),
    mcp: MCPRouter = Depends(get_mcp_router),
) -> Dict[str, Any]:
    data = await mcp.execute(
        "clinics",
        "search_vet_clinics_by_location",
        {"user_lat": user_lat, "user_lon": user_lon, "radius_km": radius_km},
    )
    return success_response(data)


@router.post("/mcp/clinics/filter-available")
async def filter_available_vet_clinics(
    request: ClinicAvailabilityRequest,
    _: str = Depends(get_current_user_id),
    mcp: MCPRouter = Depends(get_mcp_router),
) -> Dict[str, Any]:
    data = await mcp.execute("clinics", "filter_available_vet_clinics", request.model_dump())
    return success_response(data)


@router.get("/mcp/clinics/{vet_id}/contacts")
async def get_vet_contacts_by_address(
    vet_id: int,
    _: str = Depends(get_current_user_id),
    mcp: MCPRouter = Depends(get_mcp_router),
) -> Dict[str, Any]:
    data = await mcp.execute("clinics", "get_vet_contacts_by_address", {"vet_id": vet_id})
    return success_response(data)


@router.get("/mcp/clinics/location-by-name")
async def get_vet_location_by_name(
    vet_name: str = Query(..., min_length=1),
    vet_city: str = Query(..., min_length=1),
    _: str = Depends(get_current_user_id),
    mcp: MCPRouter = Depends(get_mcp_router),
) -> Dict[str, Any]:
    data = await mcp.execute(
        "clinics",
        "get_vet_location_by_name",
        {"vet_name": vet_name, "vet_city": vet_city},
    )
    return success_response(data)


@router.post("/mcp/execute")
async def execute_mcp_tool(
    request: MCPExecuteRequest,
    user_id: str = Depends(get_current_user_id),
    mcp: MCPRouter = Depends(get_mcp_router),
) -> Dict[str, Any]:
    payload = dict(request.payload)
    payload.setdefault("user_id", user_id)
    data = await mcp.execute(request.tool, request.method, payload)
    return success_response(data)

