"""
Auth routes: login, refresh, logout, MFA, change password, /me.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import get_db, User
from app.models.schemas import (
    LoginRequest, TokenPair, RefreshRequest, ChangePasswordRequest,
    MFASetupResponse, MFAVerifyRequest, UserResponse,
)
from app.services.auth_service import auth_service, AuthError
from app.utils.security import validate_password_strength
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await auth_service.authenticate(db, payload.username, payload.password)
    except AuthError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if user.is_mfa_enabled:
        if not payload.otp_code:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "MFA code required")
        if not await auth_service.verify_mfa_code(user, payload.otp_code):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid MFA code")
    tokens = await auth_service.issue_tokens(db, user)
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await auth_service.refresh(db, payload.refresh_token)
    except AuthError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e))


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await auth_service.logout(db, current_user.id)
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        phone=current_user.phone,
        role_name=current_user.role.name if current_user.role else "",
        is_active=current_user.is_active,
        is_mfa_enabled=current_user.is_mfa_enabled,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
    )


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await auth_service.setup_mfa(db, current_user)
    return MFASetupResponse(**data)


@router.post("/mfa/verify")
async def mfa_verify(
    payload: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await auth_service.verify_and_enable_mfa(db, current_user, payload.otp_code)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid OTP code")
    return {"detail": "MFA enabled successfully"}


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_strong, reason = validate_password_strength(payload.new_password)
    if not is_strong:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, reason)
    ok = await auth_service.change_password(
        db, current_user, payload.current_password, payload.new_password
    )
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password incorrect")
    return {"detail": "Password changed. Please log in again."}
