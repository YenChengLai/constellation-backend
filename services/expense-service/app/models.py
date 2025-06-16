from typing import ClassVar

from bson import ObjectId
from pydantic import BaseModel, Field, validator


class ExpenseCreate(BaseModel):
    amount: float
    category: str
    date: str
    description: str | None = None
    type: str
    currency: str = "USD"


class Category(BaseModel):
    name: str


class Expense(BaseModel):
    id: str
    userId: str
    groupId: str | None
    amount: float
    category: str
    date: str
    description: str | None
    type: str
    currency: str
    epoch: int

    class Config:
        json_encoders: ClassVar[dict] = {ObjectId: str}


class UserProfile(BaseModel):
    userId: ObjectId = Field(...)
    name: str | None = None
    image: str | None = None
    currency: str = "USD"
    dateFormat: str = "MM/DD/YYYY"
    themeMode: str = "light"
    updatedAt: int | None = None

    @validator("userId", pre=True)
    @classmethod
    def validate_user_id(cls, value):
        if isinstance(value, ObjectId):
            return value
        if isinstance(value, str):
            try:
                return ObjectId(value)
            except Exception as e:
                raise ValueError(f"Invalid ObjectId string: {value}") from e
        raise ValueError("userId must be an ObjectId or a valid ObjectId string")

    class Config:
        arbitrary_types_allowed = True
        json_encoders: ClassVar[dict] = {ObjectId: str}


class UserProfileUpdate(BaseModel):
    name: str | None = None
    image: str | None = None
    currency: str | None = None
    dateFormat: str | None = None
    themeMode: str | None = None
