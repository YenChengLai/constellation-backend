import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import HTTPException, status
from jose import jwt
from motor.motor_asyncio import AsyncIOMotorDatabase

from .config import settings
from .models import LoginRequest, RefreshTokenRequest, SignupRequest, TokenResponse, UserPublic


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


def create_access_token(user: dict) -> str:
    """Creates a short-lived Access Token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)  # 15-minute lifespan
    to_encode = {"sub": str(user["_id"]), "email": user["email"], "exp": expire, "type": "access"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def create_refresh_token(user: dict, db: AsyncIOMotorDatabase) -> str:
    """
    Creates a long-lived Refresh Token and stores its hash in the database.
    """
    # 1. Generate a secure, random token string
    refresh_token = secrets.token_hex(32)

    # 2. Hash the token for storage (never store raw tokens)
    refresh_token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()

    # 3. Set expiry date (e.g., 7 days)
    expire = datetime.now(timezone.utc) + timedelta(days=7)

    # 4. Create session document
    session_doc = {
        "user_id": user["_id"],
        "refresh_token_hash": refresh_token_hash,
        "expires_at": expire,
        "created_at": datetime.now(timezone.utc),
    }

    # 5. Insert into the new 'sessions' collection
    await db.sessions.insert_one(session_doc)

    # 6. Return the raw, un-hashed token to the client
    return refresh_token


async def create_user(db: AsyncIOMotorDatabase, user_data: SignupRequest) -> UserPublic:
    """
    Handles the business logic for creating a new user.
    """
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists.",
        )

    # Use our direct hashing function
    hashed_password = hash_password(user_data.password)

    new_user_doc = {
        "email": user_data.email,
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


async def login_user(db: AsyncIOMotorDatabase, login_data: LoginRequest) -> TokenResponse:
    """
    Handles user login and token generation.
    """
    # 1. Find user by email
    user = await db.users.find_one({"email": login_data.email})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    # 2. Verify password
    if not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    # 3. Generate tokens
    access_token = create_access_token(user)
    refresh_token = await create_refresh_token(user, db)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


async def refresh_access_token(db: AsyncIOMotorDatabase, refresh_token_data: RefreshTokenRequest) -> TokenResponse:
    """
    Handles refresh token rotation.
    1. Finds and deletes the old session atomically.
    2. Verifies the session is not expired.
    3. Issues a new pair of access and refresh tokens.
    """
    token_to_hash = refresh_token_data.refresh_token
    hashed_token = hashlib.sha256(token_to_hash.encode("utf-8")).hexdigest()

    # 1. Atomically find the session and delete it to prevent reuse.
    old_session = await db.sessions.find_one_and_delete({"refresh_token_hash": hashed_token})

    if not old_session:
        # This could mean the token was already used, or it's invalid.
        # For security, treat this as a potential breach attempt.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    # 2. Check if the token has expired
    if old_session["expires_at"] < datetime.now(timezone.utc):
        # Even if found, if it's expired, it's invalid.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired")

    # 3. Fetch user data
    user = await db.users.find_one({"_id": old_session["user_id"]})
    if not user:
        # This case is unlikely but good to handle.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # 4. Issue a new pair of tokens
    new_access_token = create_access_token(user)
    new_refresh_token = await create_refresh_token(user, db)

    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)
