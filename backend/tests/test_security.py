import io
import os
import re
import logging
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

os.environ["TEST_USE_SQLITE"] = "true"

from app.main import app
from app.core.rate_limiter import rate_limiter
from app.services.file_processing_service import process_uploaded_file, UnsupportedFileTypeError
from app.models.schemas import ShiftlyAnalysisResult
from google.genai.errors import APIError

client_a = TestClient(app, headers={"Authorization": "Bearer test-token-user-a"})
client_b = TestClient(app, headers={"Authorization": "Bearer test-token-user-b"})
client_unauth = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


# =========================================================================
# 1. SECURITY HEADERS & REQUEST CORRELATION
# =========================================================================

def test_security_headers_present():
    """Verify security headers are applied to API responses."""
    res = client_unauth.get("/api/health")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert "strict-origin" in res.headers.get("Referrer-Policy", "")
    assert "geolocation=()" in res.headers.get("Permissions-Policy", "")
    assert "frame-ancestors 'none'" in res.headers.get("Content-Security-Policy", "")
    assert res.headers.get("X-XSS-Protection") is None


def test_request_id_correlation():
    """Verify X-Request-ID is generated or preserved across responses."""
    # 1. Auto-generated ID
    res1 = client_unauth.get("/api/health")
    req_id1 = res1.headers.get("X-Request-ID")
    assert req_id1 is not None
    assert len(req_id1) >= 16

    # 2. Preserved custom ID
    custom_id = "test-custom-trace-id-12345"
    res2 = client_unauth.get("/api/health", headers={"X-Request-ID": custom_id})
    assert res2.headers.get("X-Request-ID") == custom_id


# =========================================================================
# 2. REQUEST VALIDATION & LIMITS
# =========================================================================

def test_oversized_text_rejected():
    """Verify text input exceeding MAX_INPUT_TEXT_CHARS is rejected."""
    oversized = "A" * 200_001
    res = client_a.post("/api/analyze", json={"text": oversized})
    assert res.status_code == 422


def test_empty_and_whitespace_text_rejected():
    """Verify empty or whitespace-only text is rejected."""
    res_empty = client_a.post("/api/analyze", json={"text": ""})
    assert res_empty.status_code in [400, 422]

    res_ws = client_a.post("/api/analyze", json={"text": "     \n   "})
    assert res_ws.status_code == 400


def test_oversized_file_rejected():
    """Verify uploaded file exceeding 25MB is rejected."""
    # Send large file simulation
    large_payload = b"0" * (25 * 1024 * 1024 + 100)
    res = client_a.post(
        "/api/analyze/file",
        files={"file": ("huge.txt", large_payload, "text/plain")},
    )
    assert res.status_code == 413
    assert "exceeds maximum allowed size" in res.json()["detail"].lower()


