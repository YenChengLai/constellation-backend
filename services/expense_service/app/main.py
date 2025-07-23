# services/expense_service/app/main.py

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorDatabase

from packages.shared_models.models import PyObjectId, UserInDB
from packages.shared_utils.auth import get_current_user
from packages.shared_utils.database import close_mongo_connection, connect_to_mongo, get_db

from .logic import create_category, create_transaction, delete_category, list_categories
from .models import CategoryCreate, CategoryPublic, CreateTransactionRequest, TransactionPublic


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


@app.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Categories"])
async def remove_category(
    category_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    """Delete a category for the authenticated user."""
    await delete_category(db=db, category_id=category_id, current_user=current_user)
    return
