"""FastAPI dependencies: get_current_user, require_permission, get_db."""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User, Role, get_db
from app.utils.security import verify_token
from app.services.auth_service import auth_service
from config.settings import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not token:
        if settings.app_env == "development":
            # Return a mock SuperAdmin user for local development if no token provided
            stmt = select(User).options(selectinload(User.role).selectinload(Role.permissions)).limit(1)
            result = await db.execute(stmt)
            mock_user = result.scalar_one_or_none()
            if mock_user:
                return mock_user
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        # verify_token handles both local and Supabase secrets
        payload = verify_token(token, expected_type="access")
    except Exception as e:
        # If verify_token failed, it might be a Supabase token which doesn't have "type: access"
        try:
            from jose import jwt
            payload = jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"], options={"verify_aud": False})
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {e}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token missing user identifier (sub)")
    
    # In Supabase integration, we map the JWT 'sub' to our User.id
    stmt = (
        select(User)
        .options(selectinload(User.role).selectinload(Role.permissions))
        .where(User.id == UUID(user_id))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found in application database")
        
    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User account is inactive")
        
    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not token:
        return None
    try:
        return await get_current_user(token=token, db=db)
    except HTTPException:
        return None


def require_permission(resource: str, action: str):
    """Dependency factory: enforces RBAC on a route."""
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        allowed = await auth_service.check_permission(current_user, resource, action)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: requires {resource}:{action}",
            )
        return current_user
    return _check


def require_role(*role_names: str):
    """Dependency factory: enforces specific role membership."""
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.role or current_user.role.name not in role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(role_names)}",
            )
        return current_user
    return _check
