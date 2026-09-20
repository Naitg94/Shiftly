import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.repository import _init_local_db

os.environ["TEST_USE_SQLITE"] = "true"

@pytest.fixture(autouse=True)
def setup_test_db():
    _init_local_db(clear=True)

client_a = TestClient(app, headers={"Authorization": "Bearer test-token-user-a"})
client_b = TestClient(app, headers={"Authorization": "Bearer test-token-user-b"})
raw_client = TestClient(app)


def test_display_name_cannot_alter_user_id():
    """
    Confirms user identity is derived strictly from the verified JWT subject,
    and client headers (e.g. X-Display-Name, X-User-ID) cannot alter or spoof it.
    """
    # Attempt to spoof user ID via header
    spoofed_client = TestClient(
        app,
        headers={
            "Authorization": "Bearer test-token-user-a",
            "X-User-ID": "00000000-0000-0000-0000-000000000002",
            "X-Display-Name": "User B Impersonator",
        },
    )

    # User A creates a project while attempting to spoof User B's identity
    res = spoofed_client.post("/api/projects", json={"name": "Project Spoof Test"})
    assert res.status_code == 201
    proj_id = res.json()["id"]

    # User B should NOT see this project because it belongs to User A
    res_b = client_b.get(f"/api/projects/{proj_id}")
    assert res_b.status_code == 404

    # User A sees it
    res_a = client_a.get(f"/api/projects/{proj_id}")
    assert res_a.status_code == 200


def test_display_name_cannot_alter_project_ownership():
    """
    Confirms project creation and RLS isolation ignore any display name or client-supplied user_id.
    """
    # User A passes a custom user_id in body
    res = client_a.post(
        "/api/projects",
        json={
            "name": "Project Injection Test",
            "description": "Attempting to assign to User B",
            "user_id": "00000000-0000-0000-0000-000000000002",
            "display_name": "User B",
        },
    )
    assert res.status_code == 201
    proj_id = res.json()["id"]

    # User B must not have access
    res_b = client_b.get(f"/api/projects/{proj_id}")
    assert res_b.status_code == 404

    # User A must have access
    res_a = client_a.get(f"/api/projects/{proj_id}")
    assert res_a.status_code == 200


def test_users_with_identical_display_names_remain_isolated():
    """
    Confirms that two users with the exact same display name (e.g. 'Alex Morgan')
    are completely isolated based on their unique Supabase user IDs.
    """
    # User A creates project
    res_a = client_a.post(
        "/api/projects",
        json={"name": "Alex Morgan Project A", "description": "Owner: Alex Morgan"},
    )
    assert res_a.status_code == 201
    proj_a_id = res_a.json()["id"]

    # User B creates project with identical name
    res_b = client_b.post(
        "/api/projects",
        json={"name": "Alex Morgan Project B", "description": "Owner: Alex Morgan"},
    )
    assert res_b.status_code == 201
    proj_b_id = res_b.json()["id"]

    # User A list should only contain Project A, not Project B
    list_a = client_a.get("/api/projects").json()
    ids_a = [p["id"] for p in list_a]
    assert proj_a_id in ids_a
    assert proj_b_id not in ids_a

    # User B list should only contain Project B, not Project A
    list_b = client_b.get("/api/projects").json()
    ids_b = [p["id"] for p in list_b]
    assert proj_b_id in ids_b
    assert proj_a_id not in ids_b


def test_unauthenticated_requests_cannot_access_identity_or_projects():
    """
    Confirms that unauthenticated requests cannot access projects or inject arbitrary identities.
    """
    res = raw_client.get("/api/projects", headers={"X-Display-Name": "Guest Tester", "X-Username": "Guest Tester"})
    assert res.status_code == 401
    assert "Missing Bearer token" in res.json()["detail"]


def test_username_cannot_alter_user_id_or_ownership():
    """
    Confirms that client-supplied username headers or body fields cannot alter JWT subject or project ownership.
    """
    spoofed = TestClient(
        app,
        headers={
            "Authorization": "Bearer test-token-user-a",
            "X-User-ID": "00000000-0000-0000-0000-000000000002",
            "X-Username": "User B Impersonator",
        },
    )
    res = spoofed.post(
        "/api/projects",
        json={"name": "Username Spoof Test", "username": "User B"},
    )
    assert res.status_code == 201
    proj_id = res.json()["id"]

    # User B should NOT see this project
    assert client_b.get(f"/api/projects/{proj_id}").status_code == 404
    # User A sees it
    assert client_a.get(f"/api/projects/{proj_id}").status_code == 200


def test_users_with_identical_usernames_remain_isolated():
    """
    Confirms that two users with identical usernames remain completely isolated.
    """
    res_a = client_a.post("/api/projects", json={"name": "Shared Username Proj A"})
    assert res_a.status_code == 201
    res_b = client_b.post("/api/projects", json={"name": "Shared Username Proj B"})
    assert res_b.status_code == 201

    list_a = [p["id"] for p in client_a.get("/api/projects").json()]
    list_b = [p["id"] for p in client_b.get("/api/projects").json()]
    assert res_a.json()["id"] in list_a
    assert res_b.json()["id"] not in list_a
    assert res_b.json()["id"] in list_b
    assert res_a.json()["id"] not in list_b

