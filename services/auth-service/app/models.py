# File: services/auth-service/app/models.py
# Description: Updated Pydantic models with custom type annotation for ObjectId.

from pydantic import BaseModel, EmailStr, Field, BeforeValidator
from datetime import datetime
from typing import Annotated
from bson import ObjectId

# --- Custom Type Annotation ---
# This is a function that Pydantic will run BEFORE trying to validate the field.
# It checks if the value is an ObjectId and, if so, converts it to a string.
def object_id_as_str(v):
    if isinstance(v, ObjectId):
        return str(v)
    return v

# We create a new type alias using Annotated.
# Any field with this type will automatically use our conversion function.
PyObjectId = Annotated[str, BeforeValidator(object_id_as_str)]


# --- Request Models ---

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


# --- Response Models ---

class UserPublic(BaseModel):
    # Apply our new custom type to the user_id field.
    user_id: PyObjectId = Field(alias="_id")
    email: EmailStr
    verified: bool
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True