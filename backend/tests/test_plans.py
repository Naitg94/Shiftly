import os
import io
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

os.environ["TEST_USE_SQLITE"] = "true"

from app.main import app
from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.core.plans import (
    PlanTier,
    PLAN_LIMITS,
    PLAN_CATALOG,
    UserEntitlement,
    is_private_pro_user,
    resolve_entitlement,
    resolve_effective_plan,
    resolve_public_plan,
    resolve_current_plan,
    get_user_subscription,
    get_plan_limits,
    get_plans_response,
)
from app.core.auth import AuthenticatedUser
from app.db.models import Project
from app.services.file_processing_service import ExtractedFileContent
from app.models.schemas import (
    ShiftlyAnalysisResult,
    AnalysisStats,
    KeyPointItem,
    ActionItem,
    DecisionItem,
    ImportantDateItem,
    SourceReference,
)

PRO_USER_UUID = "00000000-0000-0000-0000-000000000001"
NORMAL_USER_UUID = "00000000-0000-0000-0000-000000000002"

guest_client = TestClient(app)
pro_client = TestClient(app, headers={"Authorization": "Bearer test-token-user-a"})
normal_client = TestClient(app, headers={"Authorization": "Bearer test-token-user-b"})

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
def reset_state():
    rate_limiter.reset()
    # Configure PRO_USER_UUID as private Pro by default in tests
    with patch.object(settings, "PRIVATE_PRO_USER_IDS_RAW", PRO_USER_UUID):
        yield
    rate_limiter.reset()


# =========================================================================
# 1. PLAN CATALOG & LOCKED COMMERCIAL DEFINITIONS
# =========================================================================

def test_plan_catalog_definitions():
    """Verify exact pricing, billing interval, and limits across all tiers."""
    # Free tier
    free_details = PLAN_CATALOG["FREE"]
    assert free_details["price"] == 0
    assert free_details["currency"] == "USD"
    assert free_details["status"] == "active"
    assert free_details["tagline"] == "Active"
    free_limits = PLAN_LIMITS["FREE"]
    assert free_limits.analysis_limit == 30
    assert free_limits.max_characters_per_analysis == 50000
    assert free_limits.max_file_size_bytes == 10 * 1024 * 1024
    assert free_limits.max_projects == 10
    assert free_limits.storage_limit_bytes == 100 * 1024 * 1024
    assert free_limits.supported_inputs == ["PDF", "DOCX", "TXT"]

    # Plus tier
    plus_details = PLAN_CATALOG["PLUS"]
    assert plus_details["price"] == 1
    assert plus_details["currency"] == "USD"
    assert plus_details["status"] == "coming_soon"
    plus_limits = PLAN_LIMITS["PLUS"]
    assert plus_limits.analysis_limit == 150
    assert plus_limits.max_characters_per_analysis == 100000
    assert plus_limits.max_file_size_bytes == 20 * 1024 * 1024
    assert plus_limits.max_projects == 20
    assert plus_limits.storage_limit_bytes == 1 * 1024 * 1024 * 1024
    assert plus_limits.supported_inputs == ["PDF", "DOCX", "TXT", "EML", "MBOX", "WhatsApp", "ZIP"]

    # Pro tier
    pro_details = PLAN_CATALOG["PRO"]
    assert pro_details["price"] == 5
    assert pro_details["currency"] == "USD"
    assert pro_details["status"] == "coming_soon"
    pro_limits = PLAN_LIMITS["PRO"]
    assert pro_limits.analysis_limit is None  # Unlimited
    assert pro_limits.max_characters_per_analysis == 200000
    assert pro_limits.max_file_size_bytes == 25 * 1024 * 1024
    assert pro_limits.max_projects == 50
    assert pro_limits.storage_limit_bytes == 4 * 1024 * 1024 * 1024
    assert pro_limits.supported_inputs == ["PDF", "DOCX", "TXT", "EML", "MBOX", "WhatsApp", "ZIP"]

    # Guest limits
    guest_limits = PLAN_LIMITS["GUEST"]
    assert guest_limits.max_characters_per_analysis == 3000
    assert guest_limits.max_projects == 0
    assert guest_limits.storage_limit_bytes == 0
    assert guest_limits.project_memory is False


