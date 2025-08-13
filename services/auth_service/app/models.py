from datetime import datetime
from typing import Annotated

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, computed_field

from packages.shared_models.models import UserPublic


# --- Custom Type Annotation ---
# This is a function that Pydantic will run BEFORE trying to validate the field.
# It checks if the value is an ObjectId and, if so, converts it to a string.
def object_id_as_str(v):
    if isinstance(v, ObjectId):
        return str(v)
    return v


PyObjectId = Annotated[str, BeforeValidator(object_id_as_str)]


# --- Request Models ---


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str | None = None
    last_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserUpdateRequest(BaseModel):
    """Model for user profile updates. All fields are optional."""

    first_name: str | None = Field(default=None, min_length=1, max_length=50)
    last_name: str | None = Field(default=None, min_length=1, max_length=50)


# --- Response Models ---


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class SessionInDB(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    refresh_token_hash: str
    expires_at: datetime
    created_at: datetime
    user_agent: str | None
    ip_address: str | None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


# --- Group Models ---
class GroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class UserInGroup(BaseModel):
    """A simplified user model for embedding in group responses."""

    id: PyObjectId = Field(alias="_id")
    email: EmailStr

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class AddMemberRequest(BaseModel):
    email: EmailStr


class GroupPublic(BaseModel):
    internal_id: PyObjectId = Field(alias="_id", exclude=True)
    name: str
    owner_id: PyObjectId
    members: list[UserInGroup]
    created_at: datetime

    @computed_field
    @property
    def id(self) -> str:
        return self.internal_id

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class GroupInDB(BaseModel):
    id: PyObjectId = Field(alias="_id")
    name: str
    owner_id: PyObjectId
    members: list[PyObjectId]
    created_at: datetime
