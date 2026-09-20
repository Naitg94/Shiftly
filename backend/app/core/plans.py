from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.core.config import settings
from app.core.auth import AuthenticatedUser


class PlanTier(str, Enum):
    GUEST = "GUEST"
    FREE = "FREE"
    PLUS = "PLUS"
    PRO = "PRO"


class PlanLimits(BaseModel):
    analysis_limit: Optional[int]  # None means unlimited
    max_characters_per_analysis: int
    max_file_size_bytes: int
    max_projects: int
    storage_limit_bytes: int
    supported_inputs: List[str]
    project_memory: bool
    search_memory: bool
    source_evidence: bool


class PlanDetails(BaseModel):
    id: str
    name: str
    display_name: str
    price: int
    currency: str = "USD"
    billing_interval: str = "monthly"
    status: str  # "active" | "coming_soon"
    tagline: str
    description: str
    features: List[str]
    is_current: bool = False
    limits: PlanLimits


PLAN_LIMITS: Dict[str, PlanLimits] = {
    PlanTier.GUEST.value: PlanLimits(
        analysis_limit=None,
        max_characters_per_analysis=3000,
        max_file_size_bytes=25 * 1024 * 1024,
        max_projects=0,
        storage_limit_bytes=0,
        supported_inputs=["PDF", "DOCX", "TXT", "EML", "MBOX", "WhatsApp", "ZIP"],
        project_memory=False,
        search_memory=False,
        source_evidence=True,
    ),
    PlanTier.FREE.value: PlanLimits(
        analysis_limit=30,
        max_characters_per_analysis=50000,
        max_file_size_bytes=10 * 1024 * 1024,
        max_projects=10,
        storage_limit_bytes=100 * 1024 * 1024,  # 100 MB
        supported_inputs=["PDF", "DOCX", "TXT"],
        project_memory=True,
        search_memory=True,
        source_evidence=True,
    ),
    PlanTier.PLUS.value: PlanLimits(
        analysis_limit=150,
        max_characters_per_analysis=100000,
        max_file_size_bytes=20 * 1024 * 1024,
        max_projects=20,
        storage_limit_bytes=1 * 1024 * 1024 * 1024,  # 1 GB
        supported_inputs=["PDF", "DOCX", "TXT", "EML", "MBOX", "WhatsApp", "ZIP"],
        project_memory=True,
        search_memory=True,
        source_evidence=True,
    ),
    PlanTier.PRO.value: PlanLimits(
        analysis_limit=None,  # Unlimited
        max_characters_per_analysis=200000,
        max_file_size_bytes=25 * 1024 * 1024,
        max_projects=50,
        storage_limit_bytes=4 * 1024 * 1024 * 1024,  # 4 GB
        supported_inputs=["PDF", "DOCX", "TXT", "EML", "MBOX", "WhatsApp", "ZIP"],
        project_memory=True,
        search_memory=True,
        source_evidence=True,
    ),
}


PLAN_CATALOG: Dict[str, Dict[str, Any]] = {
    PlanTier.FREE.value: {
        "id": "FREE",
        "name": "FREE",
        "display_name": "Free",
        "price": 0,
        "currency": "USD",
        "billing_interval": "monthly",
        "status": "active",
        "tagline": "Active",
        "description": "Essential communication intelligence and Project Memory workspaces.",
        "features": [
            "30 analyses per month",
            "Up to 50,000 characters per analysis",
            "10 MB file upload limit",
            "10 Project Memory workspaces",
            "100 MB storage",
            "Supported formats: PDF, DOCX, TXT",
            "Search across discussions & decisions",
            "Source evidence alignment",
        ],
        "limits": PLAN_LIMITS[PlanTier.FREE.value],
    },
    PlanTier.PLUS.value: {
        "id": "PLUS",
        "name": "PLUS",
        "display_name": "Plus",
        "price": 1,
        "currency": "USD",
        "billing_interval": "monthly",
        "status": "coming_soon",
        "tagline": "Coming Soon",
        "description": "Higher capacity and expanded communication formats for active professionals.",
        "features": [
            "150 analyses per month",
            "Up to 100,000 characters per analysis",
            "20 MB file upload limit",
            "20 Project Memory workspaces",
            "1 GB storage",
            "All communication formats (WhatsApp ZIP, EML, MBOX, PDF, DOCX, TXT)",
            "Search across discussions & decisions",
            "Source evidence alignment",
        ],
        "limits": PLAN_LIMITS[PlanTier.PLUS.value],
    },
    PlanTier.PRO.value: {
        "id": "PRO",
        "name": "PRO",
        "display_name": "Pro",
        "price": 5,
        "currency": "USD",
        "billing_interval": "monthly",
        "status": "coming_soon",
        "tagline": "Coming Soon",
        "description": "Maximum capacity, unlimited analyses, and dedicated throughput for power users.",
        "features": [
            "Unlimited analyses per month",
            "Up to 200,000 characters per analysis",
            "25 MB file upload limit",
            "50 Project Memory workspaces",
            "4 GB storage",
            "All communication formats (WhatsApp ZIP, EML, MBOX, PDF, DOCX, TXT)",
            "Search across discussions & decisions",
            "Source evidence alignment",
        ],
        "limits": PLAN_LIMITS[PlanTier.PRO.value],
    },
}