# =========================================================================
# TEST 1: GUEST -> GUEST
# =========================================================================

def test_1_guest_resolves_to_guest():
    """TEST 1: Unauthenticated request resolves strictly to GUEST with guest limits."""
    res = guest_client.get("/api/plans")
    assert res.status_code == 200
    data = res.json()
    assert data["current_plan"] == "GUEST"
    assert data["is_authenticated"] is False

    ent = resolve_entitlement(None)
    assert ent.public_plan == PlanTier.GUEST
    assert ent.effective_plan == PlanTier.GUEST
    assert ent.lifetime is False
    assert resolve_current_plan(None) == PlanTier.GUEST


# =========================================================================
# TEST 2: NORMAL AUTHENTICATED USER -> FREE
# =========================================================================

def test_2_normal_authenticated_user_resolves_to_free():
    """TEST 2: Normal authenticated user resolves strictly to FREE."""
    user = AuthenticatedUser(id=NORMAL_USER_UUID, email="normal@example.com")
    ent = resolve_entitlement(user)
    assert ent.public_plan == PlanTier.FREE
    assert ent.effective_plan == PlanTier.FREE
    assert ent.lifetime is False
    assert resolve_current_plan(user) == PlanTier.FREE

    res_plans = normal_client.get("/api/plans")
    assert res_plans.status_code == 200
    assert res_plans.json()["current_plan"] == "FREE"


# =========================================================================
# TEST 3: MY ACCOUNT -> PRO
# =========================================================================

def test_3_designated_account_resolves_to_pro():
    """TEST 3: Designated account in PRIVATE_PRO_USER_IDS resolves to PRO."""
    user = AuthenticatedUser(id=PRO_USER_UUID, email="goyalnait678@gmail.com")
    ent = resolve_entitlement(user)
    assert ent.public_plan == PlanTier.PRO
    assert ent.effective_plan == PlanTier.PRO
    assert ent.lifetime is True
    assert resolve_current_plan(user) == PlanTier.PRO

    res_plans = pro_client.get("/api/plans")
    assert res_plans.status_code == 200
    assert res_plans.json()["current_plan"] == "PRO"


# =========================================================================
# TEST 4: FUTURE PLUS SUBSCRIPTION FIXTURE -> PLUS
# =========================================================================

def test_4_future_plus_subscription_resolves_to_plus():
    """TEST 4: Active Plus subscription resolves to PLUS."""
    user = AuthenticatedUser(id="plus-sub-user", email="plus@example.com")
    with patch("app.core.plans.get_user_subscription", return_value={"status": "active", "plan": "PLUS"}):
        ent = resolve_entitlement(user)
        assert ent.public_plan == PlanTier.PLUS
        assert ent.effective_plan == PlanTier.PLUS
        assert ent.lifetime is False
        assert resolve_current_plan(user) == PlanTier.PLUS

        res = get_plans_response(user)
        assert res["current_plan"] == "PLUS"
        plus_card = next(p for p in res["plans"] if p.id == "PLUS")
        assert plus_card.is_current is True
        free_card = next(p for p in res["plans"] if p.id == "FREE")
        assert free_card.is_current is False


# =========================================================================
# TEST 5: FUTURE PRO SUBSCRIPTION FIXTURE -> PRO
# =========================================================================

def test_5_future_pro_subscription_resolves_to_pro():
    """TEST 5: Active Pro subscription resolves to PRO."""
    user = AuthenticatedUser(id="pro-sub-user", email="prosub@example.com")
    with patch("app.core.plans.get_user_subscription", return_value={"status": "active", "plan": "PRO"}):
        ent = resolve_entitlement(user)
        assert ent.public_plan == PlanTier.PRO
        assert ent.effective_plan == PlanTier.PRO
        assert ent.lifetime is False
        assert resolve_current_plan(user) == PlanTier.PRO

        res = get_plans_response(user)
        assert res["current_plan"] == "PRO"
        pro_card = next(p for p in res["plans"] if p.id == "PRO")
        assert pro_card.is_current is True
        free_card = next(p for p in res["plans"] if p.id == "FREE")
        assert free_card.is_current is False


