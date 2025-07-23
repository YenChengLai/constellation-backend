import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from bson import ObjectId
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorDatabase

from packages.shared_models.models import UserInDB
from packages.shared_utils.database import get_db

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


def hash_password(password: str) -> str:
    """Hashes the password using bcrypt."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_pwd = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_pwd.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    password_bytes = plain_password.encode("utf-8")
    hashed_password_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_password_bytes)


def create_access_token(user: UserInDB) -> str:
    """Creates a short-lived Access Token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode = {"sub": str(user.id), "email": user.email, "exp": expire, "type": "access"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def create_refresh_token(user: UserInDB, db: AsyncIOMotorDatabase, request: Request) -> str:
    """Creates a long-lived Refresh Token and stores its hash in the database."""
    refresh_token = secrets.token_hex(32)
    refresh_token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    session_doc = {
        "user_id": ObjectId(user.id),
        "refresh_token_hash": refresh_token_hash,
        "expires_at": expire,
        "created_at": datetime.now(timezone.utc),
        "user_agent": user_agent,
        "ip_address": ip_address,
    }
    await db.sessions.insert_one(session_doc)
    return refresh_token


async def create_user(db: AsyncIOMotorDatabase, user_data: SignupRequest) -> UserPublic:
    """Handles the business logic for creating a new user."""
    if await db.users.find_one({"email": user_data.email}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User with this email already exists.")

    hashed_password = hash_password(user_data.password)
    new_user_doc = {
        "email": user_data.email,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "hashed_password": hashed_password,
        "verified": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    result = await db.users.insert_one(new_user_doc)
    created_user = await db.users.find_one({"_id": result.inserted_id})
    if not created_user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user.")
    return UserPublic.model_validate(created_user)


async def login_user(db: AsyncIOMotorDatabase, login_data: LoginRequest, request: Request) -> TokenResponse:
    """Handles user login and token generation."""
    user_doc = await db.users.find_one({"email": login_data.email})
    if not user_doc or not verify_password(login_data.password, user_doc["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    user = UserInDB.model_validate(user_doc)

    if not user.verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account not verified. Please contact an administrator."
        )

    access_token = create_access_token(user)
    refresh_token = await create_refresh_token(user, db, request)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


async def refresh_access_token(
    db: AsyncIOMotorDatabase, refresh_token_data: RefreshTokenRequest, request: Request
) -> TokenResponse:
    """Handles refresh token rotation."""
    hashed_token = hashlib.sha256(refresh_token_data.refresh_token.encode("utf-8")).hexdigest()
    old_session = await db.sessions.find_one_and_delete({"refresh_token_hash": hashed_token})

    if not old_session or old_session["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    user_doc = await db.users.find_one({"_id": old_session["user_id"]})
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    user = UserInDB.model_validate(user_doc)

    new_access_token = create_access_token(user)
    new_refresh_token = await create_refresh_token(user, db, request)
    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)


async def logout_user(db: AsyncIOMotorDatabase, refresh_token_data: RefreshTokenRequest):
    """Handles user logout by deleting their session from the database."""
    hashed_token = hashlib.sha256(refresh_token_data.refresh_token.encode("utf-8")).hexdigest()
    await db.sessions.delete_one({"refresh_token_hash": hashed_token})
    return {"message": "Logout successful"}


async def create_group(db: AsyncIOMotorDatabase, group_data: GroupCreate, current_user: UserInDB) -> GroupPublic:
    """Creates a new group for the currently authenticated user."""
    new_group_doc = {
        "name": group_data.name,
        "owner_id": ObjectId(current_user.id),
        "members": [ObjectId(current_user.id)],
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.groups.insert_one(new_group_doc)
    created_group = await db.groups.find_one({"_id": result.inserted_id})
    if not created_group:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create group.")
    return GroupPublic.model_validate(created_group)


async def list_groups_for_user(db: AsyncIOMotorDatabase, current_user: UserInDB) -> list[GroupPublic]:
    """Lists all groups the current user is a member of."""
    user_id = ObjectId(current_user.id)
    groups_cursor = db.groups.find({"members": user_id})
    groups = await groups_cursor.to_list(length=100)
    return [GroupPublic.model_validate(group) for group in groups]
