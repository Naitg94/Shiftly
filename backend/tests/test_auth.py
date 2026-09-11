import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

os.environ["TEST_USE_SQLITE"] = "true"

raw_client = TestClient(app)
auth_client = TestClient(app, headers={"Authorization": "Bearer test-token-123"})


def test_missing_auth_header_projects():
    # Attempting to access projects without token yields 401
    res = raw_client.get("/api/projects")
    assert res.status_code == 401
    assert "Missing Bearer token" in res.json()["detail"]


def test_missing_auth_header_analyze():
    # Attempting to analyze without token yields 401
    res = raw_client.post("/api/analyze", json={"text": "Client: Hello"})
    assert res.status_code == 401
    assert "Missing Bearer token" in res.json()["detail"]


def test_malformed_auth_header():
    # Malformed token (e.g. Basic instead of Bearer)
    client_basic = TestClient(app, headers={"Authorization": "Basic dXNlcjpwYXNz"})
    res = client_basic.get("/api/projects")
    assert res.status_code == 401
    assert "Missing Bearer token" in res.json()["detail"]


def test_invalid_token():
    # Invalid token (non test-token) in test environment
    client_invalid = TestClient(app, headers={"Authorization": "Bearer forged-fake-token"})
    res = client_invalid.get("/api/projects")
    # Will either fail against Supabase Auth with 401 or 503 if unreachable
    assert res.status_code in [401, 503]


def test_valid_token_access():
    # Valid test token allows access
    res = auth_client.get("/api/projects")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_health_remains_public():
    # /api/health should not require authentication
    res = raw_client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


client_a = TestClient(app, headers={"Authorization": "Bearer test-token-user-a"})
client_b = TestClient(app, headers={"Authorization": "Bearer test-token-user-b"})


def test_multi_tenant_isolation_and_deletion():
    # 1. User A creates Project A
    res_a = client_a.post("/api/projects", json={"name": "User A Private Project", "description": "Confidential"})
    assert res_a.status_code == 201
    proj_a = res_a.json()
    proj_a_id = proj_a["id"]

    # 2. User B lists projects -> Should NOT see User A's project
    res_b_list = client_b.get("/api/projects")
    assert res_b_list.status_code == 200
    b_project_ids = [p["id"] for p in res_b_list.json()]
    assert proj_a_id not in b_project_ids

    # 3. User B attempts to GET User A's project -> 404 (No metadata leakage)
    res_b_get = client_b.get(f"/api/projects/{proj_a_id}")
    assert res_b_get.status_code == 404

    # 4. User A saves an analysis to Project A
    sample_analysis = {
        "id": "analysis-iso-1",
        "title": "Confidential Briefing",
        "analyzedAt": "2026-09-11",
        "stats": {
            "messagesAnalyzed": 5,
            "participantsCount": 2,
            "keyPointsCount": 1,
            "actionsCount": 0,
            "decisionsCount": 0,
            "importantDatesCount": 0,
        },
        "summary": "Secret executive decisions regarding merger.",
        "keyPoints": [
            {
                "id": "kp-iso-1",
                "point": "Secret key point",
                "category": "Confidential",
                "source": {
                    "id": "src-1",
                    "sourceType": "Document",
                    "sourceName": "secret.txt",
                    "date": "2026-09-11",
                    "sender": "CEO",
                    "messageRef": "1",
                    "excerpt": "Top secret note",
                },
            }
        ],
        "actions": [],
        "decisions": [],
        "importantDates": [],
    }
    res_save = client_a.post(f"/api/projects/{proj_a_id}/analyses", json=sample_analysis)
    assert res_save.status_code == 201

    # 5. User B attempts to access User A's analysis -> 404
    res_b_analysis = client_b.get(f"/api/projects/{proj_a_id}/analyses/analysis-iso-1")
    assert res_b_analysis.status_code == 404

    # 6. User B attempts to search User A's project memory -> 404
    res_b_search = client_b.get(f"/api/projects/{proj_a_id}/search?q=Secret")
    assert res_b_search.status_code == 404

    # 7. User B attempts to delete User A's analysis -> 404
    res_b_del_ana = client_b.delete(f"/api/projects/{proj_a_id}/analyses/analysis-iso-1")
    assert res_b_del_ana.status_code == 404

    # 8. User B attempts to delete User A's project -> 404
    res_b_del_proj = client_b.delete(f"/api/projects/{proj_a_id}")
    assert res_b_del_proj.status_code == 404

    # 9. User A deletes the analysis -> 204
    res_a_del_ana = client_a.delete(f"/api/projects/{proj_a_id}/analyses/analysis-iso-1")
    assert res_a_del_ana.status_code == 204

    # Verify analysis is deleted from Project A
    res_a_get_ana = client_a.get(f"/api/projects/{proj_a_id}/analyses/analysis-iso-1")
    assert res_a_get_ana.status_code == 404

    # Project A still exists
    res_a_proj_check = client_a.get(f"/api/projects/{proj_a_id}")
    assert res_a_proj_check.status_code == 200

    # 10. User A deletes Project A -> 204
    res_a_del_proj = client_a.delete(f"/api/projects/{proj_a_id}")
    assert res_a_del_proj.status_code == 204

    # Verify project is completely gone
    assert client_a.get(f"/api/projects/{proj_a_id}").status_code == 404

