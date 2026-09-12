import os
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

os.environ["TEST_USE_SQLITE"] = "true"

from app.main import app
from app.core.config import settings
from app.core.rate_limiter import rate_limiter
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
    id="src-1",
    sourceType="Chat Export",
    sourceName="meeting-notes.txt",
    date="Oct 12",
    sender="Alice",
    messageRef="Msg #1",
    excerpt="Approved specifications",
)

MOCK_RESULT = ShiftlyAnalysisResult(
    id="analysis-guest-1",
    title="Design Review",
    analyzedAt="October 12, 2024",
    stats=AnalysisStats(messagesAnalyzed=1, participantsCount=1),
    summary="Client approved specifications.",
    keyPoints=[KeyPointItem(id="kp-1", point="Approved specifications", category="Design", source=MOCK_SRC)],
    actions=[ActionItem(id="act-1", action="Finalize drawings", responsiblePerson="Bob", source=MOCK_SRC)],
    decisions=[DecisionItem(id="dec-1", decision="Approved specs", approvedBy="Alice", source=MOCK_SRC)],
    importantDates=[ImportantDateItem(id="dt-1", title="Delivery", date="Nov 1", significance="Milestone", source=MOCK_SRC)],
)


@pytest.fixture(autouse=True)
def reset_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


# =========================================================================
# 1. GUEST TEXT ANALYSIS & UNLIMITED ATTEMPTS
# =========================================================================

def test_guest_can_analyze_valid_text():
    """Guest can analyze valid text without providing any authentication token."""
    with patch("app.api.v1.endpoints.analyze.analyze_communication", return_value=MOCK_RESULT):
        res = guest_client.post("/api/analyze", json={"text": "Alice: Approved the project design."})
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "Design Review"
        assert len(data["keyPoints"]) <= 5


def test_guest_unlimited_attempts_no_counter():
    """Guest can make repeated analyses without any attempt counter or daily quota blocking them."""
    with patch("app.api.v1.endpoints.analyze.analyze_communication", return_value=MOCK_RESULT):
        for i in range(5):
            res = guest_client.post("/api/analyze", json={"text": f"Message {i}: Still valid text under limit."})
            assert res.status_code == 200, f"Attempt {i+1} failed"


def test_guest_text_exactly_at_limit_succeeds():
    """Guest text exactly at GUEST_MAX_TEXT_CHAR_COUNT (e.g. 3,000 characters) succeeds."""
    limit = settings.GUEST_MAX_TEXT_CHAR_COUNT
    exact_text = "A" * limit
    assert len(exact_text) == limit

    with patch("app.api.v1.endpoints.analyze.analyze_communication", return_value=MOCK_RESULT):
        res = guest_client.post("/api/analyze", json={"text": exact_text})
        assert res.status_code == 200


def test_guest_text_one_char_over_limit_rejected_413():
    """Guest text 1 char over limit (3,001 chars) is rejected with HTTP 413 and does not call Gemini."""
    limit = settings.GUEST_MAX_TEXT_CHAR_COUNT
    oversized_text = "A" * (limit + 1)
    assert len(oversized_text) == limit + 1

    with patch("app.api.v1.endpoints.analyze.analyze_communication") as mock_gemini:
        res = guest_client.post("/api/analyze", json={"text": oversized_text})
        assert res.status_code == 413
        data = res.json()
        assert "guest mode" in data["detail"].lower()
        assert "create a free account" in data["detail"].lower() or "sign in" in data["detail"].lower()
        # Crucial: verify oversized content NEVER reached Gemini
        mock_gemini.assert_not_called()


# =========================================================================
# 2. AUTHENTICATED USER CAN EXCEED GUEST LIMIT
# =========================================================================

def test_authenticated_user_can_analyze_above_guest_limit():
    """Authenticated users are NOT restricted by the guest character limit."""
    limit = settings.GUEST_MAX_TEXT_CHAR_COUNT
    larger_text = "B" * (limit + 1500)  # 4,500 chars

    with patch("app.api.v1.endpoints.analyze.analyze_communication", return_value=MOCK_RESULT):
        res = auth_client.post("/api/analyze", json={"text": larger_text})
        assert res.status_code == 200


