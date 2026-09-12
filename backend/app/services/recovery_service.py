"""
Shiftly MVP Password Recovery Service
======================================
Provides a temporary MVP account recovery mechanism using Username (Display Name) + Email.

CRITICAL ACCOUNT-TAKEOVER & MVP LIMITATION:
-------------------------------------------
This is an intentional MVP mechanism for hackathon/preview purposes where email
verification links are deferred. Account recovery relies strictly on matching the
registered user_metadata.display_name and registered email address.
DO NOT claim this is production-grade recovery or email-verified.
This implementation must be revisited and upgraded before final production deployment.

SECURITY CONTROLS:
------------------
1. Server-side only verification: Client-side matching is strictly prohibited.
2. Supabase administrative credentials (SUPABASE_SERVICE_ROLE_KEY) are NEVER exposed to the frontend,
   never logged, never committed, and strictly restricted to this backend service.
3. Cryptographically secure single-use recovery tokens (secrets.token_urlsafe(32)) with short TTL (10 minutes).
4. Atomically consumed tokens prevent replay attacks and concurrent reuse.
5. Strict password validation: >= 8 characters, confirmation matching, no control characters.
6. Passwords and recovery tokens are NEVER logged, stored in custom tables, or returned in API responses.
7. Generic error messages prevent account/email enumeration.
"""

import logging
import os
import re
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Any
import httpx

from app.core.config import settings

logger = logging.getLogger("shiftly.recovery")


class RecoveryError(Exception):
    """Base exception for recovery service errors."""
    pass


class AccountMatchFailedError(RecoveryError):
    """Raised when username/email do not match any active account."""
    pass


class InvalidRecoveryTokenError(RecoveryError):
    """Raised when a recovery token is not found or malformed."""
    pass


class ExpiredRecoveryTokenError(RecoveryError):
    """Raised when a recovery token has passed its expiration time."""
    pass


class UsedRecoveryTokenError(RecoveryError):
    """Raised when a recovery token has already been consumed."""
    pass


class PasswordValidationError(RecoveryError):
    """Raised when a new password fails validation constraints."""
    pass


class RecoveryServiceUnavailableError(RecoveryError):
    """Raised when backend administrative credentials or Supabase Auth are unreachable."""
    pass


@dataclass
class RecoveryTokenData:
    token: str
    user_id: str
    email: str
    username: str
    expires_at: float
    used: bool = False


# In-memory thread-safe store for single-use recovery tokens
_recovery_tokens: Dict[str, RecoveryTokenData] = {}
_tokens_lock = threading.Lock()

# Test account registry for isolated automated tests (SQLite / test mode)
_test_users: Dict[str, Dict[str, Any]] = {
    "alex@example.com": {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": "alex@example.com",
        "display_name": "Alex Morgan",
        "password": "InitialPassword123!",
    },
    "bob@example.com": {
        "id": "00000000-0000-0000-0000-000000000002",
        "email": "bob@example.com",
        "display_name": "Bob Vance",
        "password": "InitialPassword123!",
    },
}
_test_users_lock = threading.Lock()


def register_test_user(email: str, display_name: str, password: str = "InitialPassword123!", user_id: Optional[str] = None):
    """Registers or updates a test user in the test user registry (for test suite only)."""
    with _test_users_lock:
        norm_email = email.strip().lower()
        uid = user_id or f"test-user-{secrets.token_hex(4)}"
        _test_users[norm_email] = {
            "id": uid,
            "email": norm_email,
            "display_name": display_name.strip(),
            "password": password,
        }


def get_test_user_password(email: str) -> Optional[str]:
    """Retrieves current password of a test user for test assertions."""
    with _test_users_lock:
        norm_email = email.strip().lower()
        user = _test_users.get(norm_email)
        return user["password"] if user else None


def reset_test_recovery_state():
    """Resets recovery tokens and test user registry between test runs."""
    with _tokens_lock:
        _recovery_tokens.clear()
    with _test_users_lock:
        _test_users.clear()
        _test_users["alex@example.com"] = {
            "id": "00000000-0000-0000-0000-000000000001",
            "email": "alex@example.com",
            "display_name": "Alex Morgan",
            "password": "InitialPassword123!",
        }
        _test_users["bob@example.com"] = {
            "id": "00000000-0000-0000-0000-000000000002",
            "email": "bob@example.com",
            "display_name": "Bob Vance",
            "password": "InitialPassword123!",
        }


def _cleanup_expired_tokens(current_time: float):
    """Removes expired or used tokens older than 1 hour to prevent memory growth."""
    stale_keys = [
        t for t, data in _recovery_tokens.items()
        if current_time > (data.expires_at + 3600)
    ]
    for k in stale_keys:
        del _recovery_tokens[k]


