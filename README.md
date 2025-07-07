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

```
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
    ├── auth-service/         # Handles user authentication and identity
    ├── expense-service/      # Handles expense tracking logic
    └── ...                   # Future services
```

## Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Database**: [MongoDB](https://www.mongodb.com/)
- **Async Driver**: [Motor](https://motor.readthedocs.io/en/stable/)
- **Package & Env Management**: [uv](https://github.com/astral-sh/uv)
- **Linting & Formatting**: [Ruff](https://github.com/astral-sh/ruff)
- **Authentication**: Stateless JWT

## Getting Started

Follow these instructions to set up the development environment on your local machine.

### Prerequisites

- [Python](https://www.python.org/) (`3.12` or higher)
- `pipx` for installing `uv` (recommended)

    ```bash
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    ```

- [uv](https://github.com/astral-sh/uv)

    ```bash
    pipx install uv
    ```

- A running [MongoDB](https://www.mongodb.com/try/download/community) instance (local or on a cloud service like MongoDB Atlas).

### Installation & Setup

1. **Clone the repository:**

    ```bash
    git clone [https://github.com/YenChengLai/constellation-backend.git](https://github.com/YenChengLai/constellation-backend.git)
    cd constellation-backend
    ```

2. **Create the virtual environment:**
    `uv` will create a `.venv` folder in your project directory.

    ```bash
    uv venv
    ```

3. **Activate the virtual environment:**
    - On macOS / Linux:

        ```bash
        source .venv/bin/activate
        ```

    - On Windows (PowerShell):

        ```bash
        .venv\Scripts\Activate.ps1
        ```

4. **Install all dependencies:**
    This command installs all core, service-specific, and development dependencies defined in `pyproject.toml`. The `-e` flag installs your local `packages` and `services` in "editable" mode, which is essential for monorepo development.

    ```bash
    uv pip install -e '.[auth,expense,dev]'
    ```

### Configuration

This project uses a `.env` file to manage environment variables. Create a `.env` file in the project root by copying the example file.

```bash
cp .env.example .env
```

Then, fill in the .env file with your specific settings.

|Variable|Description|Example|
|---|---|---|
|MONGODB_URI|The connection string for your MongoDB instance| `mongodb://localhost:27017`|
|SECRET_KEY|A long, random string used for signing JWTs. <b>Keep this secret!</b>|`a-very-long-and-random-secret-string`|
|ALGORITHM|The algorithm used for JWT signing. `HS256` is standard.|`admin@example.com`|
|ADMIN_EMAIL|The email address designated as the super-admin for the system.|`admin@example.com`|
|EXPENSE_SERVICE_URL| The local URL for the expense service, used for inter-service communication (e.g., from the auth service).|`http://127.0.0.1:8001`|

### Running the Services

Each service can be run independently. To run the auth-service for development:

```bash
uvicorn services.auth-service.app.main:app --reload --port 8000
```

- services.auth-service.app.main:app: Points to the file path and the FastAPI app instance.

- --reload: Enables hot-reloading for development. The server will restart on code changes.

- --port 8000: Specifies the port for this service.

To run multiple services, open a new terminal for each one and run them on different ports:

- Auth Service: uvicorn ... --port 8000

- Expense Service: uvicorn services.expense-service.app.main:app --reload --port 8001
