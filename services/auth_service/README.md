# Service: Authentication (`auth_service`)

This service is the central authority for user identity and authentication within the Constellation ecosystem.

## Responsibilities

- User registration (`/signup`)
- User login (`/login`) with email and password
- Issuing JWT access and refresh tokens
- Token refreshing and rotation (`/token/refresh`)
- Secure, server-side user logout (`/logout`)
- Enforcing user verification status

## Dependencies

This service relies on the following shared packages:

- `packages/shared_utils`: For database connection and other common utilities.
- `packages/shared_models`: For shared Pydantic data models.

## Configuration

This service uses the following environment variables from the root `.env` file:

| Variable      | Description                                                 |
| ------------- | ----------------------------------------------------------- |
| `MONGODB_URI` | The connection string for your MongoDB instance.            |
| `SECRET_KEY`  | A long, random string used for signing JWTs.                |
| `ALGORITHM`   | The algorithm used for JWT signing (e.g., `HS256`).         |

## How to Run This Service

Ensure you have activated the virtual environment from the root directory (`source .venv/bin/activate`).

To run the `auth_service` on port `8001` with hot-reloading:

```bash
python -m uvicorn services.auth_service.app.main:app --reload --port 8001
```

## API Documentation

This service uses FastAPI's built-in support for OpenAPI to automatically generate interactive API documentation. The code is the single source of truth.

Once the service is running, you can access the API docs at:

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