# =========================================================================
# TEST 6: MY ACCOUNT HAS PRO LIMITS
# =========================================================================

def test_6_designated_account_has_pro_limits():
    """TEST 6: Pro account receives 200k chars, 25MB, 50 projects, 4GB, unlimited analyses, and all formats."""
    # 1. Summary endpoint verification
    res_summary = pro_client.get("/api/account/summary")
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert summary["plan"]["id"] == "PRO"
    assert summary["usage"]["analyses_limit"] is None  # Unlimited
    assert summary["usage"]["characters_limit"] == 200000
    assert summary["usage"]["projects_limit"] == 50
    assert summary["storage"]["limit_bytes"] == 4 * 1024 * 1024 * 1024  # 4 GB

    # 2. 150,000 characters text analysis succeeds
    with patch("app.api.v1.endpoints.analyze.analyze_communication", return_value=MOCK_RESULT):
        res_text = pro_client.post("/api/analyze", json={"text": "A" * 150000})
        assert res_text.status_code == 200

    # 3. Unlimited monthly analyses (no 429 when analyses >= 30)
    with patch("app.db.repository.memory_repo.count_user_analyses_in_month", return_value=100):
        with patch("app.api.v1.endpoints.analyze.analyze_communication", return_value=MOCK_RESULT):
            res_unlimited = pro_client.post("/api/analyze", json={"text": "Valid note."})
            assert res_unlimited.status_code == 200

    # 4. Project creation allowed up to 50
    with patch("app.db.repository.memory_repo.count_user_projects", return_value=49):
        with patch("app.db.repository.memory_repo.create_project") as mock_create:
            mock_create.return_value = Project(id="proj-49", name="Proj 49", created_at="now", updated_at="now")
            res_proj = pro_client.post("/api/projects", json={"name": "Proj 49"})
            assert res_proj.status_code == 201

    # Over 50 is rejected with 403
    with patch("app.db.repository.memory_repo.count_user_projects", return_value=50):
        res_proj_over = pro_client.post("/api/projects", json={"name": "Proj 51"})
        assert res_proj_over.status_code == 403
        assert "50" in res_proj_over.json()["detail"]

    # 5. Advanced formats (EML, ZIP) succeed
    mock_extracted = ExtractedFileContent(
        filename="notes.eml",
        source_type="Email Thread",
        full_text="Alice: Important discussion.",
        blocks=[],
    )
    with patch("app.api.v1.endpoints.analyze.process_uploaded_file", return_value=mock_extracted):
        with patch("app.api.v1.endpoints.analyze.analyze_communication", return_value=MOCK_RESULT):
            eml_file = {"file": ("notes.eml", io.BytesIO(b"From: a@b.com\n\nNotes"), "message/rfc822")}
            res_file = pro_client.post("/api/analyze/file", files=eml_file)
            assert res_file.status_code == 200


# =========================================================================
# TEST 7: NORMAL FREE ACCOUNT HAS FREE LIMITS
# =========================================================================

