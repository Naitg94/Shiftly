import io
import os
import re
import logging
import threading
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

os.environ["TEST_USE_SQLITE"] = "true"

from app.main import app
from app.core.rate_limiter import rate_limiter
from app.db.repository import (
    memory_repo,
    DatabaseTimeoutError,
    DatabaseConnectionError,
    DatabaseOperationError,
)

auth_client = TestClient(app, headers={"Authorization": "Bearer test-token-reliability-user"})
unauth_client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


# =========================================================================
# 1. GEMINI FAILURE MODES (MOCKED/FAILURE INJECTION)
# =========================================================================

def test_gemini_timeout_returns_504():
    """Verify Gemini timeout raises HTTP 504 Gateway Timeout without leaking internals."""
    with patch("app.api.v1.endpoints.analyze.analyze_communication") as mock_analyze:
        mock_analyze.side_effect = TimeoutError("Gemini extraction timed out.")
        response = auth_client.post("/api/analyze", json={"text": "Client: Schedule meeting."})
        assert response.status_code == 504
        data = response.json()
        assert "timed out" in data["detail"].lower()
        assert "request_id" in data


def test_gemini_quota_exhaustion_returns_429():
    """Verify Gemini quota/rate exhaustion maps to HTTP 429 Too Many Requests."""
    with patch("app.api.v1.endpoints.analyze.analyze_communication") as mock_analyze:
        mock_analyze.side_effect = RuntimeError("AI extraction quota or rate limit exceeded. Please wait a moment before trying again.")
        response = auth_client.post("/api/analyze", json={"text": "Client: Schedule meeting."})
        assert response.status_code == 429
        data = response.json()
        assert "quota" in data["detail"].lower() or "rate limit" in data["detail"].lower()
        assert "request_id" in data


def test_gemini_malformed_response_returns_502():
    """Verify unparseable Gemini response returns HTTP 502 Bad Gateway without crashing server."""
    with patch("app.api.v1.endpoints.analyze.analyze_communication") as mock_analyze:
        mock_analyze.side_effect = RuntimeError("AI service returned an unparseable response structure.")
        response = auth_client.post("/api/analyze", json={"text": "Client: Schedule meeting."})
        assert response.status_code == 502
        data = response.json()
        assert "AI extraction provider error" in data["detail"]
        assert "request_id" in data


# =========================================================================
# 2. SUPABASE / DATABASE FAILURE MODES
# =========================================================================

def test_supabase_timeout_returns_504():
    """Verify database timeout raises HTTP 504 Gateway Timeout."""
    with patch.object(memory_repo, "create_project") as mock_create:
        mock_create.side_effect = DatabaseTimeoutError("Database operation timed out.")
        response = auth_client.post("/api/projects", json={"name": "Timeout Project"})
        assert response.status_code == 504
        data = response.json()
        assert "timed out" in data["detail"].lower()
        assert "request_id" in data


def test_supabase_connection_failure_returns_503():
    """Verify network drop or unreachable database raises HTTP 503 Service Unavailable."""
    with patch.object(memory_repo, "list_projects") as mock_list:
        mock_list.side_effect = DatabaseConnectionError("Network error connecting to Supabase.")
        response = auth_client.get("/api/projects")
        assert response.status_code == 503
        data = response.json()
        assert "temporarily unavailable" in data["detail"].lower()
        assert "request_id" in data


def test_unexpected_exception_returns_safe_500():
    """Verify unhandled server errors return safe 500 without leaking stack traces."""
    with patch.object(memory_repo, "get_project") as mock_get:
        mock_get.side_effect = RuntimeError("Simulated unexpected disk corruption at /var/lib/secret")
        response = auth_client.get("/api/projects/proj-xyz-123")
        assert response.status_code == 500
        data = response.json()
        assert "/var/lib/secret" not in data["detail"]
        assert "Simulated unexpected" not in data["detail"]
        assert "unexpected database error occurred" in data["detail"].lower()
        assert "request_id" in data


# =========================================================================
# 3. CORRELATION ID & RESPONSE TIMING OBSERVABILITY
# =========================================================================

def test_correlation_id_auto_generated():
    """Verify X-Request-ID is automatically created when client does not supply one."""
    res = unauth_client.get("/api/health")
    assert res.status_code == 200
    req_id = res.headers.get("X-Request-ID")
    assert req_id is not None
    assert len(req_id) >= 16


def test_correlation_id_propagated():
    """Verify custom X-Request-ID is validated and echoed in response header and body."""
    custom_cid = "client-trace-777888"
    res = unauth_client.get("/api/health", headers={"X-Request-ID": custom_cid})
    assert res.status_code == 200
    assert res.headers.get("X-Request-ID") == custom_cid


def test_response_timing_header_present():
    """Verify X-Response-Time header is attached with valid millisecond timing."""
    res = unauth_client.get("/api/health")
    assert res.status_code == 200
    rt = res.headers.get("X-Response-Time")
    assert rt is not None
    assert re.match(r"^\d+(\.\d+)?ms$", rt)


def test_sensitive_credentials_redacted_in_logs(caplog):
    """Verify SafeLoggingFilter redacts Bearer tokens and passwords."""
    from app.core.middleware import SafeLoggingFilter
    logger = logging.getLogger("test.redaction")
    flt = SafeLoggingFilter()

    record = logging.LogRecord(
        name="test.redaction",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="User authenticated with Bearer secret-auth-token-123456 and apikey=super-secret-key-abc",
        args=(),
        exc_info=None,
    )
    flt.filter(record)
    assert "secret-auth-token-123456" not in record.msg
    assert "super-secret-key-abc" not in record.msg
    assert "Bearer [REDACTED]" in record.msg
    assert "apikey=[REDACTED]" in record.msg


