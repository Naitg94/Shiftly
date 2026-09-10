from fastapi import APIRouter
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    gemini_configured: bool


@router.get("/health", response_model=HealthResponse, summary="Health Check Endpoint")
def get_health():
    return HealthResponse(
        status="ok",
        service="shiftly-backend",
        version=settings.VERSION,
        gemini_configured=bool(settings.GEMINI_API_KEY),
    )
