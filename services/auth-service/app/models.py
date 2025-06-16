from datetime import datetime

from pydantic import BaseModel, EmailStr


BEARER = "bearer"


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = BEARER


class UserResponse(BaseModel):
    email: str
    userId: str
    role: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    userId: str
    resetToken: str
    expiresAt: datetime


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class PendingUser(BaseModel):
    userId: str
    email: str
    hashedPassword: str
    createdAt: datetime


class UserApprovalRequest(BaseModel):
    userId: str
    approve: bool


class PasswordUpdateRequest(BaseModel):
    password: str


class PasswordUpdateResponse(BaseModel):
    message: str
