from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def _build_client() -> TestClient:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{tmp.name}"
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-auth-api"

    from app.database import create_tables
    from app.main import app

    asyncio.run(create_tables())
    return TestClient(app)


def test_register_and_login_accept_passwords_longer_than_72_bytes() -> None:
    client = _build_client()
    password = "A" * 100

    register = client.post(
        "/api/auth/register",
        json={
            "email": "auth-long@example.com",
            "password": password,
            "full_name": "Auth Long",
        },
    )
    assert register.status_code == 201, register.text
    tokens = register.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    login = client.post(
        "/api/auth/login",
        json={
            "email": "auth-long@example.com",
            "password": password,
        },
    )
    assert login.status_code == 200, login.text
    logged_in = login.json()
    assert logged_in["access_token"]
    assert logged_in["refresh_token"]


def test_refresh_returns_new_access_token_for_registered_user() -> None:
    client = _build_client()

    register = client.post(
        "/api/auth/register",
        json={
            "email": "refresh-user@example.com",
            "password": "refresh-password-123",
            "full_name": "Refresh User",
        },
    )
    assert register.status_code == 201, register.text
    refresh_token = register.json()["refresh_token"]

    refreshed = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refreshed.status_code == 200, refreshed.text
    payload = refreshed.json()
    assert payload["access_token"]
    assert payload["refresh_token"]


def test_google_login_creates_new_user_and_returns_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client()

    from app.api import auth as auth_api

    monkeypatch.setattr(
        auth_api,
        "_verify_google_id_token",
        lambda credential: auth_api.GoogleIdentity(
            email="google-user@example.com",
            email_verified=True,
            full_name="Google User",
        ),
    )

    response = client.post(
        "/api/auth/google",
        json={"credential": "fake-google-token-value-that-is-long-enough"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["access_token"]
    assert payload["refresh_token"]

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )
    assert me.status_code == 200, me.text
    profile = me.json()
    assert profile["email"] == "google-user@example.com"
    assert profile["full_name"] == "Google User"


def test_google_login_reuses_existing_user_record(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client()

    register = client.post(
        "/api/auth/register",
        json={
            "email": "reuse-google@example.com",
            "password": "reuse-password-123",
            "full_name": "",
        },
    )
    assert register.status_code == 201, register.text

    from app.api import auth as auth_api

    monkeypatch.setattr(
        auth_api,
        "_verify_google_id_token",
        lambda credential: auth_api.GoogleIdentity(
            email="reuse-google@example.com",
            email_verified=True,
            full_name="Linked Google User",
        ),
    )

    response = client.post(
        "/api/auth/google",
        json={"credential": "another-fake-google-token-value"},
    )
    assert response.status_code == 200, response.text

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {response.json()['access_token']}"},
    )
    assert me.status_code == 200, me.text
    profile = me.json()
    assert profile["email"] == "reuse-google@example.com"
    assert profile["full_name"] == "Linked Google User"
