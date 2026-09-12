import logging
from typing import Optional
from fastapi import APIRouter, Depends
from app.core.auth import AuthenticatedUser, get_optional_current_user
from app.core.plans import get_plans_response

logger = logging.getLogger("shiftly.plans")

router = APIRouter()


@router.get(
    "/plans",
    summary="Get Subscription Plans & Current Plan Status",
    description="Returns available plans (FREE, PLUS, PRO) and current plan state (GUEST or FREE) derived strictly from authentication.",
)
async def get_plans(
    current_user: Optional[AuthenticatedUser] = Depends(get_optional_current_user),
):
    return get_plans_response(current_user)
