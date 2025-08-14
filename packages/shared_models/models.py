from datetime import datetime
from typing import Annotated

from bson import ObjectId
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    PlainSerializer,
    PlainValidator,
    WithJsonSchema,
)


# (PyObjectId 型別定義不變)
def validate_object_id(v: any) -> ObjectId:
    if isinstance(v, ObjectId):
        return v
    if ObjectId.is_valid(v):
        return ObjectId(v)
    raise ValueError("Invalid ObjectId")


PyObjectId = Annotated[
    ObjectId,
    PlainValidator(validate_object_id),
    PlainSerializer(lambda x: str(x), return_type=str),
    WithJsonSchema({"type": "string", "example": "66a5e9d2a3b4c5d6e7f8a9b0"}),
]


# --- User Models ---
class UserBase(BaseModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    verified: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UserInDB(UserBase):
    id: PyObjectId = Field(alias="_id")
    hashed_password: str

    @property
    def _id(self) -> PyObjectId:
        return self.id


class UserPublic(UserBase):
    id: PyObjectId = Field(alias="_id")

    @property
    def _id(self) -> PyObjectId:
        return self.id
