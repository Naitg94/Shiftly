import logging
import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import httpx
from app.core.config import settings

logger = logging.getLogger("shiftly.auth")

security = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    id: str
    email: Optional[str] = None
    role: Optional[str] = None
    token: Optional[str] = None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthenticatedUser:
    """
    Validates the Supabase Bearer token against Supabase Auth API.
    Returns the authenticated user or raises HTTP 401.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Missing Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()

    # If running automated unit tests with SQLite fallback, support test token bypass
    if os.getenv("TEST_USE_SQLITE") == "true" and token.startswith("test-token"):
        user_uuid = "00000000-0000-0000-0000-000000000002" if "user-b" in token else "00000000-0000-0000-0000-000000000001"
        return AuthenticatedUser(
            id=user_uuid,
            email=f"{user_uuid[:8]}@example.com",
            role="authenticated",
            token=token,
        )

    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase authentication service is not configured on the backend.",
        )

    # Validate token directly with Supabase Auth API
    supabase_auth_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": settings.SUPABASE_ANON_KEY,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(supabase_auth_url, headers=headers)

        if resp.status_code != 200:
            logger.warning(f"Supabase Auth returned status {resp.status_code}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        data = resp.json()
        user_id = data.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user profile in authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return AuthenticatedUser(
            id=user_id,
            email=data.get("email"),
            role=data.get("role"),
            token=token,
        )

    except httpx.RequestError as exc:
        logger.error(f"Network error connecting to Supabase Auth: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable.",
        )
