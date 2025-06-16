from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .auth import (
    ADMIN_EMAIL,
    approve_user,
    authenticate_user,
    create_access_token,
    create_pending_user,
    get_pending_users,
    initiate_password_reset,
    update_password,
    verify_token,
)
from .db import get_db
from .models import (
    BEARER,
    ForgotPasswordRequest,
    LoginRequest,
    PasswordUpdateRequest,
    PendingUser,
    SignupRequest,
    TokenResponse,
    UserApprovalRequest,
    UserResponse,
)


app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_admin(authorization: Annotated[str | None, Header()] = None, db=Depends(get_db)) -> UserResponse:
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        user = verify_token(token, db)
        if user.email != ADMIN_EMAIL:
            raise HTTPException(status_code=403, detail="Admin access required")
        print(f"User {user.email} is an admin")
        return user
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid credentials") from exc


@app.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db=Depends(get_db)) -> dict:
    print("Logging in user")
    user = authenticate_user(request.email, request.password, db)
    print(f"User {user.email} logged in successfully")
    access_token = create_access_token({"sub": user.email})
    return {"access_token": access_token, "token_type": BEARER}


@app.get("/verify-token")
def verify_token_endpoint(token: str, db=Depends(get_db)) -> UserResponse:
    return verify_token(token, db)


@app.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db=Depends(get_db)) -> dict:
    try:
        initiate_password_reset(request.email, db)
        return {"message": "A password reset link has been sent to your email."}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process request: {str(e)}") from e


@app.post("/signup")
async def signup(request: SignupRequest, db=Depends(get_db)) -> dict:
    try:
        create_pending_user(request.email, request.password, db)
        return {"message": "Your registration is pending approval. You’ll be notified once approved."}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process request: {e!r}") from e


@app.get("/pending-users")
async def list_pending_users(
    _: Annotated[UserResponse, Depends(require_admin)], db=Depends(get_db)
) -> list[PendingUser]:
    return get_pending_users(db)


@app.post("/approve-user")
def approve_user_endpoint(
    request: UserApprovalRequest, _: Annotated[UserResponse, Depends(require_admin)], db=Depends(get_db)
) -> dict:
    try:
        approve_user(request.userId, request.approve, db)
        action = "approved" if request.approve else "rejected"
        return {"message": f"User {action} successfully."}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process request: {e!r}") from e


@app.put("/user/password")
async def update_user_password(
    password_data: PasswordUpdateRequest, authorization: Annotated[str | None, Header()] = None, db=Depends(get_db)
) -> dict[str, str]:
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        user = verify_token(token, db)
        if not password_data.password:
            raise HTTPException(status_code=403, detail="Cannot update password for another user")
        update_password(password_data, user, db)
        return {"message": "Password updated successfully"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to update password: {str(exc)}") from exc


@app.get("/health")
def health_check() -> dict:
    return {"status": "Auth service is up"}
