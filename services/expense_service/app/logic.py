# services/expense_service/app/logic.py

import asyncio
from datetime import datetime, timezone
from typing import Literal

from bson import ObjectId
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from packages.shared_models.models import UserInDB

from .models import (
    AccountCreate,
    AccountInfoEmbedded,
    AccountPublic,
    CategoryCreate,
    CategoryEmbedded,
    CategoryPublic,
    CreateTransactionRequest,
    TransactionPublic,
    TransactionSummaryData,
    TransactionSummaryResponse,
    UpdateAccountRequest,
    UpdateCategoryRequest,
    UpdateTransactionRequest,
)

# --- Account Logic ---


async def create_account(
    db: AsyncIOMotorDatabase, account_data: AccountCreate, current_user: UserInDB
) -> AccountPublic:
    """Creates a new account for the current user or group."""
    account_doc = account_data.model_dump()

    # 設定擁有者
    if account_data.group_id:
        # TODO: Add validation to ensure user is a member of the group
        account_doc["group_id"] = ObjectId(account_data.group_id)
        account_doc["user_id"] = None  # Group accounts are not tied to a single user
    else:
        account_doc["user_id"] = ObjectId(current_user.id)
        account_doc["group_id"] = None

    # 關鍵：將初始餘額設定為當前餘額
    account_doc["balance"] = account_doc["initial_balance"]
    account_doc["is_archived"] = False

    result = await db.accounts.insert_one(account_doc)
    created_account = await db.accounts.find_one({"_id": result.inserted_id})

    return AccountPublic.model_validate(created_account)


async def list_accounts(db: AsyncIOMotorDatabase, current_user: UserInDB) -> list[AccountPublic]:
    """Lists all active accounts for the current user (personal and group)."""
    # TODO: Fetch all groups the user is a member of
    user_groups = []  # Placeholder

    query = {"$or": [{"user_id": ObjectId(current_user.id)}, {"group_id": {"$in": user_groups}}], "is_archived": False}

    accounts_cursor = db.accounts.find(query)
    accounts = await accounts_cursor.to_list(length=None)
    return [AccountPublic.model_validate(acc) for acc in accounts]


async def update_account(
    db: AsyncIOMotorDatabase, account_id: str, update_data: UpdateAccountRequest, current_user: UserInDB
) -> AccountPublic:
    """Updates an account's name or archived status."""
    account_id_obj = ObjectId(account_id)

    # 安全檢查：確保帳戶存在且屬於當前使用者
    account_to_update = await db.accounts.find_one({"_id": account_id_obj, "user_id": ObjectId(current_user.id)})
    if not account_to_update:
        # TODO: Handle group accounts
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found or permission denied.")

    update_doc = update_data.model_dump(exclude_unset=True)

    if not update_doc:
        return AccountPublic.model_validate(account_to_update)

    updated_account = await db.accounts.find_one_and_update(
        {"_id": account_id_obj}, {"$set": update_doc}, return_document=ReturnDocument.AFTER
    )

    return AccountPublic.model_validate(updated_account)


async def archive_account(db: AsyncIOMotorDatabase, account_id: str, current_user: UserInDB):
    """Archives an account by setting is_archived to True."""
    account_id_obj = ObjectId(account_id)

    account_to_archive = await db.accounts.find_one({"_id": account_id_obj, "user_id": ObjectId(current_user.id)})
    if not account_to_archive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found or permission denied.")

    # 業務邏輯：只有餘額為 0 的帳戶才能被封存
    if account_to_archive.get("balance", 0) != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot archive an account with a non-zero balance. Please transfer the remaining balance first.",
        )

    await db.accounts.update_one({"_id": account_id_obj}, {"$set": {"is_archived": True}})
    return


async def update_balance(
    db: AsyncIOMotorDatabase, account_id: ObjectId, amount: float, operation: Literal["add", "subtract"]
):
    """
    Atomically updates the balance of a specified account.
    This is a critical helper function.
    """
    modifier = amount if operation == "add" else -amount
    await db.accounts.update_one({"_id": account_id}, {"$inc": {"balance": modifier}})


# --- Transaction Logic ---


