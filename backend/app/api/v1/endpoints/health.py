from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx
from app.core.config import settings
from app.db.repository import memory_repo

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    gemini_configured: bool


class ReadinessResponse(BaseModel):
    status: str
    service: str
    database: str
    gemini_configured: bool


@router.get("/health", response_model=HealthResponse, summary="Process Health Check")
def get_health():
    """
    Lightweight process liveness check.
    Returns 200 OK immediately as long as the FastAPI process is responsive.
    Does NOT make external network or database calls.
    """
    return HealthResponse(
        status="ok",
        service="shiftly-backend",
        version=settings.VERSION,
        gemini_configured=bool(settings.GEMINI_API_KEY),
    )


@router.get("/ready", summary="Dependency Readiness Check")
def get_readiness():
    """
    Dependency readiness probe.
    1. Probes database connectivity with a strict 2.0s timeout.
    2. Verifies Gemini API key presence without making expensive or quota-consuming AI calls.
    Returns 200 OK if dependencies are ready, 503 if database is unreachable.
    """
    db_status = "unknown"
    is_ready = True

    try:
        if memory_repo._active_sqlite_mode:
            import sqlite3
            from app.db.repository import LOCAL_DB_PATH
            conn = sqlite3.connect(LOCAL_DB_PATH, timeout=2.0)
            conn.execute("SELECT 1")
            conn.close()
            db_status = "connected"
        elif memory_repo.is_supabase_configured:
            url = f"{memory_repo.supabase_url}/rest/v1/projects?select=id&limit=1"
            headers = memory_repo._get_supabase_headers()
            res = httpx.get(url, headers=headers, timeout=2.0)
            if res.status_code == 200:
                db_status = "connected"
            else:
                db_status = f"degraded (HTTP {res.status_code})"
                is_ready = False
        else:
            db_status = "unconfigured"
            is_ready = False
    except httpx.TimeoutException:
        db_status = "timeout"
        is_ready = False
    except Exception:
        db_status = "unreachable"
        is_ready = False

    payload = {
        "status": "ready" if is_ready else "degraded",
        "service": "shiftly-backend",
        "database": db_status,
        "gemini_configured": bool(settings.GEMINI_API_KEY),
    }

    if is_ready:
        return JSONResponse(status_code=status.HTTP_200_OK, content=payload)
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)
