import os
import pytest

# Isolate automated tests to test SQLite storage
os.environ["TEST_USE_SQLITE"] = "true"

from fastapi.testclient import TestClient
from app.main import app
from app.db.repository import memory_repo, _init_local_db

client = TestClient(app)

USER_A_HEADERS = {"Authorization": "Bearer test-token-user-a"}
USER_B_HEADERS = {"Authorization": "Bearer test-token-user-b"}


@pytest.fixture(autouse=True)
def setup_test_db():
    _init_local_db(clear=True)


def test_unauthenticated_account_summary_returns_401():
    res = client.get("/api/account/summary")
    assert res.status_code == 401
    assert "Missing Bearer token" in res.json()["detail"]


def test_unauthenticated_delete_account_returns_401():
    res = client.delete("/api/account")
    assert res.status_code == 401
    assert "Missing Bearer token" in res.json()["detail"]


def test_authenticated_account_summary_returns_valid_structure():
    # Create a project for user A
    proj_res = client.post(
        "/api/projects",
        json={"name": "Account Summary Test Project", "description": "Testing usage metrics"},
        headers=USER_A_HEADERS,
    )
    assert proj_res.status_code == 201

    res = client.get("/api/account/summary", headers=USER_A_HEADERS)
    assert res.status_code == 200
    data = res.json()

    assert "plan" in data
    assert data["plan"]["id"] == "FREE"
    assert "usage" in data
    assert data["usage"]["projects_count"] >= 1
    assert data["usage"]["analyses_limit"] == 30
    assert len(data["usage"]["supported_inputs"]) == 7

    assert "storage" in data
    assert data["storage"]["limit_bytes"] == 104857600  # 100 MB Free limit
    assert "explanation" in data["storage"]
    assert len(data["storage"]["explanation"]["stored"]) == 7


def test_authenticated_delete_account_without_password_returns_422():
    # Attempt delete without password body
    del_res = client.delete("/api/account", headers=USER_A_HEADERS)
    assert del_res.status_code == 422


def test_authenticated_delete_account_with_incorrect_password_returns_400():
    # Attempt delete with incorrect password
    del_res = client.request(
        "DELETE",
        "/api/account",
        headers=USER_A_HEADERS,
        json={"password": "wrong-password"},
    )
    assert del_res.status_code == 400
    assert del_res.json()["detail"] == "Incorrect password. Please try again."


def test_authenticated_delete_account_cascades_projects():
    # User A creates a project
    proj_res = client.post(
        "/api/projects",
        json={"name": "Project to be Deleted", "description": "Cascade test"},
        headers=USER_A_HEADERS,
    )
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    # Delete User A account with verified password
    del_res = client.request(
        "DELETE",
        "/api/account",
        headers=USER_A_HEADERS,
        json={"password": "valid-secret-password"},
    )
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"

    # Verify project is no longer accessible
    get_proj = client.get(f"/api/projects/{proj_id}", headers=USER_A_HEADERS)
    assert get_proj.status_code == 404


def test_cross_user_isolation_on_account_deletion():
    # User B creates a project
    proj_b = client.post(
        "/api/projects",
        json={"name": "User B Project", "description": "Should survive User A deletion"},
        headers=USER_B_HEADERS,
    )
    assert proj_b.status_code == 201
    proj_b_id = proj_b.json()["id"]

    # User A deletes account with password
    del_a = client.request(
        "DELETE",
        "/api/account",
        headers=USER_A_HEADERS,
        json={"password": "valid-secret-password"},
    )
    assert del_a.status_code == 200

    # User B's project is still intact
    get_b = client.get(f"/api/projects/{proj_b_id}", headers=USER_B_HEADERS)
    assert get_b.status_code == 200
    assert get_b.json()["id"] == proj_b_id
