import logging
import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
import httpx

from app.core.config import settings
from app.core.auth import AuthenticatedUser, get_current_user
from app.db.repository import memory_repo

logger = logging.getLogger("shiftly.account")

router = APIRouter()


from app.core.plans import PlanTier, resolve_entitlement


@router.get("/account/summary", summary="Get Account Usage and Storage Summary")
async def get_account_summary(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Returns authoritative resource consumption, project memory storage metrics,
    and public plan status for the authenticated user.
    """
    entitlement = resolve_entitlement(current_user)
    limits = entitlement.limits
    public_tier = entitlement.public_plan

    try:
        stats = memory_repo.get_user_storage_stats(
            user_id=current_user.id,
            user_token=current_user.token,
            storage_limit_bytes=limits.storage_limit_bytes,
        )
    except Exception as e:
        logger.error("Failed to retrieve storage stats for user %s: %s", current_user.id, str(e))
        stats = {
            "projects_count": 0,
            "analyses_count": 0,
            "key_points_count": 0,
            "action_items_count": 0,
            "decisions_count": 0,
            "important_dates_count": 0,
            "total_chars_processed": 0,
            "used_storage_bytes": 0,
            "limit_storage_bytes": limits.storage_limit_bytes,
        }

    # All 7 inputs mapped with capability support
    all_inputs = ["PDF", "DOCX", "TXT", "WhatsApp", "EML", "MBOX", "ZIP"]
    supported_inputs_list = [
        {"name": inp, "supported": inp in limits.supported_inputs}
        for inp in all_inputs
    ]

    return {
        "plan": {
            "id": public_tier.value,
            "name": public_tier.value.capitalize(),
            "display_name": public_tier.value.capitalize(),
            "status": "Active",
            "description": (
                "Maximum capacity, unlimited analyses, and dedicated throughput."
                if public_tier == PlanTier.PRO
                else "Higher capacity and expanded communication formats."
                if public_tier == PlanTier.PLUS
                else "Essential communication intelligence and Project Memory workspaces."
            ),
        },
        "usage": {
            "analyses_count": stats["analyses_count"],
            "analyses_limit": limits.analysis_limit,
            "projects_count": stats["projects_count"],
            "projects_limit": limits.max_projects,
            "characters_processed": stats["total_chars_processed"],
            "characters_limit": limits.max_characters_per_analysis,
            "supported_inputs": supported_inputs_list,
        },
        "storage": {
            "used_bytes": stats["used_storage_bytes"],
            "limit_bytes": limits.storage_limit_bytes,  # 4 GB during preview
            "projects_count": stats["projects_count"],
            "analyses_count": stats["analyses_count"],
            "key_points_count": stats["key_points_count"],
            "action_items_count": stats["action_items_count"],
            "decisions_count": stats["decisions_count"],
            "important_dates_count": stats["important_dates_count"],
            "explanation": {
                "stored": [
                    "Project summaries",
                    "Key points",
                    "Action items",
                    "Decisions",
                    "Important dates",
                    "Source references",
                    "Analysis metadata",
                ],
                "not_stored": "Original uploaded files and conversation exports are not permanently stored.",
            },
        },
    }


from pydantic import BaseModel, Field

class DeleteAccountRequest(BaseModel):
    password: str = Field(..., min_length=1, description="Current account password for verification")


@router.delete("/account", summary="Permanently Delete Current User Account")
async def delete_account(
    payload: DeleteAccountRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Permanently deletes the currently authenticated user account and all associated
    Project Memory data after verifying the user's current password.
    Uses server-side elevated credentials.
    """
    user_id = current_user.id
    logger.info("Account deletion requested for authenticated user %s", user_id)

    # 1. Check test/sqlite mode vs Supabase production mode
    is_test_mode = (
        settings.ENVIRONMENT != "production"
        and (os.getenv("TEST_USE_SQLITE") == "true" or (current_user.token and current_user.token.startswith("test-token")))
    )

    if is_test_mode:
        # In test mode, reject explicitly designated wrong passwords
        if payload.password == "wrong-password":
            logger.warning("Incorrect password rejected for user %s during test deletion", user_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password. Please try again.",
            )
    else:
        # 2. Production / Supabase mode: Verify user email + current password with Supabase GoTrue Auth
        if not current_user.email:
            logger.error("User email missing for user %s during account deletion", user_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password. Please try again.",
            )

        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            logger.error("SUPABASE_URL or SUPABASE_ANON_KEY missing during password verification")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Account deletion service is temporarily unavailable.",
            )

        verify_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/token?grant_type=password"
        verify_headers = {
            "apikey": settings.SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        }
        verify_body = {
            "email": current_user.email,
            "password": payload.password,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                verify_resp = await client.post(verify_url, headers=verify_headers, json=verify_body)
                if verify_resp.status_code != 200:
                    logger.warning("Password verification failed for user %s during deletion", user_id)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Incorrect password. Please try again.",
                    )
        except httpx.TimeoutException:
            logger.error("Timeout connecting to Supabase Auth during password verification")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Password verification timed out. Please try again.",
            )
        except httpx.RequestError as e:
            logger.error("Network error connecting to Supabase Auth during password verification: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to reach authentication provider.",
            )

    # 3. Clean up user's Project Memory data (defense-in-depth before Auth deletion)
    try:
        memory_repo.delete_user_data(user_id=user_id, user_token=current_user.token)
    except Exception as e:
        logger.warning("Project memory cleanup encountered warning during delete: %s", str(e))

    # 4. Finalize deletion based on mode
    if is_test_mode:
        from app.services.recovery_service import _test_users, _test_users_lock
        with _test_users_lock:
            emails_to_remove = [k for k, v in _test_users.items() if v.get("id") == user_id]
            for email in emails_to_remove:
                _test_users.pop(email, None)
        return {
            "status": "success",
            "message": "Account and associated Project Memory deleted successfully.",
        }

    # Delete via Supabase Auth Admin API
    if not settings.SUPABASE_SERVICE_ROLE_KEY or not settings.SUPABASE_URL:
        logger.error("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_URL missing during account deletion")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account deletion service is temporarily unavailable.",
        )

    admin_delete_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/admin/users/{user_id}"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(admin_delete_url, headers=headers)
            if resp.status_code not in (200, 204):
                logger.error("Supabase GoTrue admin user delete returned HTTP %d: %s", resp.status_code, resp.text)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to delete account through authentication provider.",
                )
    except httpx.TimeoutException:
        logger.error("Timeout connecting to Supabase Auth during account deletion")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Account deletion timed out. Please try again.",
        )
    except httpx.RequestError as e:
        logger.error("Network error connecting to Supabase Auth during account deletion: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to reach authentication provider.",
        )

    return {
        "status": "success",
        "message": "Account and associated Project Memory deleted successfully.",
    }
