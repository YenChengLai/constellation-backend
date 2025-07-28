# services/expense_service/app/logic.py

from datetime import datetime, timezone
from typing import Literal

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from packages.shared_models.models import UserInDB

# 從本地和共享模組引入需要的模型
from .models import (
    CategoryCreate,
    CategoryEmbedded,
    CategoryPublic,
    CreateTransactionRequest,
    TransactionPublic,
    UpdateTransactionRequest,
)

# --- Transaction Logic ---


async def create_transaction(
    db: AsyncIOMotorDatabase, transaction_data: CreateTransactionRequest, current_user: UserInDB
) -> TransactionPublic:
    """
    Creates a new transaction record for the current user.
    """
    category = await db.categories.find_one(
        {
            "_id": ObjectId(transaction_data.category_id),
            "$or": [{"user_id": ObjectId(current_user.id)}, {"user_id": None}],
        }
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id {transaction_data.category_id} not found or not accessible by this user.",
        )

    # 建立內嵌的 category 物件 (擴展引用模式)
    embedded_category = CategoryEmbedded.model_validate(category)

    # 準備要寫入資料庫的交易文件
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

    # 插入資料庫
    result = await db.transactions.insert_one(transaction_doc)

    # 取得剛建立的完整文件並回傳
    created_transaction = await db.transactions.find_one({"_id": result.inserted_id})
    if not created_transaction:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create transaction.")

    return TransactionPublic.model_validate(created_transaction)


async def list_transactions(db: AsyncIOMotorDatabase, current_user: UserInDB) -> list[TransactionPublic]:
    """
    Lists all transactions for the current user, sorted by date.
    """
    transactions_cursor = db.transactions.find({"user_id": ObjectId(current_user.id)}).sort(
        "transaction_date", -1
    )  # -1 代表降序 (最新的在前面)

    transactions = await transactions_cursor.to_list(length=100)  # 暫時限制最多取 100 筆

    return [TransactionPublic.model_validate(tx) for tx in transactions]


# --- ✨ 新增：Update Transaction Logic ---
async def update_transaction(
    db: AsyncIOMotorDatabase,
    transaction_id: str,
    update_data: UpdateTransactionRequest,
    current_user: UserInDB,
) -> TransactionPublic:
    """Updates a transaction for the current user."""
    # 1. 安全檢查：確認這筆交易存在，並且屬於當前使用者
    transaction_to_update = await db.transactions.find_one(
        {"_id": ObjectId(transaction_id), "user_id": ObjectId(current_user.id)}
    )
    if not transaction_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")

    # 2. 準備要更新的資料
    update_doc = update_data.model_dump(exclude_unset=True)  # exclude_unset=True 只包含使用者實際傳入的欄位

    # 3. 如果使用者更新了分類，我們需要重新驗證並更新內嵌的 category 物件
    if "category_id" in update_doc and update_doc["category_id"]:
        new_category_id = update_doc["category_id"]
        category = await db.categories.find_one(
            {
                "$and": [
                    {"_id": ObjectId(new_category_id)},
                    {"$or": [{"user_id": ObjectId(current_user.id)}, {"user_id": None}]},
                ]
            }
        )
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id {new_category_id} not found or not accessible.",
            )

        update_doc["category"] = CategoryEmbedded.model_validate(category).model_dump(by_alias=True)
        del update_doc["category_id"]

    # 4. 加入更新時間戳
    if update_doc:  # 只有在有東西要更新時才更新時間戳
        update_doc["updated_at"] = datetime.now(timezone.utc)

    # 5. 執行更新並取回更新後的完整文件
    updated_transaction = await db.transactions.find_one_and_update(
        {"_id": ObjectId(transaction_id)},
        {"$set": update_doc},
        return_document=ReturnDocument.AFTER,  # 要求 MongoDB 回傳更新後的版本
    )

    if not updated_transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found after update.")

    return TransactionPublic.model_validate(updated_transaction)


# --- ✨ 新增：Delete Transaction Logic ---
async def delete_transaction(db: AsyncIOMotorDatabase, transaction_id: str, current_user: UserInDB):
    """Deletes a transaction for the current user."""
    # 執行一個原子操作：尋找並刪除符合條件的文件
    result = await db.transactions.delete_one({"_id": ObjectId(transaction_id), "user_id": ObjectId(current_user.id)})

    # 如果沒有任何文件被刪除，代表這筆交易不存在或不屬於該使用者
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found or you do not have permission to delete it.",
        )

    return


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
    """
    列出當前使用者可用的分類（包含使用者自訂及系統預設），可選擇性地按類型篩選。
    """
    query = {"$or": [{"user_id": ObjectId(current_user.id)}, {"user_id": None}]}

    # 如果有傳入類型篩選，則將其作為額外條件加入查詢
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