def test_malformed_file_signature_rejected():
    """Verify files with fake extensions (e.g. .pdf not matching PDF magic bytes) are rejected."""
    fake_pdf = b"NOT_A_REAL_PDF_HEADER_DATA"
    res = client_a.post(
        "/api/analyze/file",
        files={"file": ("document.pdf", fake_pdf, "application/pdf")},
    )
    assert res.status_code == 415
    assert "not a valid pdf document" in res.json()["detail"].lower()

    fake_docx = b"NOT_A_ZIP_FILE_DOCX"
    res = client_a.post(
        "/api/analyze/file",
        files={"file": ("report.docx", fake_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert res.status_code == 415
    assert "not a valid word document" in res.json()["detail"].lower()


def test_filename_path_traversal_sanitized():
    """Verify path traversal filenames (../../etc/passwd) are safely sanitized."""
    txt_content = b"John: Let us fix the bug.\nMary: Done."
    extracted = process_uploaded_file(txt_content, "../../../../etc/passwd.txt")
    # Filename should be sanitized to basename
    assert extracted.filename == "passwd.txt"
    assert "/" not in extracted.filename
    assert ".." not in extracted.filename


# =========================================================================
# 3. PATH PARAMETER & INJECTION PROTECTION
# =========================================================================

def test_malformed_project_id_path_traversal():
    """Verify malformed path traversal IDs are safely rejected or return 404."""
    # FastAPI path routing or regex pattern rejection
    res = client_a.get("/api/projects/..%2F..%2Fetc%2Fpasswd")
    assert res.status_code in [404, 422, 400]

    # Special characters in project ID
    res2 = client_a.get("/api/projects/<script>alert(1)</script>")
    assert res2.status_code in [404, 422, 400]


def test_html_script_tags_treated_as_plain_text():
    """Verify HTML and script tags in conversation input are treated as raw text."""
    xss_payload = "<script>alert('xss')</script> Marcus: We need approval <img src=x onerror=alert(1)>"
    # Testing extraction normalization
    from app.services.chunking_service import normalize_text
    cleaned = normalize_text(xss_payload)
    assert "<script>" in cleaned or "Marcus" in cleaned
    # Check that search endpoint accepts it as plain string without 500 error
    p = client_a.post("/api/projects", json={"name": "XSS Test Project"}).json()
    search_res = client_a.get(f"/api/projects/{p['id']}/search?q=<script>")
    assert search_res.status_code == 200


# =========================================================================
# 4. AUTHENTICATION & MULTI-TENANT ISOLATION
# =========================================================================

def test_unauthenticated_endpoints_blocked():
    """Verify protected endpoints return 401 when no token is supplied or token is invalid."""
    assert client_unauth.get("/api/projects").status_code == 401
    assert client_unauth.post("/api/projects", json={"name": "Test"}).status_code == 401
    bad_client = TestClient(app, headers={"Authorization": "Bearer fake-invalid-token"})
    assert bad_client.post("/api/analyze", json={"text": "hello"}).status_code in [401, 503]


def test_cross_user_isolation_enforced():
    """Verify User B cannot access, search, or delete User A's project."""
    # User A creates project
    proj_a = client_a.post("/api/projects", json={"name": "User A Secret"}).json()
    proj_id = proj_a["id"]

    # User B cannot access
    assert client_b.get(f"/api/projects/{proj_id}").status_code == 404
    # User B cannot search
    assert client_b.get(f"/api/projects/{proj_id}/search?q=Secret").status_code == 404
    # User B cannot delete
    assert client_b.delete(f"/api/projects/{proj_id}").status_code == 404


# =========================================================================
# 5. RATE LIMITING & RETRY-AFTER
# =========================================================================

def test_rate_limiting_triggers_429():
    """Verify rapid repeated calls trigger HTTP 429 with Retry-After header."""
    rate_limiter.reset()

    # User A sends rapid requests up to the limit
    sample_text = "Alice: Let us meet tomorrow at 10 AM.\nBob: Confirmed."
    with patch("app.api.v1.endpoints.analyze.analyze_communication") as mock_analyze:
        mock_analyze.return_value = ShiftlyAnalysisResult(
            id="test-res",
            title="Meeting",
            analyzedAt="Now",
            stats={"messagesAnalyzed": 2, "participantsCount": 2, "keyPointsCount": 0, "actionsCount": 0, "decisionsCount": 0, "importantDatesCount": 0},
            summary="Meeting planned.",
        )

        limit_hit = False
        retry_after_val = None

        # Send 12 requests (limit is 10/min)
        for i in range(12):
            res = client_a.post("/api/analyze", json={"text": sample_text})
            if res.status_code == 429:
                limit_hit = True
                retry_after_val = res.headers.get("Retry-After")
                assert "rate limit exceeded" in res.json()["detail"].lower()
                break

        assert limit_hit is True
        assert retry_after_val is not None
        assert int(retry_after_val) >= 1


# =========================================================================
# 6. EXTERNAL DEPENDENCY RESILIENCE & ERROR HANDLING
# =========================================================================

def test_gemini_quota_error_handled_safely():
    """Verify Gemini 429 quota exhaustion returns user-friendly HTTP 429 without stack trace."""
    with patch("app.api.v1.endpoints.analyze.analyze_communication") as mock_analyze:
        mock_analyze.side_effect = RuntimeError("AI extraction quota or rate limit exceeded. Please wait a moment before trying again.")
        res = client_a.post("/api/analyze", json={"text": "Meeting notes for review."})
        assert res.status_code == 429
        assert "quota or rate limit exceeded" in res.json()["detail"].lower()
        # Ensure no Python internal trace in response
        assert "Traceback" not in res.text


def test_gemini_timeout_handled_safely():
    """Verify Gemini network timeout returns HTTP 504 without stack trace."""
    with patch("app.api.v1.endpoints.analyze.analyze_communication") as mock_analyze:
        mock_analyze.side_effect = TimeoutError("Gemini call timed out")
        res = client_a.post("/api/analyze", json={"text": "Meeting notes for review."})
        assert res.status_code == 504
        assert "timed out" in res.json()["detail"].lower()
        assert "Traceback" not in res.text


def test_sensitive_tokens_not_leaked_in_logs(caplog):
    """Verify bearer tokens are masked by SafeLoggingFilter."""
    logger = logging.getLogger("shiftly.test")
    with caplog.at_level(logging.INFO):
        logger.info("Handling request with Authorization: Bearer secret_access_token_jwt_value_123")
    log_text = caplog.text
    assert "secret_access_token_jwt_value_123" not in log_text
    assert "[REDACTED]" in log_text
