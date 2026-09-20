import os
import time
import pytest
from fastapi.testclient import TestClient

os.environ["TEST_USE_SQLITE"] = "true"

from app.main import app
from app.core.rate_limiter import rate_limiter
from app.services.recovery_service import (
    register_test_user,
    get_test_user_password,
    reset_test_recovery_state,
    issue_recovery_token,
    _recovery_tokens,
    _tokens_lock,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    rate_limiter.reset()
    reset_test_recovery_state()
    register_test_user(
        email="alex@example.com",
        username="Alex Morgan",
        password="OldPassword123!",
        user_id="00000000-0000-0000-0000-000000000001",
    )
    register_test_user(
        email="bob@example.com",
        username="Bob Vance",
        password="OldPassword123!",
        user_id="00000000-0000-0000-0000-000000000002",
    )
    yield
    rate_limiter.reset()
    reset_test_recovery_state()


# =========================================================================
# 1. VALID USERNAME + EMAIL MATCH
# =========================================================================

def test_recovery_valid_match():
    """1. Valid username + email match issues single-use recovery token."""
    response = client.post(
        "/api/password-recovery/verify",
        json={"username": "Alex Morgan", "email": "alex@example.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "recovery_token" in data
    assert len(data["recovery_token"]) > 20
    assert "account verified" in data["message"].lower()


def test_recovery_valid_match_case_insensitive_and_whitespace():
    """Valid match works with leading/trailing whitespace and case differences."""
    response = client.post(
        "/api/password-recovery/verify",
        json={"username": "  alex morgan  ", "email": "  ALEX@EXAMPLE.COM  "},
    )
    assert response.status_code == 200
    assert "recovery_token" in response.json()


# =========================================================================
# 2–4. INVALID USERNAME, INVALID EMAIL, MISMATCH
# =========================================================================

def test_recovery_invalid_username():
    """2. Invalid username with valid email returns 400 generic error."""
    response = client.post(
        "/api/password-recovery/verify",
        json={"username": "Wrong Username", "email": "alex@example.com"},
    )
    assert response.status_code == 400
    assert "invalid username or email" in response.json()["detail"].lower()


def test_recovery_invalid_email():
    """3. Invalid email with registered username returns 400 generic error."""
    response = client.post(
        "/api/password-recovery/verify",
        json={"username": "Alex Morgan", "email": "nonexistent@example.com"},
    )
    assert response.status_code == 400
    assert "invalid username or email" in response.json()["detail"].lower()


def test_recovery_username_email_mismatch():
    """4. Username of User A with Email of User B returns 400 generic error."""
    response = client.post(
        "/api/password-recovery/verify",
        json={"username": "Bob Vance", "email": "alex@example.com"},
    )
    assert response.status_code == 400
    assert "invalid username or email" in response.json()["detail"].lower()


# =========================================================================
# 5–6. PASSWORD VALIDATION & CONFIRMATION MISMATCH
# =========================================================================

def test_recovery_new_password_too_short():
    """5. New password shorter than 8 characters is rejected with 400."""
    # Obtain valid recovery token first
    verify_resp = client.post(
        "/api/password-recovery/verify",
        json={"username": "Alex Morgan", "email": "alex@example.com"},
    )
    token = verify_resp.json()["recovery_token"]

    reset_resp = client.post(
        "/api/password-recovery/reset",
        json={
            "recovery_token": token,
            "new_password": "short",
            "confirm_password": "short",
        },
    )
    assert reset_resp.status_code == 422 or reset_resp.status_code == 400
    detail = reset_resp.json()["detail"].lower()
    assert "at least 8" in detail or "length" in detail


def test_recovery_password_confirmation_mismatch():
    """6. Password confirmation mismatch is rejected with 400."""
    verify_resp = client.post(
        "/api/password-recovery/verify",
        json={"username": "Alex Morgan", "email": "alex@example.com"},
    )
    token = verify_resp.json()["recovery_token"]

    reset_resp = client.post(
        "/api/password-recovery/reset",
        json={
            "recovery_token": token,
            "new_password": "NewSecurePassword123!",
            "confirm_password": "DifferentPassword456!",
        },
    )
    assert reset_resp.status_code == 400
    assert "match" in reset_resp.json()["detail"].lower()


# =========================================================================
# 7–8. SUCCESSFUL PASSWORD UPDATE & LOGIN WITH NEW PASSWORD
# =========================================================================

def test_recovery_successful_password_update():
    """7. Successful password update succeeds and reports success."""
    verify_resp = client.post(
        "/api/password-recovery/verify",
        json={"username": "Alex Morgan", "email": "alex@example.com"},
    )
    token = verify_resp.json()["recovery_token"]

    new_pwd = "UpdatedSecurePassword789!"
    reset_resp = client.post(
        "/api/password-recovery/reset",
        json={
            "recovery_token": token,
            "new_password": new_pwd,
            "confirm_password": new_pwd,
        },
    )
    assert reset_resp.status_code == 200
    data = reset_resp.json()
    assert data["success"] is True
    assert "password updated successfully" in data["message"].lower()

    # 8. Verify the password was actually updated in the user store
    assert get_test_user_password("alex@example.com") == new_pwd


# =========================================================================
# 9–10. EXPIRED & REUSED RECOVERY AUTHORIZATION
# =========================================================================

def test_recovery_expired_token():
    """9. Expired recovery authorization token is rejected with 400."""
    # Issue a token and artificially backdate expiration
    token = issue_recovery_token(
        user_id="00000000-0000-0000-0000-000000000001",
        email="alex@example.com",
        username="Alex Morgan",
        ttl_seconds=-10,  # Expired 10 seconds ago
    )

    reset_resp = client.post(
        "/api/password-recovery/reset",
        json={
            "recovery_token": token,
            "new_password": "NewSecurePassword123!",
            "confirm_password": "NewSecurePassword123!",
        },
    )
    assert reset_resp.status_code == 400
    assert "expired" in reset_resp.json()["detail"].lower()


def test_recovery_token_reuse_rejected():
    """10. Reusing an already-consumed recovery authorization token is rejected."""
    verify_resp = client.post(
        "/api/password-recovery/verify",
        json={"username": "Alex Morgan", "email": "alex@example.com"},
    )
    token = verify_resp.json()["recovery_token"]

    # First reset succeeds
    first_resp = client.post(
        "/api/password-recovery/reset",
        json={
            "recovery_token": token,
            "new_password": "FirstPassword123!",
            "confirm_password": "FirstPassword123!",
        },
    )
    assert first_resp.status_code == 200

    # Second reset with SAME token is rejected
    second_resp = client.post(
        "/api/password-recovery/reset",
        json={
            "recovery_token": token,
            "new_password": "SecondPassword456!",
            "confirm_password": "SecondPassword456!",
        },
    )
    assert second_resp.status_code == 400
    assert "already been used" in second_resp.json()["detail"].lower()


# =========================================================================
# 11. RECOVERY RATE LIMITING
# =========================================================================

def test_recovery_rate_limiting():
    """11. Recovery endpoint enforces rate limiting (5 attempts/minute)."""
    # 5 attempts allowed
    for _ in range(5):
        client.post(
            "/api/password-recovery/verify",
            json={"username": "Invalid", "email": "invalid@example.com"},
        )

    # 6th attempt triggers 429
    res = client.post(
        "/api/password-recovery/verify",
        json={"username": "Invalid", "email": "invalid@example.com"},
    )
    assert res.status_code == 429
    assert "retry-after" in res.headers
    assert "rate limit exceeded" in res.json()["detail"].lower()


# =========================================================================
# 12. MISSING OR MALFORMED RECOVERY AUTHORIZATION
# =========================================================================

def test_recovery_missing_or_unknown_token():
    """12. Reset with nonexistent token is rejected with 400."""
    reset_resp = client.post(
        "/api/password-recovery/reset",
        json={
            "recovery_token": "nonexistent-token-1234567890",
            "new_password": "NewSecurePassword123!",
            "confirm_password": "NewSecurePassword123!",
        },
    )
    assert reset_resp.status_code == 400
    assert "invalid or unknown" in reset_resp.json()["detail"].lower()


# =========================================================================
# 13. GUEST CANNOT ACCESS PRIVILEGED OPERATIONS
# =========================================================================

def test_guest_cannot_access_privileged_operations():
    """13. Recovery does not permit unauthenticated access to Project Memory or Auth."""
    # Project endpoints remain strictly 401
    assert client.get("/api/projects").status_code == 401
    assert client.post("/api/projects", json={"name": "Attacker"}).status_code == 401
    assert client.delete("/api/projects/proj-1").status_code == 401


# =========================================================================
# 14. MALFORMED EMAIL & CONTROL CHARACTERS
# =========================================================================

def test_recovery_malformed_email_rejected():
    """Malformed email is rejected without calling lookup."""
    res = client.post(
        "/api/password-recovery/verify",
        json={"username": "Alex Morgan", "email": "not-an-email"},
    )
    assert res.status_code == 400


def test_recovery_control_characters_rejected():
    """Control characters in username or email are rejected."""
    res = client.post(
        "/api/password-recovery/verify",
        json={"username": "Alex\x00Morgan", "email": "alex@example.com"},
    )
    assert res.status_code == 400


# =========================================================================
# 15. PRODUCTION SECURITY: ZERO SYNTHETIC FALLBACK IN PRODUCTION
# =========================================================================

def test_production_mode_strictly_disables_synthetic_fallback(monkeypatch):
    """In production, missing SUPABASE_SERVICE_ROLE_KEY returns 503; no synthetic fallback."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)

    # 1. Verify endpoint fails safely with 503
    res = client.post(
        "/api/password-recovery/verify",
        json={"username": "Alex Morgan", "email": "alex@example.com"},
    )
    assert res.status_code == 503
    assert "not configured" in res.json()["detail"].lower()

    # 2. Reset endpoint fails safely with 503
    valid_token = issue_recovery_token(
        user_id="00000000-0000-0000-0000-000000000001",
        email="alex@example.com",
        username="Alex Morgan",
    )
    reset_res = client.post(
        "/api/password-recovery/reset",
        json={
            "recovery_token": valid_token,
            "new_password": "NewSecurePassword123!",
            "confirm_password": "NewSecurePassword123!",
        },
    )
    assert reset_res.status_code == 503
    assert "not configured" in reset_res.json()["detail"].lower()


# =========================================================================
# 16. TOKEN-TO-USER BOUNDING: TARGET IS IMMUTABLE
# =========================================================================

def test_token_immutably_bound_to_verified_account():
    """Token is immutably bound to User A; cannot be used to update User B."""
    verify_resp = client.post(
        "/api/password-recovery/verify",
        json={"username": "Alex Morgan", "email": "alex@example.com"},
    )
    token = verify_resp.json()["recovery_token"]

    new_pwd = "NewPasswordForAlex123!"
    reset_resp = client.post(
        "/api/password-recovery/reset",
        json={
            "recovery_token": token,
            "new_password": new_pwd,
            "confirm_password": new_pwd,
        },
    )
    assert reset_resp.status_code == 200

    # User A's password updated
    assert get_test_user_password("alex@example.com") == new_pwd
    # User B's password strictly UNCHANGED
    assert get_test_user_password("bob@example.com") == "OldPassword123!"


# =========================================================================
# 17. BACKWARD COMPATIBILITY: USERNAME VS LEGACY DISPLAY_NAME
# =========================================================================

def test_recovery_with_new_username_field():
    """User registered with new username metadata field is verified successfully."""
    register_test_user(
        email="clara@example.com",
        username="Clara Oswald",
        password="OldPassword123!",
        user_id="00000000-0000-0000-0000-000000000003",
    )
    res = client.post(
        "/api/password-recovery/verify",
        json={"username": "Clara Oswald", "email": "clara@example.com"},
    )
    assert res.status_code == 200
    assert "recovery_token" in res.json()


def test_recovery_with_legacy_display_name_only():
    """Existing user registered with legacy display_name field is verified successfully."""
    register_test_user(
        email="donna@example.com",
        display_name="Donna Noble",
        password="OldPassword123!",
        user_id="00000000-0000-0000-0000-000000000004",
    )
    res = client.post(
        "/api/password-recovery/verify",
        json={"username": "Donna Noble", "email": "donna@example.com"},
    )
    assert res.status_code == 200
    assert "recovery_token" in res.json()



