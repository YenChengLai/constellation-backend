import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# Add backend/auth-service/ to sys.path (parent of app/)
sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.auth import create_access_token
from app.main import app
from app.models import BEARER


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def mock_database() -> MagicMock:
    return MagicMock()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_login_success(test_client: TestClient, mock_database: MagicMock) -> None:
    # Mock DB response with a valid user
    mock_user = {
        "email": "test@example.com",
        "hashedPassword": "$2b$12$gMLXIaKlt2EzJfLnDDY6au4ttQ8nsRTzAd0qFKQ.G908neRVQns7y",  # Hash for "123456"
        "_id": "12345",
    }
    mock_database.user.find_one.return_value = mock_user

    # Patch get_db to return mock_db
    with patch("app.main.get_db", return_value=mock_database):
        response = test_client.post("/login", json={"email": "test@example.com", "password": "123456"})
        if response.status_code != 200:
            raise AssertionError(f"Expected status code 200, but got {response.status_code}")
        data = response.json()
        if "access_token" not in data:
            raise AssertionError("Expected 'access_token' in response data")
        # Validate the token type in the response
        if data["token_type"] != BEARER:
            raise AssertionError("Expected 'token_type' to be 'bearer'")


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_login_invalid_credentials(test_client: TestClient, mock_database: MagicMock) -> None:
    # Mock DB response with no user
    mock_database.user.find_one.return_value = None

    with patch("app.main.get_db", return_value=mock_database):
        response = test_client.post("/login", json={"email": "test@example.com", "password": "wrongpass"})
        if response.status_code != 401:
            raise AssertionError(f"Expected status code 401, but got {response.status_code}")
        if response.json()["detail"] != "Invalid credentials":
            raise AssertionError("Expected 'detail' to be 'Invalid credentials'")


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_verify_token_success(test_client: TestClient, mock_database: MagicMock) -> None:
    # Create a valid token
    token = create_access_token({"sub": "test@example.com"})
    mock_user = {"email": "test@example.com", "_id": "67d2478e5592b0e4146b140c"}
    mock_database.user.find_one.return_value = mock_user

    with patch("app.main.get_db", return_value=mock_database):
        response = test_client.get("/verify-token", params={"token": token})
        if response.status_code != 200:
            raise AssertionError(f"Expected status code 200, but got {response.status_code}")
        data = response.json()
        print(data)
        if data["email"] != "test@example.com":
            raise AssertionError("Expected 'email' to be 'test@example.com'")
        if data["userId"] != "67d2478e5592b0e4146b140c":
            raise AssertionError("Expected 'userId' to be '67d2478e5592b0e4146b140c'")


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_verify_token_invalid(test_client: TestClient, mock_database: MagicMock) -> None:
    with patch("app.main.get_db", return_value=mock_database):
        response = test_client.get("/verify-token", params={"token": "invalid-token"})
        if response.status_code != 401:
            raise AssertionError(f"Expected status code 401, but got {response.status_code}")
        if response.json()["detail"] != "Could not validate token":
            raise AssertionError("Expected 'detail' to be 'Could not validate token'")


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_health_check(test_client: TestClient) -> None:
    response = test_client.get("/health")
    if response.status_code != 200:
        raise AssertionError(f"Expected status code 200, but got {response.status_code}")
    if response.json()["status"] != "Auth service is up":
        raise AssertionError("Expected 'status' to be 'Auth service is up'")
