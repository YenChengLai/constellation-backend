# File: services/auth-service/app/auth_logic.py
# Description: Reverted to direct bcrypt usage to avoid passlib warnings.

from datetime import datetime, timezone
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
import bcrypt # Import bcrypt directly

from .models import SignupRequest, UserPublic

def hash_password(password: str) -> str:
    """Hashes the password using bcrypt."""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_pwd = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_pwd.decode('utf-8')

# We don't need verify_password yet, but will add it in the login step.

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