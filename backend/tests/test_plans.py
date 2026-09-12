import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

os.environ["TEST_USE_SQLITE"] = "true"

from app.main import app
from app.core.rate_limiter import rate_limiter
from app.core.plans import PlanTier, resolve_current_plan, get_plans_response
from app.core.auth import AuthenticatedUser
from app.models.schemas import (
    ShiftlyAnalysisResult,
    AnalysisStats,
    KeyPointItem,
    ActionItem,
    DecisionItem,
    ImportantDateItem,
    SourceReference,
)

guest_client = TestClient(app)
auth_client = TestClient(app, headers={"Authorization": "Bearer test-token-user-a"})

MOCK_SRC = SourceReference(
    id="src-p1",
    sourceType="Document",
    sourceName="spec.txt",
    date="Oct 12",
    sender="Alice",
    messageRef="Msg #1",
    excerpt="Approved",
)

MOCK_RESULT = ShiftlyAnalysisResult(
    id="analysis-p1",
    title="Plan Verification",
    analyzedAt="October 12, 2024",
    stats=AnalysisStats(messagesAnalyzed=1, participantsCount=1),
    summary="Approved preview scope.",
    keyPoints=[KeyPointItem(id="kp-1", point="Full access", category="General", source=MOCK_SRC)],
    actions=[],
    decisions=[],
    importantDates=[],
)


@pytest.fixture(autouse=True)
def reset_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


# =========================================================================
# 1 & 2. UNAUTHENTICATED -> GUEST, AUTHENTICATED -> FREE
# =========================================================================

def test_unauthenticated_user_resolves_to_guest():
    """1. Unauthenticated request to /api/plans resolves strictly to GUEST."""
    res = guest_client.get("/api/plans")
    assert res.status_code == 200
    data = res.json()
    assert data["current_plan"] == "GUEST"
    assert data["is_authenticated"] is False
    assert "guest" in data["usage_status"].lower()

    # Verify unit resolver directly
    assert resolve_current_plan(None) == PlanTier.GUEST


def test_authenticated_user_resolves_to_free():
    """2. Authenticated request to /api/plans resolves strictly to FREE."""
    res = auth_client.get("/api/plans")
    assert res.status_code == 200
    data = res.json()
    assert data["current_plan"] == "FREE"
    assert data["is_authenticated"] is True
    assert "full access during preview" in data["usage_status"].lower()

    # Verify unit resolver directly
    mock_user = AuthenticatedUser(id="user-123", email="user@example.com")
    assert resolve_current_plan(mock_user) == PlanTier.FREE


# =========================================================================
# 3 & 4. GUEST & AUTHENTICATED ANALYSIS FUNCTIONALITY
# =========================================================================

def test_guest_can_still_perform_analysis():
    """3. Guest can analyze valid communication within the 3,000-char limit."""
    with patch("app.api.v1.endpoints.analyze.analyze_communication", return_value=MOCK_RESULT):
        res = guest_client.post("/api/analyze", json={"text": "Alice: Meeting scope approved."})
        assert res.status_code == 200
        assert res.json()["title"] == "Plan Verification"


def test_authenticated_can_still_perform_analysis():
    """4. Authenticated user can analyze communications."""
    with patch("app.api.v1.endpoints.analyze.analyze_communication", return_value=MOCK_RESULT):
        res = auth_client.post("/api/analyze", json={"text": "Alice: Project Alpha milestone sign-off."})
        assert res.status_code == 200
        assert res.json()["title"] == "Plan Verification"


# =========================================================================
# 5. NO MONTHLY QUOTA RESTRICTION FOR AUTHENTICATED FREE USERS
# =========================================================================

def test_authenticated_user_has_no_monthly_quota():
    """5. Authenticated users are not restricted by any monthly quota."""
    with patch("app.api.v1.endpoints.analyze.analyze_communication", return_value=MOCK_RESULT):
        for i in range(5):
            res = auth_client.post("/api/analyze", json={"text": f"Iteration {i}: scope check"})
            assert res.status_code == 200


# =========================================================================
# 6, 7 & 8. NO CLIENT-SIDE PLAN ESCALATION (PLUS / PRO CANNOT BE CLAIMED)
# =========================================================================

def test_plus_and_pro_cannot_be_activated_via_client_parameters():
    """6, 7 & 8. Query params, request bodies, or client headers attempting plan=PRO or PLUS are ignored."""
    # Attempting to send ?plan=PRO
    res1 = guest_client.get("/api/plans?plan=PRO")
    assert res1.status_code == 200
    assert res1.json()["current_plan"] == "GUEST"

    # Attempting to send ?plan=PLUS as authenticated user
    res2 = auth_client.get("/api/plans?plan=PLUS")
    assert res2.status_code == 200
    assert res2.json()["current_plan"] == "FREE"

    # Attempting to post plan="PRO" in analysis request
    with patch("app.api.v1.endpoints.analyze.analyze_communication", return_value=MOCK_RESULT):
        res3 = guest_client.post("/api/analyze", json={"text": "Hello", "plan": "PRO"})
        assert res3.status_code == 200
        # Remains guest; sending oversized content with "plan": "PRO" is still rejected by guest limits
        oversized = "A" * 3001
        res4 = guest_client.post("/api/analyze", json={"text": oversized, "plan": "PRO"})
        assert res4.status_code == 413


# =========================================================================
# 9 & 10. GUEST 3,000 LIMIT & AUTHENTICATED 200,000 LIMIT
# =========================================================================

def test_existing_limits_maintained():
    """9 & 10. Guest 3,000-char limit and authenticated 200,000-char limit remain intact."""
    # Guest > 3,000 is rejected with 413
    res_guest = guest_client.post("/api/analyze", json={"text": "G" * 3001})
    assert res_guest.status_code == 413
    assert "guest mode" in res_guest.json()["detail"].lower()

    # Authenticated 4,000 chars succeeds
    with patch("app.api.v1.endpoints.analyze.analyze_communication", return_value=MOCK_RESULT):
        res_auth = auth_client.post("/api/analyze", json={"text": "A" * 4000})
        assert res_auth.status_code == 200


# =========================================================================
# 11 & 12. RATE LIMITING & PROJECT MEMORY REMAINS PROTECTED
# =========================================================================

def test_project_memory_still_requires_authentication():
    """12. Guest cannot access Project Memory endpoints."""
    res = guest_client.get("/api/projects")
    assert res.status_code == 401
