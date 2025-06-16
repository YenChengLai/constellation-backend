from typing import ClassVar

import requests
from bson import ObjectId
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field, validator


AUTH_SERVICE_URL = "http://127.0.0.1:8002/verify-token"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://127.0.0.1:8001/login")


class TokenData(BaseModel):
    email: str
    userId: ObjectId = Field(...)

    @validator("userId", pre=True)
    @classmethod
    def validate_user_id(cls, value: str) -> ObjectId:
        if isinstance(value, str):
            try:
                return ObjectId(value)
            except Exception:
                raise ValueError("Invalid ObjectId string")
        if not isinstance(value, ObjectId):
            raise ValueError("userId must be an ObjectId or valid ObjectId string")
        return value

    class Config:
        arbitrary_types_allowed = True
        json_encoders: ClassVar[dict] = {ObjectId: str}


def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    try:
        response = requests.get(AUTH_SERVICE_URL, params={"token": token}, timeout=5)
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        return TokenData(**response.json())
    except requests.RequestException as exc:
        raise HTTPException(status_code=401, detail="Could not validate token") from exc