class UserEntitlement(BaseModel):
    public_plan: PlanTier
    effective_plan: PlanTier
    lifetime: bool
    limits: PlanLimits


def get_user_subscription(user_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Hook for checking active paid subscriptions in future billing integration.
    Returns None by default (no active paid subscription in preview).
    Can be mocked/patched in tests for future Plus/Pro subscription testing.
    """
    return None


def is_private_pro_user(user_id: Optional[str]) -> bool:
    """
    Determines whether a user has the private lifetime Pro entitlement.
    Derived strictly server-side from the verified Supabase Auth user UUID.
    Client-side parameters, emails, or usernames are NEVER consulted.
    """
    if not user_id:
        return False
    return user_id in settings.private_pro_user_ids


def resolve_entitlement(user: Optional[AuthenticatedUser]) -> UserEntitlement:
    """
    Central authoritative resolver for user plan entitlement.
    - Unauthenticated users: GUEST (public and effective).
    - Active paid subscription exists: PLUS or PRO from subscription, lifetime=False.
    - Designated accounts in PRIVATE_PRO_USER_IDS: PRO publicly, PRO effectively, lifetime=True.
    - All other authenticated users: FREE publicly, FREE effectively, lifetime=False.
    """
    if not user or not user.id:
        return UserEntitlement(
            public_plan=PlanTier.GUEST,
            effective_plan=PlanTier.GUEST,
            lifetime=False,
            limits=PLAN_LIMITS[PlanTier.GUEST.value],
        )

    # 1. Check for active paid subscription (future purchase compatibility)
    sub = get_user_subscription(user.id)
    if sub and sub.get("status") == "active":
        sub_plan = str(sub.get("plan", "")).upper()
        if sub_plan in [PlanTier.PLUS.value, PlanTier.PRO.value]:
            tier = PlanTier(sub_plan)
            return UserEntitlement(
                public_plan=tier,
                effective_plan=tier,
                lifetime=False,
                limits=PLAN_LIMITS[tier.value],
            )

    # 2. Check for private lifetime Pro entitlement
    if is_private_pro_user(user.id):
        return UserEntitlement(
            public_plan=PlanTier.PRO,
            effective_plan=PlanTier.PRO,
            lifetime=True,
            limits=PLAN_LIMITS[PlanTier.PRO.value],
        )

    # 3. Default fallback for authenticated users
    return UserEntitlement(
        public_plan=PlanTier.FREE,
        effective_plan=PlanTier.FREE,
        lifetime=False,
        limits=PLAN_LIMITS[PlanTier.FREE.value],
    )


def resolve_effective_plan(user: Optional[AuthenticatedUser]) -> PlanTier:
    """Resolves the effective plan governing actual backend capabilities and limits."""
    return resolve_entitlement(user).effective_plan


def resolve_public_plan(user: Optional[AuthenticatedUser]) -> PlanTier:
    """Resolves the public/display plan shown on the website and in UI badges."""
    return resolve_entitlement(user).public_plan


def resolve_current_plan(user: Optional[AuthenticatedUser]) -> PlanTier:
    """Central authoritative resolver returning current plan tier."""
    return resolve_public_plan(user)


def get_plan_limits(tier: PlanTier) -> PlanLimits:
    """Returns the authoritative limits object for a given plan tier."""
    return PLAN_LIMITS[tier.value]


def get_plans_response(user: Optional[AuthenticatedUser]) -> Dict[str, Any]:
    """
    Returns the official plan catalog with user public plan resolution.
    Accurately reflects whether the current user is GUEST, FREE, PLUS, or PRO.
    """
    entitlement = resolve_entitlement(user)
    public_tier = entitlement.public_plan
    plans_list = []
    for plan_id in [PlanTier.FREE.value, PlanTier.PLUS.value, PlanTier.PRO.value]:
        raw = PLAN_CATALOG[plan_id].copy()
        raw["is_current"] = (public_tier.value == plan_id)
        plans_list.append(PlanDetails(**raw))

    return {
        "current_plan": public_tier.value,
        "status": "active" if public_tier != PlanTier.GUEST else None,
        "is_authenticated": user is not None and bool(user.id),
        "usage_status": (
            "Active Pro plan"
            if public_tier == PlanTier.PRO
            else "Active Plus plan"
            if public_tier == PlanTier.PLUS
            else "Active Free plan"
            if public_tier == PlanTier.FREE
            else "Guest access (up to 3,000 characters text / 1,500 characters file)"
        ),
        "plans": plans_list,
    }
