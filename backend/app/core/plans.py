from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.core.auth import AuthenticatedUser


class PlanTier(str, Enum):
    GUEST = "GUEST"
    FREE = "FREE"
    PLUS = "PLUS"
    PRO = "PRO"


class PlanDetails(BaseModel):
    id: str
    name: str
    display_name: str
    status: str  # "active" | "coming_soon"
    tagline: str
    description: str
    features: List[str]
    is_current: bool = False


PLAN_CATALOG: Dict[str, Dict[str, Any]] = {
    PlanTier.FREE.value: {
        "id": "FREE",
        "name": "FREE",
        "display_name": "Free",
        "status": "active",
        "tagline": "Full access during preview",
        "description": "Full access to all Shiftly intelligence and Project Memory capabilities during preview.",
        "features": [
            "AI communication analysis",
            "Project Memory workspaces",
            "Search across discussions & decisions",
            "Source evidence alignment",
            "All supported communication sources (WhatsApp ZIP, EML, MBOX, PDF, DOCX, TXT)",
            "Up to 200,000 characters per analysis",
            "25 MB file upload limit",
            "No monthly analysis quota during preview",
        ],
    },
    PlanTier.PLUS.value: {
        "id": "PLUS",
        "name": "PLUS",
        "display_name": "Plus",
        "status": "coming_soon",
        "tagline": "Coming Soon",
        "description": "Future higher-capacity and advanced capabilities.",
        "features": [
            "More capacity and advanced capabilities are coming",
            "Higher analysis throughput",
            "Expanded project history retention",
            "Advanced export formats",
        ],
    },
    PlanTier.PRO.value: {
        "id": "PRO",
        "name": "PRO",
        "display_name": "Pro",
        "status": "coming_soon",
        "tagline": "Coming Soon",
        "description": "Advanced capabilities for larger teams and organizations.",
        "features": [
            "Advanced capabilities for teams and organizations",
            "Multi-user shared workspaces",
            "Organization-level governance & access control",
            "Priority processing & dedicated throughput",
        ],
    },
}


def resolve_current_plan(user: Optional[AuthenticatedUser]) -> PlanTier:
    """
    Resolves plan strictly from authenticated user identity.
    Client-side plan values are never trusted or consulted.
    """
    if not user or not user.id:
        return PlanTier.GUEST
    return PlanTier.FREE


def get_plans_response(user: Optional[AuthenticatedUser]) -> Dict[str, Any]:
    """
    Returns plan catalog with current user plan resolution.
    """
    current_tier = resolve_current_plan(user)
    plans_list = []
    for plan_id in [PlanTier.FREE.value, PlanTier.PLUS.value, PlanTier.PRO.value]:
        raw = PLAN_CATALOG[plan_id].copy()
        raw["is_current"] = (current_tier == PlanTier.FREE and plan_id == PlanTier.FREE.value)
        plans_list.append(PlanDetails(**raw))

    return {
        "current_plan": current_tier.value,
        "is_authenticated": user is not None and bool(user.id),
        "usage_status": "Full access during preview" if current_tier == PlanTier.FREE else "Guest access (up to 3,000 characters text / 1,500 characters file)",
        "plans": plans_list,
    }
