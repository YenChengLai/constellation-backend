# Auth Service

This is the `auth-service` component of the Expense Tracker v2 backend, built with FastAPI. It handles user authentication (login with email/password) and token verification (JWT) for the monorepo’s microservices.

## Tech Stack

- **Framework**: FastAPI (Python)
- **Server**: Uvicorn (ASGI)
- **Database**: MongoDB (local instance)
- **Authentication**: JWT via `python-jose`, password hashing with `bcrypt`
- **Dependencies**: Managed via `backend/requirements.txt`

## Project Structure

```text
auth-service/
├── app/
|   ├── __init__.py   # Mark library
│   ├── main.py       # FastAPI app and endpoints
│   ├── auth.py       # Authentication logic
│   ├── db.py         # MongoDB connection
│   └── models.py     # Pydantic models
├── test/
│   └── test_auth_main.py  # Unit tests
├── README.md
└── pytest.ini
```

## Testing

### Unit Tests

Test are in `test/test_auth_main.py` and use `pytest` with `TestClient` and mocking.

- Setup:
  - Ensure testing dependencies are installed:
    - Linux/macOS:

      ```bash
      pip install pytest pytest-asyncio requests
      ```

- Run Tests:
  - Linux/macOS:

    ```bash
    cd expense-tracker-v2/backend/auth-service
    pytest -v
    ```

    - Or from `backend/`:

      ```bash
      cd expense-tracker-v2/backend
      pytest auth-service/test/ -v
      ```

    - Excepted output:

      ```text
      test_auth_main.py::test_login_success PASSED
      test_auth_main.py::test_login_invalid_credentials PASSED
      test_auth_main.py::test_verify_token_success PASSED
      test_auth_main.py::test_verify_token_invalid PASSED
      test_auth_main.py::test_health_check PASSED
      ```

- Test Details:
  - Tests cover `/login`, `/verify-token`, and `/health`.
  - Uses mocks for MongoDB (`mock_database`) and `get_db` dependency.

- Configuration:
  - `pytest.ini` in `auth-service/` sets `asyncio_default_fixture_loop_scope=function` to avoid warnings.

### Manual Testing

- Verify Token:
  - Linux/macOS:

    ```bash
    curl --location 'http://127.0.0.1:8002/verify-token?token=<token>
    # Expected: {"email": "test@example.com", "userId": "..."}
    ```

  - Cross-Service: Test with `expense-service`. (Check its [README](../expense-service/README.md))
