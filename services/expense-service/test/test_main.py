import sys
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# Add backend/expense-service/ to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.main import app
from app.db import get_db


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def mock_database() -> MagicMock:
    return MagicMock()


# pylint: disable=redefined-outer-name
@pytest.fixture(autouse=True, scope="function")
def mock_db(mock_database: MagicMock) -> Generator[MagicMock, None, None]:
    # Override get_db for all tests automatically
    def _mock_get_db() -> MagicMock:
        return mock_database

    app.dependency_overrides[get_db] = _mock_get_db
    yield mock_database
    app.dependency_overrides.clear()


@pytest.fixture
def mock_auth_service() -> Generator[MagicMock, None, None]:
    with patch("app.auth.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"email": "test@example.com", "userId": "123456"}
        mock_get.return_value = mock_response
        yield mock_get


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_create_expense_success(test_client: TestClient, mock_database: MagicMock) -> None:
    # Mock DB insert
    mock_database.expense.insert_one.return_value = None

    response = test_client.post(
        "/expense",
        headers={"Authorization": "Bearer fake-token"},
        json={
            "amount": 50.00,
            "category": "Groceries",
            "date": "2025-03-15T10:00:00Z",
            "description": "Weekly shopping",
            "type": "expense",
            "currency": "USD",
        },
    )
    if response.status_code != 200:
        raise AssertionError(f"Expected status code 200, but got {response.status_code}")
    data = response.json()
    if data["amount"] != 50.0:
        raise ValueError(f"Expected amount to be 50.0, but got {data['amount']}")
    if data["category"] != "Groceries":
        raise ValueError(f"Expected category to be 'Groceries', but got {data['category']}")
    if data["currency"] != "USD":
        raise ValueError(f"Expected currency to be 'USD', but got {data['currency']}")
    if "userId" not in data:
        raise KeyError("Expected 'userId' in response data.")
    if data["userId"] != "123456":
        raise ValueError(f"Expected 'userId' to be '123456', but got {data['userId']}")


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_create_expense_unauthorized(test_client: TestClient) -> None:
    with patch("app.auth.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Invalid token"}
        mock_get.return_value = mock_response

        response = test_client.post(
            "/expense",
            headers={"Authorization": "Bearer invalid-token"},
            json={
                "amount": 50.00,
                "category": "Groceries",
                "date": "2025-03-15T10:00:00Z",
                "description": "Weekly shopping",
                "type": "expense",
                "currency": "USD",
            },
        )
        if response.status_code != 401:
            raise AssertionError(f"Expected status code 401, but got {response.status_code}")
        if response.json()["detail"] != "Invalid token":
            raise ValueError(f"Expected 'detail' to be 'Invalid token', but got {response.json()['detail']}")


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_get_expenses_success(test_client: TestClient, mock_database: MagicMock) -> None:
    # Mock DB find
    mock_expenses = [
        {
            "_id": "1",
            "userId": "123456",
            "groupId": None,
            "amount": 50.0,
            "category": "Groceries",
            "date": datetime(2025, 3, 15, 10, 0, 0),
            "description": "Weekly shopping",
            "type": "expense",
            "currency": "USD",
            "epoch": 1741832400,
        }
    ]
    mock_database.expense.find.return_value = mock_expenses

    response = test_client.get("/expense", headers={"Authorization": "Bearer fake-token"})
    if response.status_code != 200:
        raise AssertionError(f"Expected status code 200, but got {response.status_code}")
    data = response.json()
    if len(data) != 1:
        raise ValueError(f"Expected data length to be 1, but got {len(data)}")
    if data[0]["amount"] != 50.0:
        raise ValueError(f"Expected amount to be 50.0, but got {data[0]['amount']}")
    if data[0]["userId"] != "123456":
        raise ValueError(f"Expected 'userId' to be '123456', but got {data[0]['userId']}")


@pytest.mark.asyncio
async def test_health_check(test_client: TestClient) -> None:
    response = test_client.get("/health")
    if response.status_code != 200:
        raise AssertionError(f"Expected status code 200, but got {response.status_code}")
    data = response.json()

    if data["status"] != "Expense service is up":
        raise ValueError(f"Expected status to be 'Expense service is up', but got {data['status']}")
