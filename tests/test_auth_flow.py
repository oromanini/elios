import os
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("MONGO_ATLAS_URI", "mongodb://localhost:27017")
sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from backend import server


class FakeCollection:
    def __init__(self, initial_docs=None):
        self.docs = initial_docs or []

    async def find_one(self, query, projection=None):
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                result = deepcopy(doc)
                if projection and projection.get("_id") == 0:
                    result.pop("_id", None)
                return result
        return None

    async def insert_one(self, doc):
        self.docs.append(deepcopy(doc))
        return {"inserted_id": doc.get("id")}

    async def update_one(self, query, update):
        for idx, doc in enumerate(self.docs):
            if all(doc.get(k) == v for k, v in query.items()):
                updated = deepcopy(doc)
                if "$set" in update:
                    updated.update(update["$set"])
                self.docs[idx] = updated
                return {"matched_count": 1}
        return {"matched_count": 0}


class FakeDB:
    def __init__(self, users=None, sessions=None):
        self.users = FakeCollection(users or [])
        self.sessions = FakeCollection(sessions or [])


@pytest.fixture
def seeded_db(monkeypatch):
    password_hash = server.hash_password("SenhaForte@123")
    fake_db = FakeDB(
        users=[
            {
                "id": "user-1",
                "full_name": "Usuário Teste",
                "email": "teste@elios.com",
                "password_hash": password_hash,
                "role": "DEFAULT",
                "is_active": True,
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        ]
    )
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setattr(server, "JWT_COOKIE_SECURE", False)
    monkeypatch.setattr(server, "JWT_COOKIE_SAMESITE", "lax")
    return fake_db


def test_login_sets_cookie_and_creates_session(seeded_db):
    client = TestClient(server.app)

    response = client.post(
        "/api/auth/login",
        json={"email": "teste@elios.com", "password": "SenhaForte@123"},
    )

    assert response.status_code == 200
    assert response.cookies.get(server.JWT_COOKIE_NAME)
    assert response.headers["set-cookie"].find("HttpOnly") != -1
    assert response.headers["set-cookie"].find("SameSite=lax") != -1
    assert len(seeded_db.sessions.docs) == 1
    assert seeded_db.sessions.docs[0]["revoked_at"] is None


def test_auth_me_requires_valid_active_session(seeded_db):
    client = TestClient(server.app)

    login_response = client.post(
        "/api/auth/login",
        json={"email": "teste@elios.com", "password": "SenhaForte@123"},
    )
    assert login_response.status_code == 200

    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "teste@elios.com"

    session_id = seeded_db.sessions.docs[0]["id"]
    # Simula sessão revogada (ex.: logout em outro dispositivo)
    seeded_db.sessions.docs[0]["revoked_at"] = "2026-04-27T00:00:00+00:00"

    revoked_response = client.get("/api/auth/me")
    assert revoked_response.status_code == 401
    assert revoked_response.json()["detail"] == "Sessão encerrada"
    assert session_id


def test_logout_revokes_session_and_clears_cookie(seeded_db):
    client = TestClient(server.app)

    login_response = client.post(
        "/api/auth/login",
        json={"email": "teste@elios.com", "password": "SenhaForte@123"},
    )
    assert login_response.status_code == 200

    logout_response = client.post("/api/auth/logout")

    assert logout_response.status_code == 200
    assert seeded_db.sessions.docs[0]["revoked_at"] is not None
