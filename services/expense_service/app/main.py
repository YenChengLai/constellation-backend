# services/expense_service/app/main.py

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

from fastapi import Depends, FastAPI, Query, status
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorDatabase

from packages.shared_models.models import UserInDB
from packages.shared_utils.auth import get_current_user
from packages.shared_utils.database import close_mongo_connection, connect_to_mongo, get_db

from .logic import (
    create_category,
    create_transaction,
    delete_category,
    delete_transaction,
    get_transaction_summary,
    list_categories,
    list_transactions,
    update_category,
    update_transaction,
)
from .models import (
    CategoryCreate,
    CategoryPublic,
    CreateTransactionRequest,
    TransactionPublic,
    TransactionSummaryResponse,
    UpdateCategoryRequest,
    UpdateTransactionRequest,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(title="Expense Service", lifespan=lifespan)

# CORS 設定
origins = ["http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "OK", "service": "Expense Service"}


# --- Transactions Endpoints ---


@app.post("/transactions", response_model=TransactionPublic, status_code=status.HTTP_201_CREATED, tags=["Transactions"])
async def add_new_transaction(
    transaction_data: CreateTransactionRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    """Create a new transaction for the authenticated user."""
    new_transaction = await create_transaction(db=db, transaction_data=transaction_data, current_user=current_user)
    return new_transaction


@app.get("/transactions", response_model=list[TransactionPublic], tags=["Transactions"])
async def get_transactions(
    group_id: str | None = Query(default=None),
    year: int | None = Query(default=None, description="Filter by year"),
    month: int | None = Query(default=None, description="Filter by month (1-12)"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    """Retrieve all transactions for the authenticated user for a given month and year."""
    # 如果前端沒有提供年月，我們在內部將其設為當前時間
    now = datetime.now(timezone.utc)
    query_year = year if year is not None else now.year
    query_month = month if month is not None else now.month

    transactions = await list_transactions(
        db=db, current_user=current_user, year=query_year, month=query_month, group_id=group_id
    )
    return transactions


@app.patch("/transactions/{transaction_id}", response_model=TransactionPublic, tags=["Transactions"])
async def update_existing_transaction(
    transaction_id: str,
    update_data: UpdateTransactionRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    """Update a specific transaction for the authenticated user."""
    updated_tx = await update_transaction(
        db=db, transaction_id=transaction_id, update_data=update_data, current_user=current_user
    )
    return updated_tx


@app.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Transactions"])
async def remove_transaction(
    transaction_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    """Delete a specific transaction for the authenticated user."""
    await delete_transaction(db=db, transaction_id=transaction_id, current_user=current_user)
    return


@app.get("/transactions/summary", response_model=TransactionSummaryResponse, tags=["Transactions"])
async def get_transactions_summary(
    group_id: str | None = Query(default=None),
    year: int | None = Query(default=None, description="Filter by year"),
    month: int | None = Query(default=None, description="Filter by month (1-12)"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Get a summary of income and expenses for the specified month and the previous month.
    """
    now = datetime.now(timezone.utc)
    query_year = year if year is not None else now.year
    query_month = month if month is not None else now.month

    summary = await get_transaction_summary(
        db=db, current_user=current_user, year=query_year, month=query_month, group_id=group_id
    )
    return summary


# --- Categories Endpoints ---


@app.post("/categories", response_model=CategoryPublic, status_code=status.HTTP_201_CREATED, tags=["Categories"])
async def add_new_category(
    category_data: CategoryCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    """Create a new category for the authenticated user."""
    new_category = await create_category(db=db, category_data=category_data, current_user=current_user)
    return new_category


@app.get("/categories", response_model=list[CategoryPublic], tags=["Categories"])
async def get_user_categories(
    category_type: Literal["expense", "income"] | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    """List all categories for the authenticated user, optionally filtered by type."""
    categories = await list_categories(db=db, current_user=current_user, category_type=category_type)
    return categories


@app.patch("/categories/{category_id}", response_model=CategoryPublic, tags=["Categories"])
async def update_user_category(
    category_id: str,
    update_data: UpdateCategoryRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    """Update a user-defined category."""
    updated_category = await update_category(
        db=db, category_id=category_id, update_data=update_data, current_user=current_user
    )
    return updated_category


@app.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Categories"])
async def remove_category(
    category_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    """Delete a category for the authenticated user."""
    await delete_category(db=db, category_id=category_id, current_user=current_user)
    return