def test_7_normal_free_account_has_free_limits():
    """TEST 7: Free account has 50k chars, 10MB, 10 projects, 100MB, 30 analyses/month, no advanced formats."""
    # 1. Summary verification
    res_summary = normal_client.get("/api/account/summary")
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert summary["plan"]["id"] == "FREE"
    assert summary["usage"]["analyses_limit"] == 30
    assert summary["usage"]["characters_limit"] == 50000
    assert summary["usage"]["projects_limit"] == 10
    assert summary["storage"]["limit_bytes"] == 100 * 1024 * 1024

    # 2. Exceeding 50k chars is rejected with 413
    res_text = normal_client.post("/api/analyze", json={"text": "A" * 50001})
    assert res_text.status_code == 413
    assert "50,000" in res_text.json()["detail"]

    # 3. Exceeding monthly limit (30) returns 429
    with patch("app.db.repository.memory_repo.count_user_analyses_in_month", return_value=30):
        res_quota = normal_client.post("/api/analyze", json={"text": "Valid note discussion."})
        assert res_quota.status_code == 429
        assert "Monthly analysis limit of 30 reached" in res_quota.json()["detail"]

    # 4. Exceeding 10 projects returns 403
    with patch("app.db.repository.memory_repo.count_user_projects", return_value=10):
        res_proj = normal_client.post("/api/projects", json={"name": "Project 11"})
        assert res_proj.status_code == 403
        assert "Project limit reached" in res_proj.json()["detail"]

    # 5. Advanced communication formats (EML, ZIP) rejected with 403
    eml_file = {"file": ("test.eml", io.BytesIO(b"From: a@b.com\n\nHi"), "message/rfc822")}
    res_eml = normal_client.post("/api/analyze/file", files=eml_file)
    assert res_eml.status_code == 403
    assert "EML file format is not supported on your plan" in res_eml.json()["detail"]


# =========================================================================
# TEST 8: NAVBAR DISPLAYS PRO FOR MY ACCOUNT
# =========================================================================

def test_8_navbar_displays_pro_for_designated_account():
    """TEST 8: Central current plan resolver returns PRO for navbar display."""
    user = AuthenticatedUser(id=PRO_USER_UUID, email="goyalnait678@gmail.com")
    assert resolve_current_plan(user) == PlanTier.PRO
    assert resolve_public_plan(user) == PlanTier.PRO


# =========================================================================
# TEST 9: SETTINGS DISPLAYS PRO FOR MY ACCOUNT
# =========================================================================

