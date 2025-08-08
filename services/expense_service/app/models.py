# services/expense_service/app/models.py

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

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

    internal_id: PyObjectId = Field(alias="_id", exclude=True)
    user_id: PyObjectId | None = None  # 可選，若為 None 則為系統預設分類

    # 使用 computed_field 來確保 'id' 欄位永遠存在於 JSON 輸出中
    @computed_field
    @property
    def id(self) -> str:
        return str(self.internal_id)

    # 加上 model_config 以啟用 from_attributes 和 populate_by_name
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class UpdateCategoryRequest(BaseModel):
    """用於更新分類的請求模型，所有欄位皆可選"""

    name: str | None = Field(default=None, min_length=1, max_length=50)
    icon: str | None = None
    color: str | None = None


# --- Transaction Models ---


class CategoryEmbedded(BaseModel):
    """
    用於內嵌在 Transaction 中的分類資訊。
    這就是我們討論的「擴展引用」模式的實現。
    """

    id: PyObjectId = Field(alias="_id")
    icon: str | None = None
    name: str


class TransactionBase(BaseModel):
    """基本交易模型"""

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


class TransactionPublic(TransactionBase):
    # 使用一個臨時的內部欄位來接收來自資料庫的 _id
    internal_id: PyObjectId = Field(alias="_id", exclude=True)
    user_id: PyObjectId
    group_id: PyObjectId | None = None
    category: CategoryEmbedded
    created_at: datetime
    updated_at: datetime

    # 使用 computed_field 來確保 'id' 欄位永遠存在於 JSON 輸出中
    @computed_field
    @property
    def id(self) -> str:
        return str(self.internal_id)

    # 加上 model_config 以啟用 from_attributes 和 populate_by_name
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


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


class UpdateTransactionRequest(BaseModel):
    """
    Model for updating a transaction. All fields are optional.
    """

    type: Literal["expense", "income"] | None = None
    amount: float | None = Field(default=None, gt=0)
    transaction_date: datetime | None = None
    description: str | None = None
    category_id: PyObjectId | None = None
    group_id: PyObjectId | None = None