async def create_transaction(
    db: AsyncIOMotorDatabase, transaction_data: CreateTransactionRequest, current_user: UserInDB
) -> TransactionPublic:
    """Creates a new transaction and updates the account balance."""
    category = await db.categories.find_one(
        {
            "$and": [
                {"_id": ObjectId(transaction_data.category_id)},
                {"$or": [{"user_id": ObjectId(current_user._id)}, {"user_id": None}]},
            ]
        }
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id {transaction_data.category_id} not found or not accessible.",
        )

    account_id_obj = ObjectId(transaction_data.account_id)
    account = await db.accounts.find_one({"_id": account_id_obj, "is_archived": False})
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found or has been archived.")

    embedded_category = CategoryEmbedded.model_validate(category)
    now = datetime.now(timezone.utc)
    transaction_doc = transaction_data.model_dump()
    if transaction_doc.get("group_id"):
        transaction_doc["group_id"] = ObjectId(transaction_doc["group_id"])
    if transaction_doc.get("payer_id"):
        transaction_doc["payer_id"] = ObjectId(transaction_doc["payer_id"])
    if transaction_doc.get("account_id"):
        transaction_doc["account_id"] = ObjectId(transaction_doc["account_id"])

    transaction_doc.update(
        {
            "user_id": ObjectId(current_user._id),
            "category": embedded_category.model_dump(by_alias=True),
            "created_at": now,
            "updated_at": now,
        }
    )

    transaction_doc["category"]["_id"] = ObjectId(transaction_doc["category"]["_id"])

    if "payer_id" not in transaction_doc or transaction_doc["payer_id"] is None:
        # 如果前端沒有傳 payer_id (例如在個人帳本模式下)，
        # 我們預設支付者就是當前使用者
        transaction_doc["payer_id"] = ObjectId(current_user._id)

    # 驗證 payer_id 的權限
    # 如果是群組交易，要確認 payer 是群組成員
    if transaction_doc.get("group_id"):
        group = await db.groups.find_one(
            {
                "_id": transaction_doc["group_id"],
                "members": transaction_doc["payer_id"],  # 檢查 payer 是否在成員列表
            }
        )
        if not group:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Payer is not a member of this group.")
    else:
        # 如果是個人交易，payer 必須是自己
        if transaction_doc["payer_id"] != ObjectId(current_user._id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Payer must be the current user for personal transactions.",
            )

    if "category_id" in transaction_doc:
        del transaction_doc["category_id"]

    result = await db.transactions.insert_one(transaction_doc)
    operation = "income" if transaction_data.type == "income" else "subtract"
    await update_balance(db, account_id_obj, transaction_data.amount, operation)

    created_transaction = await db.transactions.find_one({"_id": result.inserted_id})
    if not created_transaction:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create transaction.")

    del created_transaction["account_id"]  # 移除 account_id 欄位

    return TransactionPublic.model_validate(created_transaction)


async def list_transactions(
    db: AsyncIOMotorDatabase, current_user: UserInDB, year: int, month: int, group_id: str | None
) -> list[TransactionPublic]:
    """Lists all transactions for the current user for a specific month and year."""
    start_of_month = datetime(year, month, 1, tzinfo=timezone.utc)
    start_of_next_month = start_of_month + relativedelta(months=1)
    match_criteria = {
        "user_id": ObjectId(current_user._id),
        "transaction_date": {"$gte": start_of_month, "$lt": start_of_next_month},
    }

    if group_id:
        group = await db.groups.find_one({"_id": ObjectId(group_id), "members": ObjectId(current_user._id)})
        if not group:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not in this group.")
        match_criteria["group_id"] = ObjectId(group_id)
    else:
        match_criteria["user_id"] = ObjectId(current_user._id)
        match_criteria["group_id"] = None

    pipeline = [
        {"$match": match_criteria},
        {"$sort": {"transaction_date": -1}},
        {"$lookup": {"from": "accounts", "localField": "account_id", "foreignField": "_id", "as": "account_details"}},
        {"$unwind": {"path": "$account_details", "preserveNullAndEmptyArrays": True}},
        {"$addFields": {"account": "$account_details"}},
    ]

    transactions_cursor = db.transactions.aggregate(pipeline)
    transactions = await transactions_cursor.to_list(length=1000)
    for tx in transactions:
        if tx.get("account_id"):
            del tx["account_id"]
    return [TransactionPublic.model_validate(tx) for tx in transactions]


