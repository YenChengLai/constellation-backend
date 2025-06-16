import time
from typing import Annotated, Any

from bson import ObjectId
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo.database import Database

from .auth import TokenData, get_current_user
from .db import get_db
from .models import Category, Expense, ExpenseCreate, UserProfile, UserProfileUpdate


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/expense")
def create_expense(
    expense: ExpenseCreate,
    current_user: Annotated[TokenData, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_db)],
) -> Expense:
    expense_dict = expense.model_dump()
    expense_dict["userId"] = current_user.userId
    expense_dict["groupId"] = None
    expense_dict["epoch"] = int(time.time())
    result = db.expense.insert_one(expense_dict)
    expense_dict["id"] = str(result.inserted_id)
    expense_dict["userId"] = str(expense_dict["userId"])
    return Expense(**expense_dict)


@app.get("/expense")
def get_expenses(
    current_user: Annotated[TokenData, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_db)],
    date_gte: str | None = None,
    date_lte: str | None = None,
    category: str | None = None,
    type: str | None = None,
) -> list[Expense]:
    query: dict = {"userId": current_user.userId}
    if date_gte:
        query["date"] = query.get("date", {})
        query["date"].update({"$gte": date_gte})
    if date_lte:
        query["date"] = query.get("date", {})
        query["date"].update({"$lte": date_lte})
    if category:
        query["category"] = category
    if type:
        query["type"] = type
    expenses = db.expense.find(query)
    return [
        Expense(
            id=str(exp["_id"]),
            userId=str(exp["userId"]),
            groupId=exp.get("groupId"),
            amount=exp["amount"],
            category=exp["category"],
            date=exp["date"],
            description=exp.get("description"),
            type=exp["type"],
            currency=exp["currency"],
            epoch=exp["epoch"],
        )
        for exp in expenses
    ]


@app.put("/expense/{expense_id}")
def update_expense(
    expense_id: str,
    expense: ExpenseCreate,
    current_user: Annotated[TokenData, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_db)],
) -> Expense:
    expense_dict = expense.model_dump()
    expense_dict["userId"] = current_user.userId
    expense_dict["groupId"] = None
    expense_dict["epoch"] = int(time.time() * 1000)
    result = db.expense.update_one({"_id": ObjectId(expense_id), "userId": current_user.userId}, {"$set": expense_dict})
    if not result.modified_count:
        raise HTTPException(status_code=404, detail="Expense not found or not owned by user")
    updated_expense = db.expense.find_one({"_id": ObjectId(expense_id)}) or {}
    return Expense(
        id=str(updated_expense.get("_id")),
        userId=str(updated_expense["userId"]),
        groupId=updated_expense.get("groupId"),
        amount=float(updated_expense.get("amount", 0.0)),
        category=updated_expense.get("category", ""),
        date=updated_expense.get("date", ""),
        description=updated_expense.get("description"),
        type=updated_expense.get("type", ""),
        currency=updated_expense.get("currency", "USD"),
        epoch=int(updated_expense.get("epoch", int(time.time() * 1000))),
    )


@app.delete("/expense/{expense_id}")
def delete_expense(
    expense_id: str,
    current_user: Annotated[TokenData, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_db)],
) -> dict[str, str]:
    result = db.expense.delete_one({"_id": ObjectId(expense_id), "userId": current_user.userId})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Expense not found or not owned by user")
    return {"message": "Expense deleted successfully"}


@app.post("/categories")
def create_category(
    category: Category,
    db: Annotated[Database, Depends(get_db)],
    current_user: Annotated[TokenData, Depends(get_current_user)],
) -> Category:
    existing = db.category.find_one({"name": category.name, "userId": current_user.userId})
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists for this user")
    db.category.insert_one({"name": category.name, "userId": current_user.userId})
    return category


@app.get("/categories")
def list_categories(
    db: Annotated[Database, Depends(get_db)],
    current_user: Annotated[TokenData, Depends(get_current_user)],
    show_universal: bool = False,
) -> list[dict]:
    user_query = {"userId": current_user.userId}
    user_categories = db.category.find(user_query).to_list(None)
    universal_categories = []
    if show_universal:
        universal_query = {"userId": {"$exists": False}}
        universal_categories = db.category.find(universal_query).to_list(None)
    all_categories = user_categories + universal_categories
    return [
        {"name": cat["name"], "userId": str(cat.get("userId")) if cat.get("userId") else None} for cat in all_categories
    ]


@app.put("/categories/{name}")
def update_category(
    name: str,
    category: Category,
    db: Annotated[Database, Depends(get_db)],
    current_user: Annotated[TokenData, Depends(get_current_user)],
) -> Category:
    existing = db.category.find_one({"name": name, "userId": current_user.userId})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found or not owned by user")
    if db.category.find_one({"name": category.name, "userId": current_user.userId}):
        raise HTTPException(status_code=400, detail="New category name already exists")
    db.category.update_one({"name": name, "userId": current_user.userId}, {"$set": {"name": category.name}})
    db.expense.update_many({"category": name, "userId": current_user.userId}, {"$set": {"category": category.name}})
    return category


@app.delete("/categories/{name}")
def delete_category(
    name: str,
    db: Annotated[Database, Depends(get_db)],
    current_user: Annotated[TokenData, Depends(get_current_user)],
) -> dict[str, str]:
    existing = db.category.find_one({"name": name, "userId": current_user.userId})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found or not owned by user")
    if db.expense.find_one({"category": name, "userId": current_user.userId}):
        raise HTTPException(status_code=400, detail="Cannot delete category used in records")
    db.category.delete_one({"name": name, "userId": current_user.userId})
    return {"message": "Category deleted successfully"}


@app.post("/user/profile")
def create_user_profile(
    user_data: UserProfile,
    db: Annotated[Database, Depends(get_db)],
) -> dict[str, str]:
    existing = db.user_profile.find_one({"userId": user_data.userId})
    if existing:
        raise HTTPException(status_code=400, detail="User profile already exists")
    profile = user_data.model_dump()
    profile["userId"] = user_data.userId
    profile["updatedAt"] = int(time.time() * 1000)
    db.user_profile.insert_one(profile)
    return {"message": "User profile created successfully"}


@app.get("/user")
def get_user(
    current_user: Annotated[TokenData, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_db)],
) -> dict[Any, Any]:
    profile = db.user_profile.find_one({"userId": current_user.userId})
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    # Fetch email from auth-service using TokenData
    email = current_user.email
    profile_dict = {}
    profile_dict["email"] = email  # Add email to the response
    profile_dict["userId"] = str(profile["userId"])
    profile_dict["name"] = profile.get("name")
    profile_dict["image"] = profile.get("image")
    profile_dict["currency"] = profile.get("currency", "USD")
    profile_dict["dateFormat"] = profile.get("dateFormat", "MM/DD/YYYY")
    profile_dict["themeMode"] = profile.get("themeMode", "light")
    return profile_dict


@app.put("/user")
def update_user(
    update_data: UserProfileUpdate,
    current_user: Annotated[TokenData, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_db)],
) -> dict[str, str]:
    update_fields = update_data.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_fields["updatedAt"] = int(time.time() * 1000)
    result = db.user_profile.update_one({"userId": current_user.userId}, {"$set": update_fields})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User profile not found")
    return {"message": "User profile updated successfully"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "Expense service is up"}
