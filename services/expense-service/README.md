# Expense Service

This is the `expense-service` component of the Expense Tracker v2 backend, built with FastAPI. It provides RESTful APIs for managing expense data, using MongoDB as the database. This service is part of a microservices architecture within the `expense-tracker-v2` monorepo, with authentication currently handled locally (to be moved to `auth-service` in the future).

## Tech Stack

- **Framework**: FastAPI (Python)
- **Server**: Uvicorn (ASGI)
- **Database**: MongoDB (local instance, shared with `auth-service`)
- **Authentication**: JWT validation via `auth-service`
- **Dependencies**: Managed via `backend/requirements.txt`

### Project Structure

```text
expense-service/
├── app/
│   ├── __init__.py   # Marks directory as a Python package
│   ├── main.py       # FastAPI app and endpoints
│   ├── auth.py       # Authentication logic (token verification)
│   ├── db.py         # MongoDB connection
│   └── models.py     # Pydantic models for request/response validation
├── test/
│   └── test_auth_main.py  # Unit tests
├── README.md
└── pytest.ini
```

## Testing

### Unit Tests

Tests are in `test/test_main.py` and use `pytest` with `TestClient` and mocking.

- Setup:
  Ensure testing dependencies are installed:
  - Linux/macOS:

    ```bash
    pip install pytest pytest-asyncio requests
    ```

- Run Tests:
  - Linux/macOS:

    ```bash
    cd expense-tracker-v2/backend/expense-service
    pytest -v
    ```

    - Or from `/backend`:

      ```bash
      cd expense-tracker-v2/backend
      pytest expense-service/test/ -v
      ```

    - Expected output (assuming tests are implemented):

      ```test
      test_main.py::test_create_expense_success PASSED
      test_main.py::test_create_expense_unauthorized PASSED
      test_main.py::test_get_expenses_success PASSED
      test_main.py::test_health_check PASSED
      ```

- Test Details:
  - Tests cover expense creation, retrieval, and health check endpoints.
  - Mocks MongoDB (`mock_database`) and `auth-service` token validation.

- Configuration:
  - `pytest.ini` in `expense-service/` (if present) sets `asyncio_default_fixture_loop_scope=function` to avoid warnings.

### Manual Testing

- Create Expense (requires a valid JWT from `auth-service`):

    ```bash
    curl -X POST "http://127.0.0.1:8001/expenses" \
    -H "Authorization: Bearer <access_token>" \
    -H "Content-Type: application/json" \
    -d '{
      "amount":30.00,
      "category":"Transport",
      "date":"2025-03-14T15:00:00Z",
      "description":"Bus fare",
      "type":"expense",
      "currency":"USD"
    }'
    # Expected: {"id": "...", "amount": 30.00, "category": "Transport", "date": "2025-03-14T15:00:00Z", "description": "Bus fare", "type":"expense", "currency":"USD"}
    ```

  - Get a token first:

    ```bash
    curl --location 'http://127.0.0.1:8002/login' \
    --header 'Content-Type: application/json' \
    --data-raw '{"email": "<test@example.com>", "password": "123456"}'
    ```
  
  - Get Expenses:

      ```bash
      curl "http://127.0.0.1:8001/expenses" \
      -H "Authorization: Bearer <access_token>"
      # Expected: [{"id": "...", "amount": 50.00, "description": "Coffee", "date": "2025-04-09"}, ...]
      ```
  
  - Health Check:

    ```bash
    curl "http://127.0.0.1:8001/health"
    # Expected: {"status": "Expense service is up"}
    ```

  - Cross-Service:
    - Relies on `auth-service` for token validation. (Check its [README](../auth-service/README.md))
