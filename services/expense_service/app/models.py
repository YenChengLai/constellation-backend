# services/expense_service/app/models.py

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

# 假設我們的共享 PyObjectId 位於 packages/shared_models/models.py
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
    user_id: PyObjectId


# --- Transaction Models ---


class CategoryEmbedded(BaseModel):
    """
    用於內嵌在 Transaction 中的分類資訊。
    這就是我們討論的「擴展引用」模式的實現。
    """

    id: PyObjectId = Field(alias="_id")
    name: str


class TransactionBase(BaseModel):
    """基本交易模型"""

    type: Literal["expense", "income"]
    amount: Decimal = Field(..., gt=0, description="Amount must be positive")
    transaction_date: datetime = Field(default_factory=datetime.now)
    description: str | None = None
    currency: str = "TWD"  # 預設貨幣


class CreateTransactionRequest(TransactionBase):
    """用於建立新交易的請求模型"""

    category_id: PyObjectId
    group_id: PyObjectId | None = None  # 可選，若為 None 則為個人帳


class TransactionPublic(TransactionBase):
    """用於 API 回應的公開交易模型"""

    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    group_id: PyObjectId | None = None
    category: CategoryEmbedded  # 回應中包含完整的內嵌分類資訊
    created_at: datetime
    updated_at: datetime


class TransactionInDB(TransactionBase):
    """儲存在資料庫中的完整交易模型"""

    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    group_id: PyObjectId | None = None
    category: CategoryEmbedded
    created_at: datetime
    updated_at: datetime
