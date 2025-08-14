# services/expense_service/app/models.py

from datetime import datetime
from typing import Literal

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator

from packages.shared_models.models import PyObjectId

# --- Category Models ---


class CategoryBase(BaseModel):
    """基本分類模型，包含所有共享的欄位"""

    name: str = Field(..., min_length=1, max_length=50)
    type: Literal["expense", "income"]
    icon: str | None = None
    color: str | None = None


class CategoryCreate(CategoryBase):
    """用於建立新分類的請求模型"""

    pass


class CategoryPublic(CategoryBase):
    """用於 API 回應的模型，包含 ID"""

    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId | None = None
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @property
    def _id(self) -> PyObjectId:
        return self.id


class UpdateCategoryRequest(BaseModel):
    """用於更新分類的請求模型，所有欄位皆可選"""

    name: str | None = Field(default=None, min_length=1, max_length=50)
    icon: str | None = None
    color: str | None = None


# --- Transaction Models ---


class CategoryEmbedded(BaseModel):
    id: PyObjectId = Field(alias="_id")
    name: str
    icon: str | None = None
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @property
    def _id(self) -> PyObjectId:
        return self.id


class TransactionBase(BaseModel):
    type: Literal["expense", "income"]
    amount: float = Field(..., gt=0, description="Amount must be positive")
    transaction_date: datetime = Field(default_factory=datetime.now)
    description: str | None = None
    currency: str = "TWD"  # 預設貨幣
    payer_id: PyObjectId | None = None


class CreateTransactionRequest(TransactionBase):
    """用於建立新交易的請求模型"""

    category_id: PyObjectId
    group_id: PyObjectId | None = None  # 可選，若為 None 則為個人帳

    @field_validator("category_id", "group_id", "payer_id")
    @classmethod
    def must_be_valid_object_id(cls, v: str | None) -> str | None:
        if v is not None and not ObjectId.is_valid(v):
            raise ValueError(f"'{v}' is not a valid ObjectId")
        return v


class TransactionPublic(TransactionBase):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    group_id: PyObjectId | None = None
    category: CategoryEmbedded
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @property
    def _id(self) -> PyObjectId:
        return self.id


class TransactionSummaryData(BaseModel):
    """代表一個月份的總收入和總支出"""

    income: float = 0.0
    expense: float = 0.0


class TransactionSummaryResponse(BaseModel):
    """GET /transactions/summary 的回應模型"""

    current_month: TransactionSummaryData
    previous_month: TransactionSummaryData


class TransactionInDB(TransactionBase):
    """儲存在資料庫中的完整交易模型"""

    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    group_id: PyObjectId | None = None
    category: CategoryEmbedded
    created_at: datetime
    updated_at: datetime

    @property
    def _id(self) -> PyObjectId:
        return self.id


class UpdateTransactionRequest(BaseModel):
    type: Literal["expense", "income"] | None = None
    amount: float | None = Field(default=None, gt=0)
    transaction_date: datetime | None = None
    description: str | None = None
    category_id: str | None = None
    group_id: str | None = None

    @field_validator("category_id", "group_id")
    @classmethod
    def must_be_valid_object_id(cls, v: str | None) -> str | None:
        if v is not None and not ObjectId.is_valid(v):
            raise ValueError(f"'{v}' is not a valid ObjectId")
        return v
