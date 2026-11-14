"""
backend/tests/test_auth.py
==========================
Tests for user registration, login, and profile retrieval.
"""

import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    payload = {
        "org_name": "New Horizons AI",
        "email": "founder@newhorizons.ai",
        "password": "Password12345!",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user: User):
    payload = {
        "org_name": "Copycat AI",
        "email": test_user.email,
        "password": "Password12345!",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User):
    payload = {
        "email": test_user.email,
        "password": "SuperSecret123!",
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, test_user: User):
    payload = {
        "email": test_user.email,
        "password": "WrongPassword!",
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, test_user: User):
    # Login first
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "SuperSecret123!"},
    )
    token = login_res.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["role"] == test_user.role.value
