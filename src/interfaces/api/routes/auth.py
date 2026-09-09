"""Auth routes — register, login, me."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.auth.dependencies import get_current_user
from infrastructure.auth.jwt import create_access_token
from infrastructure.auth.password import hash_password, verify_password
from infrastructure.db.base import get_session
from infrastructure.db.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128, description="Mật khẩu tối thiểu 8 ký tự")
    name: str = Field("", max_length=100, description="Tên hiển thị")
    # role is ignored for public register — always 'user'; admin is seeded


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(3600, description="Seconds until expiry")
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    created_at: str | None = None
    last_login_at: str | None = None


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản mới",
)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    email_norm = body.email.lower().strip()
    # Check existing
    result = await session.execute(select(User).where(User.email == email_norm))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email đã được đăng ký")

    user = User(
        email=email_norm,
        hashed_password=hash_password(body.password),
        name=body.name.strip() or email_norm.split("@")[0],
        role="user",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)

    from shared.config import JWT_EXPIRE_MINUTES

    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=JWT_EXPIRE_MINUTES * 60,
        user=user.to_dict(),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Đăng nhập",
)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    email_norm = body.email.lower().strip()
    result = await session.execute(select(User).where(User.email == email_norm))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email hoặc mật khẩu không đúng")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa")

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await session.flush()

    from shared.config import JWT_EXPIRE_MINUTES

    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=JWT_EXPIRE_MINUTES * 60,
        user=user.to_dict(),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Thông tin user hiện tại",
)
async def me(current_user: User = Depends(get_current_user)):
    d = current_user.to_dict()
    return UserResponse(**d)


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="Danh sách users (admin only) — debug",
)
async def list_users(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    result = await session.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [UserResponse(**u.to_dict()) for u in users]
