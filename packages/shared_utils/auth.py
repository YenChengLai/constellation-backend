# packages/shared_utils/auth.py

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorDatabase

from packages.shared_models.models import UserInDB
from packages.shared_utils.config import settings
from packages.shared_utils.database import get_db

http_bearer_scheme = HTTPBearer(description="Enter JWT Bearer token")


async def get_current_user(
    db: AsyncIOMotorDatabase = Depends(get_db), credentials: HTTPAuthorizationCredentials = Depends(http_bearer_scheme)
) -> UserInDB:
    """
    A reusable dependency to get the current user from a JWT Bearer token.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        expire_time = payload.get("exp")
        if expire_time is None or datetime.fromtimestamp(expire_time, tz=timezone.utc) < datetime.now(timezone.utc):
            raise credentials_exception

        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise credentials_exception

    return UserInDB.model_validate(user)


async def get_current_admin_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """
    Dependency to check if the current user is the admin.
    """
    if current_user.email != settings.ADMIN_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )
    return current_user
