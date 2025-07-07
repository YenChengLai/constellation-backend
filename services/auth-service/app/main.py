# File: services/auth-service/app/main.py (Final Version)

# --- START: Project Root Path Injection (We keep this for robustness) ---
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# --- END: Project Root Path Injection ---

from fastapi import FastAPI, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from contextlib import asynccontextmanager

# Import from our own modules
from .config import settings
from .models import SignupRequest, UserPublic
from .auth_logic import create_user
# This import will now work correctly!
from packages.shared_utils.database import get_db, connect_to_mongo, close_mongo_connection


# --- NEW: Lifespan event handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This code runs on startup
    await connect_to_mongo()
    yield
    # This code runs on shutdown
    await close_mongo_connection()

# Initialize the FastAPI app with the lifespan handler
app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "OK", "service": settings.APP_NAME}

@app.post(
    "/signup",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"]
)
async def signup_new_user(
    user_data: SignupRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> UserPublic:
    new_user = await create_user(db=db, user_data=user_data)
    return new_user