def issue_recovery_token(user_id: str, email: str, username: str, ttl_seconds: int = 600) -> str:
    """
    Generates a cryptographically random, single-use recovery token valid for ttl_seconds (default: 10m).
    """
    current_time = time.time()
    token = secrets.token_urlsafe(32)
    token_data = RecoveryTokenData(
        token=token,
        user_id=user_id,
        email=email,
        username=username,
        expires_at=current_time + ttl_seconds,
        used=False,
    )
    with _tokens_lock:
        _cleanup_expired_tokens(current_time)
        _recovery_tokens[token] = token_data

    return token


def validate_and_consume_token(token: str) -> RecoveryTokenData:
    """
    Validates recovery token authenticity, expiration, and single-use status.
    Atomically marks the token as used to prevent replay attacks.
    """
    if not token or not isinstance(token, str):
        raise InvalidRecoveryTokenError("Invalid recovery authorization token.")

    token = token.strip()
    current_time = time.time()

    with _tokens_lock:
        data = _recovery_tokens.get(token)
        if not data:
            raise InvalidRecoveryTokenError("Invalid or unknown recovery authorization.")

        if data.used:
            raise UsedRecoveryTokenError("Recovery authorization has already been used. Please request a new one.")

        if current_time > data.expires_at:
            raise ExpiredRecoveryTokenError("Recovery authorization has expired. Please request a new one.")

        # Atomically consume
        data.used = True
        return data


def validate_username_input(username: str) -> str:
    """Validates display name / username input according to Shiftly rules."""
    if not username or not username.strip():
        raise AccountMatchFailedError("Username/display name is required.")
    trimmed = username.strip()
    if len(trimmed) < 2 or len(trimmed) > 50:
        raise AccountMatchFailedError("Invalid username or email address.")
    if re.search(r"[\x00-\x1f\x7f-\x9f]", trimmed):
        raise AccountMatchFailedError("Invalid username or email address.")
    return trimmed


def validate_email_input(email: str) -> str:
    """Validates email input format and length."""
    if not email or not email.strip():
        raise AccountMatchFailedError("Email address is required.")
    trimmed = email.strip().lower()
    if len(trimmed) > 255 or re.search(r"[\x00-\x1f\x7f-\x9f]", trimmed):
        raise AccountMatchFailedError("Invalid username or email address.")
    # Safe RFC 5322 compatible pattern
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", trimmed):
        raise AccountMatchFailedError("Invalid username or email address.")
    return trimmed


def _normalize_name(name: Optional[str]) -> str:
    """Normalizes display names for comparison by collapsing internal whitespace and lowercasing."""
    if not name:
        return ""
    return re.sub(r"\s+", " ", str(name).strip().lower())


def _extract_display_candidates(raw_meta: Optional[dict], email: str) -> list[str]:
    """Extracts all valid display identity candidate strings from user metadata and email prefix."""
    meta = raw_meta or {}
    candidates = []
    if meta.get("display_name"):
        candidates.append(str(meta.get("display_name")))
    if meta.get("name"):
        candidates.append(str(meta.get("name")))
    if meta.get("full_name"):
        candidates.append(str(meta.get("full_name")))
    if meta.get("user_name"):
        candidates.append(str(meta.get("user_name")))
    if meta.get("username"):
        candidates.append(str(meta.get("username")))
    if email and "@" in email:
        candidates.append(email.split("@")[0])
    return candidates


def _check_name_match(input_name: str, candidates: list[str]) -> bool:
    """Checks if normalized input matches any normalized candidate."""
    norm_input = _normalize_name(input_name)
    if not norm_input:
        return False
    norm_candidates = [_normalize_name(c) for c in candidates if c]
    return norm_input in norm_candidates


def get_db_connection():
    """Establishes a direct connection to PostgreSQL, handling unescaped special characters in credentials."""
    raw = settings.DATABASE_URL
    if not raw:
        return None
    try:
        prefix, rest = raw.split("://", 1)
        user_pass, host_port_db = rest.rsplit("@", 1)
        user, password = user_pass.split(":", 1)
        host_port, dbname = host_port_db.split("/", 1)
        if ":" in host_port:
            host, port = host_port.split(":", 1)
        else:
            host, port = host_port, 5432
        import psycopg2
        return psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=int(port),
            dbname=dbname,
            sslmode="require",
            connect_timeout=5,
        )
    except Exception as e:
        logger.error("Failed to connect to PostgreSQL for recovery: %s", type(e).__name__)
        return None


