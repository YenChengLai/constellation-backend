import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from packages.shared_utils.auth import get_current_user

# This import will now work correctly!
from packages.shared_utils.database import close_mongo_connection, connect_to_mongo, get_db

from .auth_logic import (
    create_group,
    create_user,
    list_groups_for_user,
    login_user,
    logout_user,
    refresh_access_token,
)

# Import from our own modules
from .config import settings
from .models import (
    GroupCreate,
    GroupPublic,
    LoginRequest,
    RefreshTokenRequest,
    SignupRequest,
    TokenResponse,
    UserPublic,
)

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

origins = [
    "http://localhost:5173",  # Local development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 允許指定的來源
    allow_credentials=True,  # 允許傳送 cookies/authorization headers
    allow_methods=["*"],  # 允許所有 HTTP 方法 (GET, POST, etc.)
    allow_headers=["*"],  # 允許所有 HTTP headers
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # 從錯誤中提取第一條、對使用者最有用的訊息
    try:
        first_error = exc.errors()[0]
        # 組合欄位和錯誤訊息
        field = ".".join(map(str, first_error.get("loc", [])))
        message = f"{field}: {first_error.get('msg', 'Invalid input.')}"
    except (IndexError, KeyError):
        message = "Invalid input details provided."

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": message},
    )


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


@app.post("/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["Authentication"])
async def logout(token_data: RefreshTokenRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Endpoint to log out a user by invalidating their refresh token.
    """
    await logout_user(db=db, refresh_token_data=token_data)
    return


@app.post("/groups", response_model=GroupPublic, status_code=status.HTTP_201_CREATED, tags=["Groups"])
async def create_new_group(
    group_data: GroupCreate, db: AsyncIOMotorDatabase = Depends(get_db), current_user: dict = Depends(get_current_user)
) -> GroupPublic:
    """
    Create a new group for the currently authenticated user.
    The creator is automatically set as the owner and first member.
    """
    new_group = await create_group(db=db, group_data=group_data, current_user=current_user)
    return new_group


@app.get("/groups/me", response_model=list[GroupPublic], tags=["Groups"])
async def read_user_groups(
    db: AsyncIOMotorDatabase = Depends(get_db), current_user: dict = Depends(get_current_user)
) -> list[GroupPublic]:
    """
    Retrieve a list of groups that the currently authenticated user is a member of.
    """
    groups = await list_groups_for_user(db=db, current_user=current_user)
    return groups
