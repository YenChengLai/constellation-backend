# File: tests/services/auth_service/test_signup.py
import pytest
from httpx import AsyncClient

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


async def test_signup_success_with_names(client: AsyncClient):
    """
    Tests successful user registration WITH first and last names.
    """
    response = await client.post(
        "/signup",
        json={
            "email": "test@example.com",
            "password": "a_strong_password_123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"
    assert "user_id" in data


async def test_signup_success_without_names(client: AsyncClient):
    """
    Tests successful user registration WITHOUT optional names.
    """
    response = await client.post(
        "/signup",
        json={"email": "anon@example.com", "password": "a_strong_password_123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "anon@example.com"
    # Ensure optional fields are returned as null/None
    assert data["first_name"] is None
    assert data["last_name"] is None


async def test_signup_duplicate_email(client: AsyncClient):
    """
    Tests that registering with a duplicate email fails.
    """
    # First, create a user
    await client.post(
        "/signup",
        json={"email": "duplicate@example.com", "password": "password123"},
    )

    # Then, attempt to create another user with the same email
    response = await client.post(
        "/signup",
        json={"email": "duplicate@example.com", "password": "another_password"},
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "User with this email already exists."}


async def test_signup_invalid_email(client: AsyncClient):
    """
    Tests that registration with an invalid email fails.
    """
    response = await client.post(
        "/signup",
        json={"email": "not-an-email", "password": "password123"},
    )
    assert response.status_code == 422  # Unprocessable Entity