def test_authenticated_user_exceeding_max_input_rejected_413():
    """Authenticated user exceeding MAX_INPUT_TEXT_CHARS (200,000) is rejected."""
    max_limit = settings.MAX_INPUT_TEXT_CHARS
    oversized = "C" * (max_limit + 1)

    res = auth_client.post("/api/analyze", json={"text": oversized})
    # Rejected either by Pydantic validation (422) or endpoint logic (413)
    assert res.status_code in [413, 422]


# =========================================================================
# 3. GUEST FILE ANALYSIS & LIMIT ENFORCEMENT
# =========================================================================

def test_guest_file_within_limit_succeeds():
    """Guest can upload a valid file whose extracted text is within the guest character limit."""
    valid_text = "Alice: Approved the drawings for sector 7."
    with patch("app.api.v1.endpoints.analyze.analyze_communication", return_value=MOCK_RESULT):
        res = guest_client.post(
            "/api/analyze/file",
            files={"file": ("notes.txt", valid_text.encode("utf-8"), "text/plain")},
        )
        assert res.status_code == 200


def test_guest_file_oversized_extracted_text_rejected_413():
    """Guest file whose extracted text exceeds GUEST_MAX_FILE_CHAR_COUNT (1,500) is rejected with 413."""
    limit = settings.GUEST_MAX_FILE_CHAR_COUNT
    oversized_text = "D" * (limit + 1)

    with patch("app.api.v1.endpoints.analyze.analyze_communication") as mock_gemini:
        res = guest_client.post(
            "/api/analyze/file",
            files={"file": ("large_doc.txt", oversized_text.encode("utf-8"), "text/plain")},
        )
        assert res.status_code == 413
        detail = res.json()["detail"]
        assert "1,500" in detail
        assert "create a free account" in detail.lower()
        mock_gemini.assert_not_called()


def test_guest_file_within_limit_exact_1500_succeeds():
    """Guest file whose extracted text is exactly at 1,500 characters succeeds."""
    limit = settings.GUEST_MAX_FILE_CHAR_COUNT
    exact_text = "D" * limit

    with patch("app.api.v1.endpoints.analyze.analyze_communication", return_value=MOCK_RESULT):
        res = guest_client.post(
            "/api/analyze/file",
            files={"file": ("exact_doc.txt", exact_text.encode("utf-8"), "text/plain")},
        )
        assert res.status_code == 200


# =========================================================================
# 4. PROJECT MEMORY STRICT 401 FOR GUESTS
# =========================================================================

def test_guest_cannot_access_project_memory_endpoints():
    """All Project Memory endpoints strictly reject unauthenticated requests with HTTP 401."""
    # 1. Create project
    assert guest_client.post("/api/projects", json={"name": "P"}).status_code == 401

    # 2. List projects
    assert guest_client.get("/api/projects").status_code == 401

    # 3. Get project
    assert guest_client.get("/api/projects/proj-123").status_code == 401

    # 4. Delete project
    assert guest_client.delete("/api/projects/proj-123").status_code == 401

    # 5. Save analysis
    assert guest_client.post("/api/projects/proj-123/analyses", json=MOCK_RESULT.model_dump()).status_code == 401

    # 6. List analyses
    assert guest_client.get("/api/projects/proj-123/analyses").status_code == 401

    # 7. Get analysis
    assert guest_client.get("/api/projects/proj-123/analyses/aid-123").status_code == 401

    # 8. Delete analysis
    assert guest_client.delete("/api/projects/proj-123/analyses/aid-123").status_code == 401

    # 9. Search memory
    assert guest_client.get("/api/projects/proj-123/search?q=test").status_code == 401


def test_authenticated_project_memory_still_functional():
    """Authenticated users can successfully perform Project Memory CRUD and search."""
    # Create project
    create_res = auth_client.post("/api/projects", json={"name": "Guest Suite Project"})
    assert create_res.status_code in [200, 201]
    proj_id = create_res.json()["id"]

    # Save analysis
    save_res = auth_client.post(f"/api/projects/{proj_id}/analyses", json=MOCK_RESULT.model_dump())
    assert save_res.status_code in [200, 201]

    # Search
    search_res = auth_client.get(f"/api/projects/{proj_id}/search?q=Approved")
    assert search_res.status_code == 200

    # Delete project
    del_res = auth_client.delete(f"/api/projects/{proj_id}")
    assert del_res.status_code in [200, 204]
