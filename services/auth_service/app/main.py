import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, status, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

# This import will now work correctly!S
from packages.shared_utils.database import close_mongo_connection, connect_to_mongo, get_db

from .auth_logic import create_user, login_user, refresh_access_token

# Import from our own modules
from .config import settings
from .models import LoginRequest, RefreshTokenRequest, SignupRequest, TokenResponse, UserPublic

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


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


@app.post("/signup", response_model=UserPublic, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
async def signup_new_user(user_data: SignupRequest, db: AsyncIOMotorDatabase = Depends(get_db)) -> UserPublic:
    new_user = await create_user(db=db, user_data=user_data)
    return new_user


@app.post("/login", response_model=TokenResponse, tags=["Authentication"])
async def login_for_access_token(
    request: Request, login_data: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)
) -> TokenResponse:
    """
    Endpoint to log in a user and receive tokens.
    """
    token_pair = await login_user(db=db, login_data=login_data, request=request)
    return token_pair


@app.post("/token/refresh", response_model=TokenResponse, tags=["Authentication"])
async def refresh_tokens(
    request: Request, token_data: RefreshTokenRequest, db: AsyncIOMotorDatabase = Depends(get_db)
) -> TokenResponse:
    """
    Endpoint to get a new pair of tokens using a refresh token.
    """
    new_token_pair = await refresh_access_token(db=db, refresh_token_data=token_data, request=request)
    return new_token_pair