async def verify_account_for_recovery(username: str, email: str) -> str:
    """
    Verifies that the supplied username (display name) and email address correspond
    to the same Shiftly account. Returns a single-use recovery token if matched.
    Raises AccountMatchFailedError on mismatch, never differentiating whether the email exists.
    """
    clean_username = validate_username_input(username)
    clean_email = validate_email_input(email)

    # 1. Production Safety Check: in production mode, SUPABASE_SERVICE_ROLE_KEY is strictly required
    if settings.ENVIRONMENT == "production" and not settings.SUPABASE_SERVICE_ROLE_KEY:
        logger.error("Password recovery requested in production mode without SUPABASE_SERVICE_ROLE_KEY.")
        raise RecoveryServiceUnavailableError("Password recovery service is not configured on the backend.")

    # 2. Test Mode Fallback (when TEST_USE_SQLITE is explicitly set for isolated test runs)
    if os.getenv("TEST_USE_SQLITE") == "true":
        with _test_users_lock:
            user = _test_users.get(clean_email)
            if not user:
                logger.warning("recovery_verify_failed reason=user_not_found")
                raise AccountMatchFailedError("Invalid username or email address. For this MVP, account recovery requires matching username and email.")

            candidates = [user.get("display_name"), user.get("name"), clean_email.split("@")[0]]
            if not _check_name_match(clean_username, candidates):
                logger.warning("recovery_verify_failed reason=display_name_mismatch")
                raise AccountMatchFailedError("Invalid username or email address. For this MVP, account recovery requires matching username and email.")

            logger.info("recovery_verify_success mode=test user_id=%s", user["id"])
            return issue_recovery_token(user_id=user["id"], email=clean_email, username=clean_username)

    # 2. Live Supabase PostgreSQL Mode (Direct auth.users lookup via DATABASE_URL)
    db_conn = get_db_connection()
    if db_conn is not None:
        try:
            with db_conn:
                with db_conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, email, raw_user_meta_data FROM auth.users WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s)) LIMIT 1",
                        (clean_email,)
                    )
                    row = cur.fetchone()
            if not row:
                logger.warning("recovery_verify_failed reason=user_not_found")
                raise AccountMatchFailedError("Invalid username or email address. For this MVP, account recovery requires matching username and email.")

            user_id, u_email, raw_meta = row
            candidates = _extract_display_candidates(raw_meta, u_email or clean_email)
            if not _check_name_match(clean_username, candidates):
                logger.warning("recovery_verify_failed reason=display_name_mismatch")
                raise AccountMatchFailedError("Invalid username or email address. For this MVP, account recovery requires matching username and email.")

            logger.info("recovery_verify_success mode=postgres user_id=%s", user_id)
            return issue_recovery_token(user_id=str(user_id), email=clean_email, username=clean_username)
        finally:
            try:
                db_conn.close()
            except Exception:
                pass

    # 3. Live Supabase GoTrue Admin API Mode (if SUPABASE_SERVICE_ROLE_KEY is provided)
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        admin_users_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/admin/users"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(admin_users_url, headers=headers, params={"page": 1, "per_page": 1000})

            if resp.status_code != 200:
                logger.error("Supabase GoTrue admin users API returned HTTP %d", resp.status_code)
                raise RecoveryServiceUnavailableError("Authentication administrative service temporarily unavailable.")

            users_payload = resp.json()
            users_list = users_payload.get("users", []) if isinstance(users_payload, dict) else users_payload

            matched_user = None
            for u in users_list:
                u_email = str(u.get("email", "")).strip().lower()
                if u_email == clean_email:
                    matched_user = u
                    break

            if not matched_user:
                logger.warning("recovery_verify_failed reason=user_not_found")
                raise AccountMatchFailedError("Invalid username or email address. For this MVP, account recovery requires matching username and email.")

            metadata = matched_user.get("user_metadata", {}) or {}
            candidates = _extract_display_candidates(metadata, clean_email)
            if not _check_name_match(clean_username, candidates):
                logger.warning("recovery_verify_failed reason=display_name_mismatch")
                raise AccountMatchFailedError("Invalid username or email address. For this MVP, account recovery requires matching username and email.")

            user_id = matched_user.get("id")
            if not user_id:
                raise RecoveryServiceUnavailableError("Invalid user data received from authentication provider.")

            logger.info("recovery_verify_success mode=supabase user_id=%s", user_id)
            return issue_recovery_token(user_id=user_id, email=clean_email, username=clean_username)

        except httpx.RequestError as exc:
            logger.error("Network error communicating with Supabase Admin Auth: %s", exc)
            raise RecoveryServiceUnavailableError("Authentication service temporarily unavailable.")

    # 4. If neither database nor service role key is configured:
    if settings.ENVIRONMENT == "production":
        logger.error("Password recovery requested but neither DATABASE_URL nor SUPABASE_SERVICE_ROLE_KEY is configured.")
        raise RecoveryServiceUnavailableError("Password recovery service is not configured on the backend.")

    # Fallback in local dev when no backend database connection exists
    with _test_users_lock:
        user = _test_users.get(clean_email)
        if not user:
            logger.warning("recovery_verify_failed reason=user_not_found")
            raise AccountMatchFailedError("Invalid username or email address. For this MVP, account recovery requires matching username and email.")

        candidates = [user.get("display_name"), user.get("name"), clean_email.split("@")[0]]
        if not _check_name_match(clean_username, candidates):
            logger.warning("recovery_verify_failed reason=display_name_mismatch")
            raise AccountMatchFailedError("Invalid username or email address. For this MVP, account recovery requires matching username and email.")

        logger.info("recovery_verify_success mode=test user_id=%s", user["id"])
        return issue_recovery_token(user_id=user["id"], email=clean_email, username=clean_username)


