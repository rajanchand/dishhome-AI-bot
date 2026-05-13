"""
Authentication service: login, MFA, refresh tokens, RBAC permission checks.
"""

from datetime import datetime, timedelta
from typing import Optional, Set
from uuid import UUID

from loguru import logger
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User, Role, Permission
from app.utils.security import (
    verify_password, hash_password, create_access_token, create_refresh_token,
    hash_refresh_token, verify_token, generate_totp_secret, get_totp_uri, verify_totp,
)
from config.settings import settings
from config.rbac import has_permission as rbac_has_permission


class AuthError(Exception):
    pass


class AuthService:
    async def authenticate(
        self, db: AsyncSession, username: str, password: str
    ) -> Optional[User]:
        stmt = (
            select(User)
            .options(selectinload(User.role).selectinload(Role.permissions))
            .where(or_(User.username == username, User.email == username.lower()))
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return None
        if not user.is_active:
            raise AuthError("Account is inactive")
        if user.is_locked:
            raise AuthError(f"Account locked until {user.locked_until.isoformat()}")
        if not verify_password(password, user.hashed_password):
            user.failed_login_count = (user.failed_login_count or 0) + 1
            if user.failed_login_count >= settings.max_failed_logins:
                user.locked_until = datetime.utcnow() + timedelta(
                    minutes=settings.lockout_duration_minutes
                )
                logger.warning(f"Account locked: {user.username}")
            await db.commit()
            return None
        user.failed_login_count = 0
        user.last_login_at = datetime.utcnow()
        return user

    async def issue_tokens(self, db: AsyncSession, user: User) -> dict:
        access_token = create_access_token({
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.name if user.role else "support_agent",
        })
        refresh_raw, refresh_hash = create_refresh_token(str(user.id))
        user.refresh_token_hash = refresh_hash
        await db.commit()
        return {
            "access_token": access_token,
            "refresh_token": refresh_raw,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_expire_minutes * 60,
            "user_id": str(user.id),
            "role": user.role.name if user.role else "support_agent",
            "requires_mfa": user.is_mfa_enabled,
        }

    async def refresh(self, db: AsyncSession, refresh_token: str) -> dict:
        try:
            payload = verify_token(refresh_token, expected_type="refresh")
        except Exception as e:
            raise AuthError(f"Invalid refresh token: {e}")
        user_id = payload.get("sub")
        if not user_id:
            raise AuthError("Refresh token missing subject")
        stmt = (
            select(User)
            .options(selectinload(User.role).selectinload(Role.permissions))
            .where(User.id == UUID(user_id))
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise AuthError("User not found or inactive")
        expected_hash = hash_refresh_token(refresh_token)
        if user.refresh_token_hash != expected_hash:
            raise AuthError("Refresh token revoked")
        return await self.issue_tokens(db, user)

    async def logout(self, db: AsyncSession, user_id: UUID) -> None:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.refresh_token_hash = None
            await db.commit()

    async def setup_mfa(self, db: AsyncSession, user: User) -> dict:
        secret = generate_totp_secret()
        user.mfa_secret = secret
        await db.commit()
        return {
            "secret": secret,
            "qr_code_uri": get_totp_uri(secret, user.email),
            "backup_codes": [],
        }

    async def verify_and_enable_mfa(self, db: AsyncSession, user: User, otp_code: str) -> bool:
        if not user.mfa_secret:
            return False
        if not verify_totp(user.mfa_secret, otp_code):
            return False
        user.is_mfa_enabled = True
        await db.commit()
        return True

    async def verify_mfa_code(self, user: User, otp_code: str) -> bool:
        if not user.is_mfa_enabled or not user.mfa_secret:
            return True
        return verify_totp(user.mfa_secret, otp_code)

    async def change_password(
        self, db: AsyncSession, user: User, current_password: str, new_password: str
    ) -> bool:
        if not verify_password(current_password, user.hashed_password):
            return False
        user.hashed_password = hash_password(new_password)
        user.refresh_token_hash = None  # force re-login
        await db.commit()
        return True

    async def get_user_permissions(self, user: User) -> Set[str]:
        if not user.role:
            return set()
        if user.role.name == "superadmin":
            return {"*:*"}
        return {f"{p.resource}:{p.action}" for p in user.role.permissions}

    async def check_permission(self, user: User, resource: str, action: str) -> bool:
        perms = await self.get_user_permissions(user)
        return rbac_has_permission(perms, resource, action)


auth_service = AuthService()
