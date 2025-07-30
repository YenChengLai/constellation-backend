# services/expense_service/app/logic.py

from datetime import datetime, timezone
from typing import Literal

from bson import ObjectId
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from packages.shared_models.models import UserInDB

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
    """Creates a new transaction record for the current user."""
    category = await db.categories.find_one(
        {
            "$and": [
                {"_id": ObjectId(transaction_data.category_id)},
                {"$or": [{"user_id": ObjectId(current_user.id)}, {"user_id": None}]},
            ]
        }
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id {transaction_data.category_id} not found or not accessible.",
        )

    embedded_category = CategoryEmbedded.model_validate(category)
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


async def list_transactions(
    db: AsyncIOMotorDatabase, current_user: UserInDB, year: int, month: int
) -> list[TransactionPublic]:
    """Lists all transactions for the current user for a specific month and year."""
    start_of_month = datetime(year, month, 1, tzinfo=timezone.utc)
    start_of_next_month = start_of_month + relativedelta(months=1)
    query = {
        "user_id": ObjectId(current_user.id),
        "transaction_date": {"$gte": start_of_month, "$lt": start_of_next_month},
    }

    transactions_cursor = db.transactions.find(query).sort("transaction_date", -1)
    transactions = await transactions_cursor.to_list(length=1000)

    return [TransactionPublic.model_validate(tx) for tx in transactions]


async def update_transaction(
    db: AsyncIOMotorDatabase,
    transaction_id: str,
    update_data: UpdateTransactionRequest,
    current_user: UserInDB,
) -> TransactionPublic:
    """Updates a transaction for the current user."""
    transaction_to_update = await db.transactions.find_one(
        {"_id": ObjectId(transaction_id), "user_id": ObjectId(current_user.id)}
    )
    if not transaction_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")

    update_doc = update_data.model_dump(exclude_unset=True)
    if update_data.category_id:
        new_category_id_obj = ObjectId(update_data.category_id)
        category = await db.categories.find_one(
            {
                "$and": [
                    {"_id": new_category_id_obj},
                    {"$or": [{"user_id": ObjectId(current_user.id)}, {"user_id": None}]},
                ]
            }
        )
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id {update_data.category_id} not accessible.",
            )
        update_doc["category"] = CategoryEmbedded.model_validate(category).model_dump(by_alias=True)
        del update_doc["category_id"]

    if update_doc:
        update_doc["updated_at"] = datetime.now(timezone.utc)
    else:
        return TransactionPublic.model_validate(transaction_to_update)

    updated_transaction = await db.transactions.find_one_and_update(
        {"_id": ObjectId(transaction_id)}, {"$set": update_doc}, return_document=ReturnDocument.AFTER
    )
    if not updated_transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found after update.")

    return TransactionPublic.model_validate(updated_transaction)


async def delete_transaction(db: AsyncIOMotorDatabase, transaction_id: str, current_user: UserInDB):
    """Deletes a transaction for the current user."""
    result = await db.transactions.delete_one({"_id": ObjectId(transaction_id), "user_id": ObjectId(current_user.id)})
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
    """Creates a new category for the current user."""
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
    """Lists categories available to the user (theirs + defaults)."""
    query = {"$or": [{"user_id": ObjectId(current_user.id)}, {"user_id": None}]}
    if category_type:
        query["type"] = category_type

    categories_cursor = db.categories.find(query)
    categories = await categories_cursor.to_list(length=100)
    return [CategoryPublic.model_validate(cat) for cat in categories]


async def delete_category(db: AsyncIOMotorDatabase, category_id: str, current_user: UserInDB):
    """Deletes a user-defined category."""
    category_to_delete = await db.categories.find_one(
        {"_id": ObjectId(category_id), "user_id": ObjectId(current_user.id)}
    )
    if not category_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")

    transaction_using_category = await db.transactions.find_one(
        {"category._id": ObjectId(category_id), "user_id": ObjectId(current_user.id)}
    )
    if transaction_using_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category as it is currently in use by one or more transactions.",
        )

    await db.categories.delete_one({"_id": ObjectId(category_id)})
    return