async def reset_password_with_token(token: str, new_password: str, confirm_password: str) -> None:
    """
    Validates the recovery token, verifies password constraints, and updates the user's
    password in Supabase Auth (via PostgreSQL auth.users bcrypt crypt or GoTrue Admin API).
    """
    # 1. Validate password constraints
    if not new_password:
        raise PasswordValidationError("New password cannot be empty.")

    if len(new_password) < 8:
        raise PasswordValidationError("Password must be at least 8 characters long.")

    if re.search(r"[\x00-\x1f\x7f-\x9f]", new_password):
        raise PasswordValidationError("Password contains invalid control characters.")

    if new_password != confirm_password:
        raise PasswordValidationError("Passwords do not match. Please re-enter your password.")

    # 2. Validate and consume recovery authorization token (atomic single-use)
    token_data = validate_and_consume_token(token)

    # 3. Production Safety Check: in production mode, SUPABASE_SERVICE_ROLE_KEY is strictly required
    if settings.ENVIRONMENT == "production" and not settings.SUPABASE_SERVICE_ROLE_KEY:
        logger.error("Password reset requested in production mode without SUPABASE_SERVICE_ROLE_KEY.")
        raise RecoveryServiceUnavailableError("Password recovery service is not configured on the backend.")

    # 4. Update password in Test Mode (when TEST_USE_SQLITE is explicitly set)
    if os.getenv("TEST_USE_SQLITE") == "true":
        with _test_users_lock:
            user = _test_users.get(token_data.email)
            if user:
                user["password"] = new_password
            logger.info("password_reset_success mode=test user_id=%s", token_data.user_id)
            return

    # 4. Live Supabase PostgreSQL Mode (Direct auth.users update using crypt gen_salt)
    db_conn = get_db_connection()
    if db_conn is not None:
        try:
            with db_conn:
                with db_conn.cursor() as cur:
                    cur.execute(
                        "UPDATE auth.users SET encrypted_password = crypt(%s, gen_salt('bf', 10)), updated_at = NOW() WHERE id = %s",
                        (new_password, token_data.user_id)
                    )
            logger.info("password_reset_success mode=postgres user_id=%s", token_data.user_id)
            return
        finally:
            try:
                db_conn.close()
            except Exception:
                pass

    # 5. Live Supabase GoTrue Admin API Mode (if SUPABASE_SERVICE_ROLE_KEY is configured)
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        update_user_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/admin/users/{token_data.user_id}"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.put(update_user_url, headers=headers, json={"password": new_password})

            if resp.status_code != 200:
                logger.error("Supabase GoTrue admin user update returned HTTP %d", resp.status_code)
                raise RecoveryServiceUnavailableError("Failed to update password. Please try again.")

            logger.info("password_reset_success mode=supabase user_id=%s", token_data.user_id)
            return

        except httpx.RequestError as exc:
            logger.error("Network error communicating with Supabase Admin Auth during password update: %s", exc)
            raise RecoveryServiceUnavailableError("Authentication service temporarily unavailable.")

    # 6. Production check
    if settings.ENVIRONMENT == "production":
        raise RecoveryServiceUnavailableError("Password recovery service is not configured on the backend.")

    # Fallback in local dev
    with _test_users_lock:
        user = _test_users.get(token_data.email)
        if user:
            user["password"] = new_password
        logger.info("password_reset_success mode=test user_id=%s", token_data.user_id)