async def update_transaction(
    db: AsyncIOMotorDatabase,
    transaction_id: str,
    update_data: UpdateTransactionRequest,
    current_user: UserInDB,
) -> TransactionPublic:
    """Updates a transaction and correctly adjusts account balances."""
    transaction_id_obj = ObjectId(transaction_id)

    # 1. 取得交易「更新前」的原始狀態
    original_transaction = await db.transactions.find_one(
        {"_id": transaction_id_obj, "user_id": ObjectId(current_user.id)}
    )
    if not original_transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")

    update_doc = update_data.model_dump(exclude_unset=True)

    if "category_id" in update_doc and update_doc["category_id"]:
        new_category_id_obj = ObjectId(update_doc["category_id"])
        category = await db.categories.find_one(
            {
                "$and": [
                    {"_id": new_category_id_obj},
                    {"$or": [{"user_id": ObjectId(current_user.id)}, {"user_id": None}]},
                ]
            },
            {"icon": 1, "name": 1, "_id": 1},
        )
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id {update_data.category_id} not accessible.",
            )
        update_doc["category"] = category
        del update_doc["category_id"]

    if not update_doc:
        return TransactionPublic.model_validate(original_transaction, from_attributes=True)

    update_doc["updated_at"] = datetime.now(timezone.utc)
    if update_doc.get("account_id"):
        update_doc["account_id"] = ObjectId(update_doc["account_id"])

    # 2. 執行更新
    updated_transaction = await db.transactions.find_one_and_update(
        {"_id": transaction_id_obj}, {"$set": update_doc}, return_document=ReturnDocument.AFTER
    )
    if not updated_transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found after update.")

    # 3. 進行餘額調整
    original_account_id = original_transaction.get("account_id")
    if original_account_id:
        # a. 先將原始交易的影響「復原」
        original_amount = original_transaction["amount"]
        original_type = original_transaction["type"]
        reverse_op = "subtract" if original_type == "income" else "add"
        await update_balance(db, original_account_id, original_amount, reverse_op)

    new_account_id = updated_transaction.get("account_id")
    if new_account_id:
        # b. 再將新交易的影響「應用」上去
        new_amount = updated_transaction["amount"]
        new_type = updated_transaction["type"]
        apply_op = "add" if new_type == "income" else "subtract"
        await update_balance(db, new_account_id, new_amount, apply_op)

    del updated_transaction["account_id"]  # 移除 account_id 欄位

    return TransactionPublic.model_validate(updated_transaction)


async def get_transaction_summary(
    db: AsyncIOMotorDatabase,
    current_user: UserInDB,
    year: int,
    month: int,
    group_id: str | None,
) -> TransactionSummaryResponse:
    """
    Calculates the income and expense summary for a given month and the previous month
    using the MongoDB Aggregation Framework.
    """
    # 計算當月和上個月的日期範圍
    current_month_start = datetime(year, month, 1, tzinfo=timezone.utc)
    previous_month_start = current_month_start - relativedelta(months=1)
    next_month_start = current_month_start + relativedelta(months=1)

    # 定義一個可重用的 aggregation pipeline 函式
    async def _calculate_summary(start_date, end_date):
        match_criteria = {"transaction_date": {"$gte": start_date, "$lt": end_date}}
        if group_id:
            match_criteria["group_id"] = ObjectId(group_id)
        else:
            match_criteria["user_id"] = ObjectId(current_user._id)
            match_criteria["group_id"] = None

        pipeline = [
            {"$match": match_criteria},
            {
                "$group": {
                    "_id": "$type",  # 按照 'income' 或 'expense' 分組
                    "total_amount": {"$sum": "$amount"},  # 將同類型的金額加總
                }
            },
        ]

        summary_data = {"income": 0.0, "expense": 0.0}
        results = await db.transactions.aggregate(pipeline).to_list(length=None)

        for result in results:
            if result["_id"] == "income":
                summary_data["income"] = result["total_amount"]
            elif result["_id"] == "expense":
                summary_data["expense"] = result["total_amount"]

        return TransactionSummaryData(**summary_data)

    # 平行執行當月和上個月的計算
    current_month_summary, previous_month_summary = await asyncio.gather(
        _calculate_summary(current_month_start, next_month_start),
        _calculate_summary(previous_month_start, current_month_start),
    )

    return TransactionSummaryResponse(current_month=current_month_summary, previous_month=previous_month_summary)


