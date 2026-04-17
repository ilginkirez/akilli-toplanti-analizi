import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.routers import auth as auth_router
from src.services.user_store import DEFAULT_DEMO_PASSWORD, UserStore


def build_client(tmp_path: Path, monkeypatch) -> tuple[TestClient, UserStore]:
    store = UserStore(str(tmp_path / "app.db"))
    monkeypatch.setattr(auth_router, "user_store", store)

    app = FastAPI()
    app.include_router(auth_router.router, prefix="/api/auth")
    client = TestClient(app)
    return client, store


def test_seeded_demo_user_can_login_and_list_company_members(tmp_path, monkeypatch):
    client, _ = build_client(tmp_path, monkeypatch)

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "ahmet.yilmaz@company.com",
            "password": DEFAULT_DEMO_PASSWORD,
        },
    )
    assert login_response.status_code == 200
    payload = login_response.json()
    token = payload["token"]
    assert payload["user"]["company_code"] == "COMPANY"

    members_response = client.get(
        "/api/auth/company-members",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert members_response.status_code == 200
    members = members_response.json()["users"]
    assert len(members) >= 6
    assert any(member["email"] == "zeynep.kara@company.com" for member in members)


def test_register_with_new_company_code_creates_company_and_session(tmp_path, monkeypatch):
    client, _ = build_client(tmp_path, monkeypatch)

    register_response = client.post(
        "/api/auth/register",
        json={
            "name": "Ilgin Kirez",
            "email": "ilgin@example.com",
            "password": "superpass1",
            "department": "Product",
            "company_code": "TEAM42",
            "company_name": "Team Forty Two",
        },
    )
    assert register_response.status_code == 200
    payload = register_response.json()
    assert payload["user"]["company_code"] == "TEAM42"
    assert payload["user"]["company_name"] == "Team Forty Two"
    assert payload["user"]["role"] == "manager"

    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {payload['token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "ilgin@example.com"
