import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from bson import ObjectId
from fastapi import HTTPException, Request, status
from jose import jwt
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from packages.shared_models.models import UserInDB

from .config import settings
from .models import (
    AddMemberRequest,
    GroupCreate,
    GroupPublic,
    LoginRequest,
    RefreshTokenRequest,
    SignupRequest,
    TokenResponse,
    UserInGroup,
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
    """
    Creates a new group for the currently authenticated user.
    """
    # 1. 準備要寫入資料庫的 Group 文件
    user_id_obj = ObjectId(current_user.id)
    new_group_doc = {
        "name": group_data.name,
        "owner_id": user_id_obj,
        "members": [user_id_obj],  # Initially, members array contains only ObjectIds
        "created_at": datetime.now(timezone.utc),
    }

    result = await db.groups.insert_one(new_group_doc)

    # 2. 取得剛建立的完整文件
    created_group_doc = await db.groups.find_one({"_id": result.inserted_id})
    if not created_group_doc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create group.")

    members_cursor = db.users.find({"_id": {"$in": created_group_doc["members"]}})
    members_list = await members_cursor.to_list(length=None)

    # 用查詢到的完整使用者文件，來取代原本只有 ID 的列表
    created_group_doc["members"] = [UserInGroup.model_validate(mem) for mem in members_list]

    # 4. 使用填充後的資料來進行最終的驗證和回傳
    return GroupPublic.model_validate(created_group_doc)


async def list_groups_for_user(db: AsyncIOMotorDatabase, current_user: UserInDB) -> list[GroupPublic]:
    """
    Lists all groups the current user is a member of, with populated member details.
    """
    user_id = ObjectId(current_user.id)

    # 1. 找到使用者所屬的所有群組文件
    groups_cursor = db.groups.find({"members": user_id})
    groups_docs = await groups_cursor.to_list(length=100)

    populated_groups = []
    for group in groups_docs:
        # 2. 對於每一個群組，獲取其成員 ID 列表
        member_ids = group.get("members", [])

        # 3. 根據 ID 列表，去 users collection 查詢所有成員的詳細資料
        members_cursor = db.users.find({"_id": {"$in": member_ids}})
        members_list = await members_cursor.to_list(length=None)

        # 4. 將查詢到的成員資料，轉換為 UserInGroup 模型
        group["members"] = [UserInGroup.model_validate(mem) for mem in members_list]

        # 5. 將填充完畢的 group 文件，轉換為 GroupPublic 模型
        populated_groups.append(GroupPublic.model_validate(group))

    return populated_groups


async def list_unverified_users(db: AsyncIOMotorDatabase) -> list[UserPublic]:
    """
    Retrieves a list of all users with verified=false.
    """
    users_cursor = db.users.find({"verified": False})
    users = await users_cursor.to_list(length=1000)  # 最多顯示 1000 名未驗證使用者
    return [UserPublic.model_validate(user) for user in users]


async def verify_user(db: AsyncIOMotorDatabase, user_id: str) -> UserPublic:
    """
    Sets a user's 'verified' status to True.
    """
    user_to_verify = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user_to_verify:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id {user_id} not found.")

    updated_user = await db.users.find_one_and_update(
        {"_id": ObjectId(user_id)}, {"$set": {"verified": True}}, return_document=ReturnDocument.AFTER
    )

    if not updated_user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user.")

    return UserPublic.model_validate(updated_user)


async def get_group_details(db: AsyncIOMotorDatabase, group_id: str, current_user: UserInDB) -> GroupPublic:
    """獲取單一群組的詳細資訊，並填入成員的公開資訊。"""
    group = await db.groups.find_one({"_id": ObjectId(group_id)})
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")

    # 安全檢查：確保當前使用者是該群組的成員之一
    user_id_list = [member["_id"] for member in group.get("members", [])]
    if ObjectId(current_user.id) not in user_id_list:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this group.")

    # 查詢所有成員的詳細資訊
    members_cursor = db.users.find({"_id": {"$in": user_id_list}})
    members_list = await members_cursor.to_list(length=None)

    # 將成員資料轉換為 UserInGroup 模型
    group["members"] = [UserInGroup.model_validate(mem) for mem in members_list]

    return GroupPublic.model_validate(group)


async def add_member_to_group(
    db: AsyncIOMotorDatabase, group_id: str, member_data: AddMemberRequest, current_user: UserInDB
) -> GroupPublic:
    """將一位新成員加入到指定的群組中。"""
    group = await db.groups.find_one({"_id": ObjectId(group_id)})
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")

    # 安全檢查：只有群組的擁有者 (owner) 才能新增成員
    if group["owner_id"] != ObjectId(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the group owner can add members.")

    # 尋找要被加入的使用者
    user_to_add = await db.users.find_one({"email": member_data.email})
    if not user_to_add:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User with email {member_data.email} not found."
        )

    # 檢查使用者是否已經是成員
    if user_to_add["_id"] in group["members"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a member of this group.")

    # 使用 $addToSet 操作符來新增成員，它可以自動處理重複問題
    await db.groups.update_one({"_id": ObjectId(group_id)}, {"$addToSet": {"members": user_to_add["_id"]}})

    # 回傳更新後的群組詳細資訊
    return await get_group_details(db, group_id, current_user)


async def remove_member_from_group(
    db: AsyncIOMotorDatabase, group_id: str, member_id: str, current_user: UserInDB
) -> GroupPublic:
    """從指定的群組中移除一位成員。"""
    group = await db.groups.find_one({"_id": ObjectId(group_id)})
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")

    # 安全檢查：只有群組的擁有者 (owner) 才能移除成員
    if group["owner_id"] != ObjectId(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the group owner can remove members.")

    member_id_to_remove = ObjectId(member_id)

    # 業務邏輯：擁有者不能移除自己
    if member_id_to_remove == group["owner_id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner cannot be removed from the group.")

    # 使用 $pull 操作符來移除成員
    await db.groups.update_one({"_id": ObjectId(group_id)}, {"$pull": {"members": member_id_to_remove}})

    # 回傳更新後的群組詳細資訊
    return await get_group_details(db, group_id, current_user)
