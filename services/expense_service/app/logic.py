# services/expense_service/app/logic.py

from datetime import datetime, timezone
from typing import Literal

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from packages.shared_models.models import UserInDB

# 從本地和共享模組引入需要的模型
from .models import CategoryCreate, CategoryEmbedded, CategoryPublic, CreateTransactionRequest, TransactionPublic

# --- Transaction Logic ---


async def create_transaction(
    db: AsyncIOMotorDatabase, transaction_data: CreateTransactionRequest, current_user: UserInDB
) -> TransactionPublic:
    # ... (我們之前寫的 create_transaction 邏輯保持不變)
    category = await db.categories.find_one(
        {"_id": ObjectId(transaction_data.category_id), "user_id": ObjectId(current_user.id)}
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id {transaction_data.category_id} not found for this user.",
        )

    embedded_category = CategoryEmbedded(id=category["_id"], name=category["name"])
    now = datetime.now(timezone.utc)
    transaction_doc = transaction_data.model_dump()
    transaction_doc.update(
        {
            "user_id": ObjectId(current_user.id),
            "category": embedded_category.model_dump(by_alias=True),
            "created_at": now,
            "updated_at": now,
        }
    )
    del transaction_doc["category_id"]

    result = await db.transactions.insert_one(transaction_doc)
    created_transaction = await db.transactions.find_one({"_id": result.inserted_id})
    if not created_transaction:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create transaction.")

    return TransactionPublic.model_validate(created_transaction)


# --- Category Logic ---


async def create_category(
    db: AsyncIOMotorDatabase, category_data: CategoryCreate, current_user: UserInDB
) -> CategoryPublic:
    """為當前使用者建立一個新的分類。"""
    # 檢查同名同類型的分類是否已存在，防止重複
    existing_category = await db.categories.find_one(
        {"name": category_data.name, "type": category_data.type, "user_id": ObjectId(current_user.id)}
    )
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category '{category_data.name}' of type '{category_data.type}' already exists.",
        )

    category_doc = category_data.model_dump()
    category_doc["user_id"] = ObjectId(current_user.id)

    result = await db.categories.insert_one(category_doc)
    created_category = await db.categories.find_one({"_id": result.inserted_id})

    if not created_category:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create category.")

    return CategoryPublic.model_validate(created_category)


async def list_categories(
    db: AsyncIOMotorDatabase, current_user: UserInDB, category_type: Literal["expense", "income"] | None
) -> list[CategoryPublic]:
    """列出當前使用者可用的分類，可選擇性地按類型篩選。"""
    query = {"user_id": ObjectId(current_user.id)}
    if category_type:
        query["type"] = category_type

    categories_cursor = db.categories.find(query)
    categories = await categories_cursor.to_list(length=100)
    return [CategoryPublic.model_validate(cat) for cat in categories]


async def delete_category(db: AsyncIOMotorDatabase, category_id: str, current_user: UserInDB):
    """刪除一個使用者自訂的分類。"""
    # 1. 檢查這個分類是否存在，並且屬於當前使用者
    category_to_delete = await db.categories.find_one(
        {"_id": ObjectId(category_id), "user_id": ObjectId(current_user.id)}
    )
    if not category_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")

    # 2. 安全檢查：檢查是否有任何交易正在使用這個分類
    transaction_using_category = await db.transactions.find_one(
        {"category.id": ObjectId(category_id), "user_id": ObjectId(current_user.id)}
    )
    if transaction_using_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category as it is currently in use by one or more transactions.",
        )

    # 3. 如果檢查通過，則刪除
    await db.categories.delete_one({"_id": ObjectId(category_id)})
    return
