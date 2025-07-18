# Constellation Backend

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-blue)](https://fastapi.tiangolo.com/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/badge/uv-0.1.40-blue)](https://github.com/astral-sh/uv)

The backend monorepo for the Constellation ecosystem, a personalized suite of applications designed to manage and harmonize various aspects of family life.

This project follows a microservices architecture, where each service is an independent, deployable application built with FastAPI. It emphasizes modern, efficient development practices using tools like `uv` and `ruff`.

## Project Architecture

This is a Python monorepo managed with `uv`. It contains two primary top-level directories:

- **`/services`**: Holds the individual, standalone microservices. Each service is a complete FastAPI application.
- **`/packages`**: Contains shared code (libraries) used by one or more services, promoting the DRY (Don't Repeat Yourself) principle.

```text
constellation-backend/
│
├── .env.example              # Example environment variables file
├── .gitignore
├── pyproject.toml            # Project configuration and dependencies
├── README.md                 # This file
│
├── packages/
│   ├── shared_models/        # Shared Pydantic models
│   └── shared_utils/         # Shared utilities (e.g., database connection)
│
└── services/
    ├── auth_service/         # Handles user authentication and identity
    ├── expense_service/      # Handles expense tracking logic
    └── ...                   # Future services
```

```mermaid
graph TD
    subgraph "constellation-backend (Monorepo)"
        direction TB

        subgraph "services/"
            style services/ fill:#e6f3ff,stroke:#005cb3
            AUTH["fa:fa-server auth_service"]
        end

        subgraph "packages/ (shared codes)"
            style packages/ fill:#e6ffed,stroke:#00642e
            SHARED_UTILS["fa:fa-cogs shared_utils\n (database.py)"]
            SHARED_MODELS["fa:fa-cubes shared_models\n (models.py)"]
        end

        AUTH -->|imports| SHARED_UTILS
        AUTH -->|imports| SHARED_MODELS
    end

    subgraph "External Dependencies"
        DB["fa:fa-database MongoDB 
         constellation_db"]
    end

    AUTH -->|connects to| DB

    style AUTH fill:#fff0e6,stroke:#b35900
```

## Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Database**: [MongoDB](https://www.mongodb.com/)
- **Async Driver**: [Motor](https://motor.readthedocs.io/en/stable/)
- **Package & Env Management**: [uv](https://github.com/astral-sh/uv)
- **Linting & Formatting**: [Ruff](https://github.com/astral-sh/ruff)
- **Authentication**: Stateless JWT with **Refresh Token Rotation**

## Local Development Setup

### Prerequisites

- [Python](https://www.python.org/) (`3.12` or higher) & `pipx`
- [uv](https://github.com/astral-sh/uv) (`pipx install uv`)
- A running [MongoDB](https://www.mongodb.com/try/download/community) instance.

### Installation & Setup

1. **Clone the repository:**

    ```bash
    git clone [https://github.com/YenChengLai/constellation-backend.git](https://github.com/YenChengLai/constellation-backend.git)
    cd constellation-backend
    ```

2. **Create and activate the virtual environment:**

    ```bash
    uv venv
    source .venv/bin/activate  # For macOS / Linux
    # .venv\Scripts\Activate.ps1 # For Windows PowerShell
    ```

3. **Install all dependencies:**
    This command installs all core, service-specific, and development dependencies defined in `pyproject.toml`. The `-e` flag installs your local `packages` and `services` in "editable" mode, which is essential for monorepo development.

    ```bash
    uv pip install -e '.[auth,expense,dev]'
    ```

### Configuration

Create your local `.env` file from the template. This file is ignored by Git and contains your secret values.

```bash
cp .env.example .env
```

Then, edit the `.env` file with your specific settings (e.g., your database URI and a strong `SECRET_KEY`).

|Variable|Description|Example|
|---|---|---|
|MONGODB_URI|The connection string for your MongoDB instance| `mongodb://localhost:27017`|
|SECRET_KEY|A long, random string used for signing JWTs. <b>Keep this secret!</b>|`a-very-long-and-random-secret-string`|
|ALGORITHM|The algorithm used for JWT signing. `HS256` is standard.|`admin@example.com`|
|ADMIN_EMAIL|The email address designated as the super-admin for the system.|`HS256`|
|EXPENSE_SERVICE_URL| The local URL for the expense service, used for inter-service communication (e.g., from the auth service).|`http://127.0.0.1:8001`|

### Running the Services

To avoid potential conflicts with Python version managers like `pyenv`, it is highly recommended to run services by invoking the module directly with `python -m`.

To run the auth_service for development on port 8001:

```bash
python -m uvicorn services.auth_service.app.main:app --reload --port 8001
```

- services.auth_service.app.main:app: Points to the file path and the FastAPI app instance.

- --reload: Enables hot-reloading for development. The server will restart on code changes.

- --port 8001: Specifies the port for this service.

To run multiple services, open a new terminal for each one and run them on different ports:

- Auth Service: uvicorn ... --port 8001

### Unit Testing

This project uses `pytest` for unit testing. Tests are located in the `/tests` directory, mirroring the `/services` structure.

To run all tests:

```bash
pytest
```

### API Endpoints & Testing

Here are the currently available endpoints.

Service: `auth_service`

`GET /health`

- Description: Checks if the service is running
- Test: `curl http://127.0.0.1:8001/health`

`POST /signup`

- Description: Registers a new user.
- Request Body:

```json
{
  "email": "user@example.com",
  "password": "a-very-strong-password"
}
```

- Test Command:

```bash
curl -X POST "[http://127.0.0.1:8001/signup](http://127.0.0.1:8001/signup)" \
-H "Content-Type: application/json" \
-d '{"email": "test@example.com", "password": "a_strong_password_123"}'
```

- Success Response (201 Created):

```json
{
  "user_id": "668aa5a4c5e3f4a1b2c3d4e5",
  "email": "test@example.com",
  "verified": false,
  "created_at": "2025-07-07T07:23:48.123Z"
}
```

`POST /login`

- Description: Logs in a user and returns a pair of tokens.
- Request Body:

```json
{
  "email": "test@example.com",
  "password": "a_strong_password_123"
}
```

- Test Command:

```bash
curl -X POST "[http://127.0.0.1:8001/login](http://127.0.0.1:8001/login)" \
-H "Content-Type: application/json" \
-d '{"email": "test@example.com", "password": "a_strong_password_123"}'
```

- Success Response (201 Created):

```json
{
  "access_token": "ey...",
  "refresh_token": "abc...",
  "token_type": "bearer"
}
```

`POST /token/refresh`

- Description: Exchanges a valid refresh token for a new pair of tokens.
- Request Body:

```json
{
  "refresh_token": "abc...",
}
```

- Test Command:

```bash
curl -X POST "[http://127.0.0.1:8001/token/refresh](http://127.0.0.1:8001/token/refresh)" \
-H "Content-Type: application/json" \
-d '{"refresh_token": "your_refresh_token_here"}'
```

- Success Response (201 Created):

```json
{
  "access_token": "ey...",
  "refresh_token": "abc...",
  "token_type": "bearer"
}
```
