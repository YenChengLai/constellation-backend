# Service: Expense Tracker (`expense_service`)

This service manages all logic related to tracking income and expenses for both individuals and groups.

## Responsibilities

- Creating, reading, updating, and deleting transactions (CRUD).
- Creating, reading, and deleting user-defined and default categories.
- Associating transactions with users and groups.

## Dependencies

This service relies on the following shared packages:

- `packages/shared_utils`: For database connection, configuration, and user authentication.
- `packages/shared_models`: For shared Pydantic data models like `UserInDB`.

## Configuration

This service uses the global settings from the root `.env` file (e.g., `MONGODB_URI`). It does not require any service-specific environment variables at this time.

## How to Run This Service

Ensure you have activated the virtual environment from the root directory (`source .venv/bin/activate`).

- **To run all services together (recommended):**
    From the project root, run `make run`. The service will be available at `http://localhost:8002`.

- **To run this service standalone:**
    From the project root, run `make run-expense`.

## API Documentation

This service uses FastAPI's built-in support for OpenAPI to automatically generate interactive API documentation. The code is the single source of truth.

Once the service is running, you can access the API docs at:

- **Swagger UI**: [http://localhost:8002/docs](http://localhost:8002/docs)
- **ReDoc**: [http://localhost:8002/redoc](http://localhost:8002/redoc)
