# Backend Services

The backend services for expense-tracker-v2 includes auth-service and expense-tracker. The former one focuses on handling token issuing and validating, which the latter one works on the domain logic in expense tracking.

## Setup Instructions

### 1. Prerequisites

- Python 3.12+:
  - Linux: Install via package manager (e.g., `sudo apt-get install python3.12`) or `pyenv`:

    ```bash
    curl https://pyenv.run | bash
    pyenv install 3.12.2
    pyenv global 3.12.2
    ```

  - macOS: Use Homebrew or `pyenv`:

    ```bash
    brew install python@3.12
    # OR with pyenv
    brew install pyenv
    pyenv install 3.12.2
    pyenv global 3.12.2
    ```

- MongoDB: Install and run a local MongoDB instance:
  - Linux: install and start

    ```bash
    sudo apt-get install mongodb  # Ubuntu/Debian
    sudo systemctl start mongodb  # Start the service
    mongosh  # Verify with: show dbs
    ```
  
  - macOS: Install via Homebrew and start:

    ```bash
    brew tap mongodb/brew
    brew install mongodb-community
    brew services start mongodb-community
    mongosh  # Verify with: show dbs
    ```

- Git: Clone the monorepo if not already done:
  - Linux/macOS:

    ```bash
    git clone <repo-url>
    cd expense-tracker-v2
    ```

### 2. Set Up the Shared Virtual Environment

The backend services share a virtual environment located at `backend/venv/` .

- Create the Virtual Environment (if not already set up):
  - Linux/macOS:

    ```bash
    cd expense-tracker-v2/backend
    python3 -m venv venv  # Use python3 explicitly on macOS if python is Python 2
    source venv/bin/activate
    ```

- Install Dependencies:
  - Linux/macOS:

    ```bash
    pip install -r requirements.txt
    ```

### 3. Configure MongoDB

- Database: The service uses a local MongoDB instance (`mongodb://localhost:27017`).
- Initial User: Add a test user to the `expense_tracker` database:
  - Linux/macOS:

    ```bash
    mongosh
    use expense_tracker
    db.user.insertOne({
      "email": "test@example.com",
      "hashedPassword": "$2b$12$gMLXIaKlt2EzJfLnDDY6au4ttQ8nsRTzAd0qFKQ.G908neRVQns7y"  // Hash for 123456
    })
    ```

    You can get the hashed password by using `generate_hash.py`

    ```bash
    python3 generate_hash.py 123456
    # Get the hashed value for 123456
    ```

### 4. Run the Auth Service

- Linux/macOS:
  
  ```bash
  make start
  ```

  The defined makefile will do the following:

  ```bash
  cd backend/expense-service && uvicorn app.main:app --port 8001 --reload
  cd backend/auth-service && uvicorn app.main:app --port 8002 --reload
  ```

  - `--reload`: Auto-restarts on code changes (development only).
  - `--port 8002`: Avoids conflicts with other services (e.g., `expense-service` on 8001)

### 5. Verify It's Working

- Health Check:
  - Linux/macOS:

  ```bash
  curl http://127.0.0.1:8002/health
  # Expected: {"status": "Auth service is up"}
  ```

- Login:
  - Linux/macOS:

  ```bash
  curl -X POST "http://127.0.0.1:8002/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "<test@example.com>", "password": "123456"}'
  # Expected: {"access_token": "...", "token_type": "bearer"}
  ```
  
## Development Notes

### Common Issues

- MongoDB Not Running:
  - Error: `pymongo.errors.ServerSelectionTimeoutError` .
  - Fix:
    - Linux: `sudo systemctl start mongodb`
    - macOS: `brew services start mongodb-community`
    - Verify: `mongosh --eval "db.runCommand({ping: 1})"`
- Path Resolution:
  - Imports like `from app.main import app` may fail in tests or IDEs.
  - Fix: Run from `backend/` with `pytest auth-service/test/` or configure your IDE (e.g., VS Code’s settings.json):

    ```json
    "python.analysis.extraPaths": ["${workspaceFolder}/backend/auth-service/app"]
    ```

- Dependency Conflicts:
  - If `pip install` fails, recreate the `venv`:
    - Linux/macOS:

      ```bash
      rm -rf venv
      python3 -m venv venv
      source venv/bin/activate
      pip install -r requirements.txt
      ```

- Virtual Environment Activation:
  - Manually running `source venv/bin/activate` can be tedious
  - Solution: Use `direnv`:
    - Linux: `sudo apt-get install direnv`
    - macOS: `brew install direnv`
    - Then:

      ```bash
      echo 'eval "$(direnv hook bash)"' >> ~/.bashrc  # or ~/.zshrc for Zsh
      source ~/.bashrc  # or ~/.zshrc
      cd backend
      echo "source venv/bin/activate" > .envrc
      direnv allow
      ```