async def delete_transaction(db: AsyncIOMotorDatabase, transaction_id: str, current_user: UserInDB):
    """Deletes a transaction and reverses its effect on the account balance."""
    transaction_id_obj = ObjectId(transaction_id)

    # 1. 在刪除前，先找到這筆交易的資料
    transaction_to_delete = await db.transactions.find_one(
        {"_id": transaction_id_obj, "user_id": ObjectId(current_user.id)}
    )

    if not transaction_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found or you do not have permission to delete it.",
        )

    account_id = transaction_to_delete.get("account_id")

    if account_id:
        # 2. 根據交易資料，先將帳戶餘額「復原」
        amount = transaction_to_delete["amount"]
        op_type = transaction_to_delete["type"]
        account_id = transaction_to_delete["account_id"]

        reverse_op = "subtract" if op_type == "income" else "add"
        await update_balance(db, account_id, amount, reverse_op)

    # 3. 餘額復原(或跳過)後，再安全地刪除這筆交易
    await db.transactions.delete_one({"_id": transaction_id_obj})
    return


# --- Category Logic ---


async def create_category(
    db: AsyncIOMotorDatabase, category_data: CategoryCreate, current_user: UserInDB
) -> CategoryPublic:
    """Creates a new category for the current user."""
    existing_category = await db.categories.find_one(
        {"name": category_data.name, "type": category_data.type, "user_id": ObjectId(current_user._id)}
    )
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category '{category_data.name}' of type '{category_data.type}' already exists.",
        )

    category_doc = category_data.model_dump()
    category_doc["user_id"] = ObjectId(current_user._id)
    result = await db.categories.insert_one(category_doc)
    created_category = await db.categories.find_one({"_id": result.inserted_id})
    if not created_category:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create category.")

    return CategoryPublic.model_validate(created_category)


async def list_categories(
    db: AsyncIOMotorDatabase, current_user: UserInDB, category_type: Literal["expense", "income"] | None
) -> list[CategoryPublic]:
    """Lists categories available to the user (theirs + defaults)."""
    query = {"$or": [{"user_id": ObjectId(current_user._id)}, {"user_id": None}]}
    if category_type:
        query["type"] = category_type

    categories_cursor = db.categories.find(query)
    categories = await categories_cursor.to_list(length=100)
    return [CategoryPublic.model_validate(cat) for cat in categories]


async def update_category(
    db: AsyncIOMotorDatabase, category_id: str, update_data: UpdateCategoryRequest, current_user: UserInDB
) -> CategoryPublic:
    """更新一個使用者自訂的分類。"""
    # 安全檢查：確保分類存在，且屬於當前使用者 (不允許修改預設分類)
    category_to_update = await db.categories.find_one(
        {"_id": ObjectId(category_id), "user_id": ObjectId(current_user._id)}
    )
    if not category_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found or permission denied.")

    update_doc = update_data.model_dump(exclude_unset=True)

    if not update_doc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update.")

    updated_category = await db.categories.find_one_and_update(
        {"_id": ObjectId(category_id)}, {"$set": update_doc}, return_document=ReturnDocument.AFTER
    )

    # TODO: 未來可以考慮加入一個背景任務，去同步更新所有 transaction 中內嵌的 category name

    return CategoryPublic.model_validate(updated_category)


async def delete_category(db: AsyncIOMotorDatabase, category_id: str, current_user: UserInDB):
    """Deletes a user-defined category."""
    category_to_delete = await db.categories.find_one(
        {"_id": ObjectId(category_id), "user_id": ObjectId(current_user._id)}
    )
    if not category_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")

    transaction_using_category = await db.transactions.find_one(
        {"category._id": ObjectId(category_id), "user_id": ObjectId(current_user._id)}
    )
    if transaction_using_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category as it is currently in use by one or more transactions.",
        )

    await db.categories.delete_one({"_id": ObjectId(category_id)})
    return
