import os
import json
import pytest

# Isolate automated tests to test SQLite storage
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

client = TestClient(app, headers={"Authorization": "Bearer test-token-123"})

SAMPLE_SRC = SourceReference(
    id="src-1",
    sourceType="Document",
    sourceName="riverside_notes.pdf",
    date="Oct 12, 2024",
    sender="Architect",
    messageRef="Page 2",
    excerpt="We will finalize drawings by Friday.",
)

SAMPLE_RESULT = ShiftlyAnalysisResult(
    id="test-analysis-401",
    title="Riverside Office Design Review",
    analyzedAt="October 12, 2024 • 11:45 AM",
    stats=AnalysisStats(
        messagesAnalyzed=12,
        participantsCount=3,
        keyPointsCount=2,
        actionsCount=1,
        decisionsCount=1,
        importantDatesCount=1,
    ),
    summary="Client approved the lobby layout and requested ceiling framing drawings by Friday.",
    keyPoints=[
        KeyPointItem(id="kp-1", point="Lobby reception desk width reduced by 300 mm.", category="Layout", source=SAMPLE_SRC),
        KeyPointItem(id="kp-2", point="Ceiling framing requires approved drawings prior to start.", category="Structure", source=SAMPLE_SRC),
    ],
    actions=[
        ActionItem(
            id="act-1",
            action="Issue revised ceiling framing drawings",
            responsiblePerson="Elena Vance (Architect)",
            deadline="Friday, October 15",
            priority="High",
            source=SAMPLE_SRC,
        )
    ],
    decisions=[
        DecisionItem(
            id="dec-1",
            decision="Approved revised lobby layout and material palette",
            approvedBy="David Miller (Client)",
            date="Oct 12",
            source=SAMPLE_SRC,
        )
    ],
    importantDates=[
        ImportantDateItem(
            id="dt-1",
            title="Ceiling Framing Drawings Delivery",
            date="October 15, 2024",
            significance="Prerequisite milestone before framing crew begins",
            source=SAMPLE_SRC,
        )
    ],
)


@pytest.fixture(scope="module")
def project_id():
    res = client.post("/api/projects", json={"name": "Riverside Office", "description": "Commercial renovation"})
    assert res.status_code == 201
    return res.json()["id"]


def test_1_create_project(project_id: str):
    assert project_id is not None
    res = client.get(f"/api/projects/{project_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == project_id
    assert data["name"] == "Riverside Office"


def test_2_list_projects(project_id: str):
    res = client.get("/api/projects")
    assert res.status_code == 200
    projects = res.json()
    assert isinstance(projects, list)
    assert any(p["id"] == project_id for p in projects)


def test_3_get_project(project_id: str):
    res = client.get(f"/api/projects/{project_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == project_id
    assert data["name"] == "Riverside Office"


def test_4_save_analysis_and_child_entities(project_id: str):
    # Save analysis payload
    res = client.post(f"/api/projects/{project_id}/analyses", json=SAMPLE_RESULT.model_dump())
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == "test-analysis-401"
    assert data["project_id"] == project_id
    assert data["key_points_count"] == 2
    assert data["actions_count"] == 1
    assert data["decisions_count"] == 1
    assert data["important_dates_count"] == 1


def test_5_list_project_analyses(project_id: str):
    res = client.get(f"/api/projects/{project_id}/analyses")
    assert res.status_code == 200
    analyses = res.json()
    assert len(analyses) >= 1
    assert analyses[0]["id"] == "test-analysis-401"


def test_6_get_stored_analysis_rehydration(project_id: str):
    res = client.get(f"/api/projects/{project_id}/analyses/test-analysis-401")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "test-analysis-401"
    assert data["title"] == "Riverside Office Design Review"
    assert len(data["keyPoints"]) == 2
    assert len(data["actions"]) == 1
    assert len(data["decisions"]) == 1
    assert len(data["importantDates"]) == 1

    # Verify source reference integrity
    kp_src = data["keyPoints"][0]["source"]
    assert kp_src["sourceName"] == "riverside_notes.pdf"
    assert kp_src["messageRef"] == "Page 2"
    assert "We will finalize drawings" in kp_src["excerpt"]


def test_7_search_project_memory(project_id: str):
    # Search for "ceiling"
    res = client.get(f"/api/projects/{project_id}/search?q=ceiling")
    assert res.status_code == 200
    data = res.json()
    assert data["query"] == "ceiling"
    assert data["total_results"] >= 1
    results = data["results"]
    assert any("ceiling" in r["content"].lower() for r in results)

    # Search for non-existent keyword
    res_none = client.get(f"/api/projects/{project_id}/search?q=xyznonexistent")
    assert res_none.status_code == 200
    assert res_none.json()["total_results"] == 0


def test_8_error_handling():
    # 404 for non-existent project
    res_404 = client.get("/api/projects/fake-project-id")
    assert res_404.status_code == 404

    # 404 for saving to non-existent project
    res_save_404 = client.post("/api/projects/fake-project-id/analyses", json=SAMPLE_RESULT.model_dump())
    assert res_save_404.status_code == 404

    # 422 for invalid project payload (missing name)
    res_422 = client.post("/api/projects", json={"description": "no name"})
    assert res_422.status_code == 422

    # 400 for empty project name
    res_empty_name = client.post("/api/projects", json={"name": "   "})
    assert res_empty_name.status_code == 400


def test_9_regression_endpoints():
    # Health check
    res_h = client.get("/api/health")
    assert res_h.status_code == 200

    # Paste analyze endpoint
    res_p = client.post("/api/analyze", json={"text": "Client: Approved the drawings."})
    assert res_p.status_code in [200, 503]

    # File analyze endpoint
    res_f = client.post("/api/analyze/file", files={"file": ("notes.txt", b"Client: Approved drawings.", "text/plain")})
    assert res_f.status_code in [200, 503]


def test_10_missing_supabase_config_enforcement(monkeypatch):
    from app.core.config import settings
    from app.db.repository import ProjectMemoryRepository, DatabaseConfigurationError
    monkeypatch.setattr(settings, "SUPABASE_URL", None)
    monkeypatch.setattr(settings, "SUPABASE_PUBLISHABLE_KEY", None)
    monkeypatch.setattr(settings, "SUPABASE_ANON_KEY", None)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.setenv("TEST_USE_SQLITE", "false")

    repo = ProjectMemoryRepository(use_sqlite_for_tests=False)

    with pytest.raises(DatabaseConfigurationError):
        repo.create_project("Test")
    with pytest.raises(DatabaseConfigurationError):
        repo.list_projects()
    with pytest.raises(DatabaseConfigurationError):
        repo.get_project("fake-id")
    with pytest.raises(DatabaseConfigurationError):
        repo.delete_project("fake-id")
    with pytest.raises(DatabaseConfigurationError):
        repo.save_analysis("fake-id", SAMPLE_RESULT)
    with pytest.raises(DatabaseConfigurationError):
        repo.list_project_analyses("fake-id")
    with pytest.raises(DatabaseConfigurationError):
        repo.get_analysis("fake-id", "fake-aid")
    with pytest.raises(DatabaseConfigurationError):
        repo.search_project_memory("fake-id", "query")


if __name__ == "__main__":
    pid = project_id()
    test_1_create_project(pid)
    test_2_list_projects(pid)
    test_3_get_project(pid)
    test_4_save_analysis_and_child_entities(pid)
    test_5_list_project_analyses(pid)
    test_6_get_stored_analysis_rehydration(pid)
    test_7_search_project_memory(pid)
    test_8_error_handling()
    test_9_regression_endpoints()
    print("All Project Memory automated tests passed successfully!")