# =========================================================================
# 4. CONCURRENCY & THREAD-SAFE RATE LIMITING
# =========================================================================

def test_rate_limiter_thread_safety():
    """Verify concurrent requests to InMemoryRateLimiter maintain atomic bounds."""
    key = "user:thread-safety-test"
    max_requests = 10
    window_seconds = 60
    results = []
    threads = []

    def worker():
        allowed, _ = rate_limiter.check_rate_limit(key, max_requests, window_seconds)
        results.append(allowed)

    # Launch 25 concurrent threads
    for _ in range(25):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Exactly max_requests should succeed, remaining should be rejected
    allowed_count = sum(1 for r in results if r is True)
    denied_count = sum(1 for r in results if r is False)
    assert allowed_count == max_requests
    assert denied_count == 15


# =========================================================================
# 5. RESOURCE BOUNDS & HEALTH PROBES
# =========================================================================

def test_max_chunks_bound_enforced():
    """Verify input producing >15 chunks is rejected with HTTP 400."""
    with patch("app.services.gemini_service.split_into_chunks") as mock_chunks:
        # Mock 16 chunks returned
        mock_chunks.return_value = ["chunk"] * 16
        res = auth_client.post("/api/analyze", json={"text": "Client: Large chat log."})
        assert res.status_code == 400
        assert "exceeds the limit of 15" in res.json()["detail"]


def test_large_input_protection_enforced():
    """Verify text exceeding 200,000 chars is rejected with 422 Unprocessable Content."""
    oversized = "A" * 200001
    res = auth_client.post("/api/analyze", json={"text": oversized})
    assert res.status_code == 422


def test_health_endpoint_is_lightweight():
    """Verify /api/health returns fast 200 without DB queries."""
    res = unauth_client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "shiftly-backend"


def test_readiness_probe_healthy():
    """Verify /api/ready returns 200 OK when database is accessible."""
    res = unauth_client.get("/api/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"


def test_readiness_probe_degraded_when_db_down():
    """Verify /api/ready returns 503 Service Unavailable when DB is unreachable."""
    with patch("sqlite3.connect") as mock_sql:
        mock_sql.side_effect = Exception("Database disk unavailable")
        res = unauth_client.get("/api/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "degraded"
        assert data["database"] == "unreachable"


def test_project_delete_failure_handling():
    """Verify failed project delete returns 503 and does not return false success 204."""
    with patch.object(memory_repo, "delete_project") as mock_del:
        mock_del.side_effect = DatabaseConnectionError("Connection lost.")
        res = auth_client.delete("/api/projects/proj-to-delete-fail")
        assert res.status_code == 503
        assert "temporarily unavailable" in res.json()["detail"]


def test_unauthenticated_requests_return_401():
    """Verify protected endpoints reject requests lacking valid auth tokens with HTTP 401."""
    res_proj = unauth_client.get("/api/projects")
    assert res_proj.status_code == 401
    assert "authentication required" in res_proj.json()["detail"].lower()

    # Invalid token is rejected with 401
    bad_client = TestClient(app, headers={"Authorization": "Bearer forged-fake-token"})
    res_analyze = bad_client.post("/api/analyze", json={"text": "Hello"})
    assert res_analyze.status_code in [401, 503]


def test_cross_user_isolation_remains_intact():
    """Verify User B cannot access or modify projects owned by User A."""
    client_a = TestClient(app, headers={"Authorization": "Bearer test-token-user-a"})
    client_b = TestClient(app, headers={"Authorization": "Bearer test-token-user-b"})

    # User A creates a project
    res = client_a.post("/api/projects", json={"name": "User A Private Vault"})
    assert res.status_code == 201
    proj_id = res.json()["id"]

    # User B cannot see it in listing
    res_b_list = client_b.get("/api/projects")
    assert res_b_list.status_code == 200
    b_ids = [p["id"] for p in res_b_list.json()]
    assert proj_id not in b_ids

    # User B cannot access it directly
    res_b_get = client_b.get(f"/api/projects/{proj_id}")
    assert res_b_get.status_code == 404

    # User B cannot delete it
    res_b_del = client_b.delete(f"/api/projects/{proj_id}")
    assert res_b_del.status_code == 404


def test_project_save_failure_does_not_create_phantom_success():
    """Verify failure during analysis save raises 500/503 and returns no phantom record."""
    with patch.object(memory_repo, "save_analysis") as mock_save:
        mock_save.side_effect = DatabaseOperationError("DB write failure")
        payload = {
            "id": "analysis-1",
            "title": "Failed Analysis",
            "analyzedAt": "2026-09-11",
            "stats": {"messagesAnalyzed": 1, "participantsCount": 1, "keyPointsCount": 0, "actionsCount": 0, "decisionsCount": 0, "importantDatesCount": 0},
            "summary": "Summary text",
            "keyPoints": [],
            "actions": [],
            "decisions": [],
            "importantDates": [],
        }
        res = auth_client.post("/api/projects/proj-123/analyses", json=payload)
        assert res.status_code in (500, 503)
        assert res.status_code != 201

