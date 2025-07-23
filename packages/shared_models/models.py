# packages/shared_models/models.py

from datetime import datetime
from typing import Annotated

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, computed_field


# --- Custom Type Annotation ---
def object_id_as_str(v):
    if isinstance(v, ObjectId):
        return str(v)
    return v


PyObjectId = Annotated[str, BeforeValidator(object_id_as_str)]


# ✨✨✨ UserInDB Model now lives here ✨✨✨
class UserInDB(BaseModel):
    """
    Represents a full user document as stored in the database,
    including the hashed password.
    """

    id: PyObjectId = Field(alias="_id")
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    hashed_password: str
    verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


# ... any other shared models like UserPublic if you moved it ...