def test_9_settings_displays_pro_for_designated_account():
    """TEST 9: Settings summary endpoint returns PRO badge and display name."""
    res = pro_client.get("/api/account/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["plan"]["id"] == "PRO"
    assert data["plan"]["display_name"] == "Pro"
    assert data["plan"]["status"] == "Active"


# =========================================================================
# TEST 10: PLANS PAGE MARKS PRO AS CURRENT PLAN FOR MY ACCOUNT
# =========================================================================

def test_10_plans_page_marks_pro_as_current_plan():
    """TEST 10: Plans page response marks PRO as is_current=True."""
    res = pro_client.get("/api/plans")
    assert res.status_code == 200
    data = res.json()
    assert data["current_plan"] == "PRO"
    pro_card = next(p for p in data["plans"] if p["id"] == "PRO")
    assert pro_card["is_current"] is True


# =========================================================================
# TEST 11: FREE IS NOT SIMULTANEOUSLY MARKED CURRENT PLAN FOR MY ACCOUNT
# =========================================================================

def test_11_free_not_simultaneously_current_for_pro():
    """TEST 11: When user has PRO, FREE and PLUS must have is_current=False."""
    res = pro_client.get("/api/plans")
    assert res.status_code == 200
    data = res.json()
    free_card = next(p for p in data["plans"] if p["id"] == "FREE")
    assert free_card["is_current"] is False
    plus_card = next(p for p in data["plans"] if p["id"] == "PLUS")
    assert plus_card["is_current"] is False
    # Exactly one plan is current
    current_count = sum(1 for p in data["plans"] if p["is_current"])
    assert current_count == 1


# =========================================================================
# TEST 12: CLIENT CANNOT FORCE PRO
# =========================================================================

def test_12_client_cannot_force_pro():
    """TEST 12: Client cannot force PRO via query params, body, or headers."""
    # Query param tampering
    res1 = normal_client.get("/api/plans?plan=PRO&tier=PRO")
    assert res1.status_code == 200
    assert res1.json()["current_plan"] == "FREE"

    # Body tampering
    res2 = normal_client.post(
        "/api/analyze",
        json={"text": "A" * 50001, "plan": "PRO", "tier": "PRO", "is_pro": True},
    )
    assert res2.status_code == 413

    # Header tampering
    res3 = normal_client.get("/api/plans", headers={"X-Plan": "PRO", "X-Tier": "PRO"})
    assert res3.status_code == 200
    assert res3.json()["current_plan"] == "FREE"


# =========================================================================
# TEST 13: CLIENT CANNOT FORCE FREE
# =========================================================================

def test_13_client_cannot_force_free_for_pro():
    """TEST 13: Client cannot force FREE on a PRO account."""
    res = pro_client.get("/api/plans?plan=FREE&tier=FREE", headers={"X-Plan": "FREE"})
    assert res.status_code == 200
    assert res.json()["current_plan"] == "PRO"
    pro_card = next(p for p in res.json()["plans"] if p["id"] == "PRO")
    assert pro_card["is_current"] is True


# =========================================================================
# TEST 14: PRIVATE ENTITLEMENT SURVIVES LOGOUT/LOGIN
# =========================================================================

def test_14_private_entitlement_persists_across_sessions():
    """TEST 14: Entitlement persists across separate client sessions for the same user."""
    client1 = TestClient(app, headers={"Authorization": "Bearer test-token-user-a"})
    res1 = client1.get("/api/account/summary")
    assert res1.status_code == 200
    assert res1.json()["plan"]["id"] == "PRO"

    # New client instance simulating re-login
    client2 = TestClient(app, headers={"Authorization": "Bearer test-token-user-a"})
    res2 = client2.get("/api/account/summary")
    assert res2.status_code == 200
    assert res2.json()["plan"]["id"] == "PRO"
    assert res2.json()["usage"]["projects_limit"] == 50
    assert res2.json()["storage"]["limit_bytes"] == 4 * 1024 * 1024 * 1024


# =========================================================================
# TEST 15: NO PRIVATE UUID IS EXPOSED TO FRONTEND
# =========================================================================

def test_15_no_private_uuid_exposed_to_frontend():
    """TEST 15: No private UUID is leaked in public API endpoints or frontend code."""
    # Check /api/plans response
    res_guest = guest_client.get("/api/plans")
    assert PRO_USER_UUID not in res_guest.text

    res_normal = normal_client.get("/api/plans")
    assert PRO_USER_UUID not in res_normal.text

    res_pro = pro_client.get("/api/plans")
    assert PRO_USER_UUID not in res_pro.text

    # Check /api/account/summary response does not contain other users' UUIDs
    res_summary = normal_client.get("/api/account/summary")
    assert PRO_USER_UUID not in res_summary.text


# =========================================================================
# TEST 16: DESIGNATED ACCOUNT RESOLVES TO PRO WITHOUT ENV VAR
# =========================================================================

def test_16_designated_account_resolves_to_pro_without_env_var():
    """TEST 16: Designated account resolves to PRO even when runtime env vars are empty."""
    with patch.object(settings, "PRIVATE_PRO_USER_IDS_RAW", ""), patch.object(settings, "PRIVATE_PRO_EMAILS_RAW", ""):
        # 1. Full designated user (matching production UUID and email)
        user = AuthenticatedUser(id="53d108fa-89fb-497b-92e6-ee67c6f7b7ce", email="goyalnait678@gmail.com")
        ent = resolve_entitlement(user)
        assert ent.public_plan == PlanTier.PRO
        assert ent.effective_plan == PlanTier.PRO
        assert ent.lifetime is True
        assert resolve_current_plan(user) == PlanTier.PRO

        # 2. Designated email with different UUID (e.g. if auth provider regenerates ID)
        user_email = AuthenticatedUser(id="regenerated-uuid-123", email="goyalnait678@gmail.com")
        assert resolve_entitlement(user_email).public_plan == PlanTier.PRO

        # 3. Designated UUID with missing or masked email
        user_uuid = AuthenticatedUser(id="53d108fa-89fb-497b-92e6-ee67c6f7b7ce", email=None)
        assert resolve_entitlement(user_uuid).public_plan == PlanTier.PRO

        # 4. Normal user with empty env vars must remain FREE
        normal_user = AuthenticatedUser(id="normal-user-uuid", email="someoneelse@example.com")
        assert resolve_entitlement(normal_user).public_plan == PlanTier.FREE

        # 5. Unauthenticated user must remain GUEST
        assert resolve_entitlement(None).public_plan == PlanTier.GUEST
