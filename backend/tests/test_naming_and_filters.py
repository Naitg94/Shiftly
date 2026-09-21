import os
import json
import pytest

os.environ["TEST_USE_SQLITE"] = "true"

from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import (
    ShiftlyAnalysisResult,
    AnalysisStats,
    KeyPointItem,
    ActionItem,
    DecisionItem,
    ImportantDateItem,
    SourceReference,
)

client = TestClient(app, headers={"Authorization": "Bearer test-token-user1"})
client_user2 = TestClient(app, headers={"Authorization": "Bearer test-token-user-b"})
unauthed_client = TestClient(app)

SAMPLE_SRC = SourceReference(
    id="src-filter-1",
    sourceType="Document",
    sourceName="spec.txt",
    date="Oct 20, 2024",
    sender="Lead Eng",
    messageRef="Line 12",
    excerpt="We need to finalize the roadmap.",
)

SAMPLE_RESULT = ShiftlyAnalysisResult(
    id="test-analysis-rename-1",
    title="Original Roadmap Review",
    analyzedAt="October 20, 2024 • 10:00 AM",
    stats=AnalysisStats(
        messagesAnalyzed=5,
        participantsCount=2,
        keyPointsCount=1,
        actionsCount=1,
        decisionsCount=1,
        importantDatesCount=1,
    ),
    summary="Reviewing the roadmap priorities for Q4.",
    keyPoints=[
        KeyPointItem(id="kp-1", point="Priority 1 is latency reduction.", category="Performance", source=SAMPLE_SRC),
    ],
    actions=[
        ActionItem(
            id="act-1",
            action="Benchmark baseline latency",
            responsiblePerson="Dev Lead",
            deadline="Friday",
            priority="High",
            source=SAMPLE_SRC,
        )
    ],
    decisions=[
        DecisionItem(
            id="dec-1",
            decision="Adopt HTTP/2 for gateway",
            approvedBy="CTO",
            date="Oct 20",
            source=SAMPLE_SRC,
        )
    ],
    importantDates=[
        ImportantDateItem(
            id="dt-1",
            title="Q4 Freeze",
            date="November 15, 2024",
            significance="Code freeze for release",
            source=SAMPLE_SRC,
        )
    ],
)


from app.db.repository import _init_local_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    _init_local_db(clear=True)
    yield


@pytest.fixture(scope="module")
def shared_project():
    res = client.post("/api/projects", json={"name": "Rename Test Project", "description": "Testing rename and filters"})
    assert res.status_code == 201
    proj_id = res.json()["id"]
    yield proj_id
    # Clean up project
    client.delete(f"/api/projects/{proj_id}")


def test_project_rename_lifecycle(shared_project: str):
    proj_id = shared_project

    # 1. Rename project
    rename_res = client.patch(f"/api/projects/{proj_id}", json={"name": "Updated Project Name"})
    assert rename_res.status_code == 200
    data = rename_res.json()
    assert data["id"] == proj_id
    assert data["name"] == "Updated Project Name"

    # 2. Verify persistence
    get_res = client.get(f"/api/projects/{proj_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Updated Project Name"

    # 3. Same name rename (idempotent / unchanged)
    same_res = client.patch(f"/api/projects/{proj_id}", json={"name": "Updated Project Name"})
    assert same_res.status_code == 200
    assert same_res.json()["name"] == "Updated Project Name"


def test_project_rename_validation(shared_project: str):
    proj_id = shared_project

    # Empty string
    res = client.patch(f"/api/projects/{proj_id}", json={"name": ""})
    assert res.status_code == 422

    # Whitespace only
    res = client.patch(f"/api/projects/{proj_id}", json={"name": "   "})
    assert res.status_code == 422

    # Exceeding max length (150 chars)
    res = client.patch(f"/api/projects/{proj_id}", json={"name": "A" * 151})
    assert res.status_code == 422

    # Control characters
    res = client.patch(f"/api/projects/{proj_id}", json={"name": "Project\x00Name"})
    assert res.status_code == 422


def test_project_rename_auth_and_ownership(shared_project: str):
    proj_id = shared_project

    # Unauthenticated
    res = unauthed_client.patch(f"/api/projects/{proj_id}", json={"name": "Hacked Name"})
    assert res.status_code == 401

    # Another user
    res = client_user2.patch(f"/api/projects/{proj_id}", json={"name": "User 2 Overwrite"})
    assert res.status_code in [403, 404]


def test_analysis_rename_lifecycle(shared_project: str):
    proj_id = shared_project

    # 1. Save analysis
    save_res = client.post(f"/api/projects/{proj_id}/analyses", json=SAMPLE_RESULT.model_dump())
    assert save_res.status_code == 201
    analysis_id = save_res.json()["id"]
    assert save_res.json()["title"] == "Original Roadmap Review"

    # 2. Rename analysis title
    rename_res = client.patch(
        f"/api/projects/{proj_id}/analyses/{analysis_id}",
        json={"title": "Updated Roadmap Review Q4"}
    )
    assert rename_res.status_code == 200
    data = rename_res.json()
    assert data["id"] == analysis_id
    assert data["project_id"] == proj_id
    assert data["title"] == "Updated Roadmap Review Q4"

    # 3. Verify persistence & intelligence integrity
    get_res = client.get(f"/api/projects/{proj_id}/analyses/{analysis_id}")
    assert get_res.status_code == 200
    full_data = get_res.json()
    assert full_data["id"] == analysis_id
    assert full_data["title"] == "Updated Roadmap Review Q4"
    assert len(full_data["keyPoints"]) == 1
    assert full_data["keyPoints"][0]["point"] == "Priority 1 is latency reduction."
    assert len(full_data["actions"]) == 1
    assert len(full_data["decisions"]) == 1
    assert len(full_data["importantDates"]) == 1

    # 4. Same title rename (idempotent / unchanged)
    same_res = client.patch(
        f"/api/projects/{proj_id}/analyses/{analysis_id}",
        json={"title": "Updated Roadmap Review Q4"}
    )
    assert same_res.status_code == 200
    assert same_res.json()["title"] == "Updated Roadmap Review Q4"


def test_analysis_rename_validation(shared_project: str):
    proj_id = shared_project
    analysis_id = SAMPLE_RESULT.id

    # Empty title
    res = client.patch(f"/api/projects/{proj_id}/analyses/{analysis_id}", json={"title": ""})
    assert res.status_code == 422

    # Whitespace only
    res = client.patch(f"/api/projects/{proj_id}/analyses/{analysis_id}", json={"title": "    "})
    assert res.status_code == 422

    # Exceeding max length (200 chars)
    res = client.patch(f"/api/projects/{proj_id}/analyses/{analysis_id}", json={"title": "T" * 201})
    assert res.status_code == 422

    # Control characters
    res = client.patch(f"/api/projects/{proj_id}/analyses/{analysis_id}", json={"title": "Title\nWith\x00Null"})
    assert res.status_code == 422


def test_analysis_rename_auth_and_ownership(shared_project: str):
    proj_id = shared_project
    analysis_id = SAMPLE_RESULT.id

    # Unauthenticated
    res = unauthed_client.patch(f"/api/projects/{proj_id}/analyses/{analysis_id}", json={"title": "Hacked Title"})
    assert res.status_code == 401

    # Another user
    res = client_user2.patch(f"/api/projects/{proj_id}/analyses/{analysis_id}", json={"title": "User 2 Overwrite"})
    assert res.status_code in [403, 404]
