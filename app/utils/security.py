"""
Security primitives: password hashing, JWT, TOTP, Fernet encryption.
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple

import pyotp
from passlib.context import CryptContext
from jose import jwt, JWTError
from cryptography.fernet import Fernet

from config.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


# ── Password hashing ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    if len(password) < settings.password_min_length:
        return False, f"Password must be at least {settings.password_min_length} characters"
    if not any(c.isupper() for c in password):
        return False, "Password must include at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must include at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must include at least one digit"
    if not any(c in "!@#$%^&*()-_=+[]{}|;:,.<>/?`~" for c in password):
        return False, "Password must include at least one special character"
    return True, ""


# ── JWT tokens ────────────────────────────────────────────────────────────────

def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.jwt_access_expire_minutes)
    )
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": secrets.token_urlsafe(16),
        "type": "access",
    })
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> Tuple[str, str]:
    """Generate a refresh token. Returns (raw_token, hash_to_store)."""
    raw = secrets.token_urlsafe(64)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(days=settings.jwt_refresh_expire_days),
        "iat": datetime.utcnow(),
        "type": "refresh",
        "token_id": raw[:32],
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, hashed


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def verify_token(token: str, expected_type: str = "access") -> dict:
    """Decode a JWT. Raises JWTError on failure."""
    try:
        # Try local secret first
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != expected_type:
            raise JWTError(f"Token type mismatch: expected {expected_type}")
        return payload
    except JWTError:
        # Fallback to Supabase secret if available
        if settings.supabase_jwt_secret:
            return jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"])
        raise


# ── TOTP MFA ──────────────────────────────────────────────────────────────────

def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(secret: str, account_email: str, issuer: str = "DishHome") -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=account_email, issuer_name=issuer)


def verify_totp(secret: str, otp_code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(otp_code, valid_window=1)


# ── Fernet encryption (PII at rest) ───────────────────────────────────────────

_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key_material = settings.app_secret_key.encode()[:32].ljust(32, b"0")
        import base64
        fernet_key = base64.urlsafe_b64encode(key_material)
        _fernet = Fernet(fernet_key)
    return _fernet


def encrypt_field(value: str) -> str:
    if not value:
        return value
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_field(value: str) -> str:
    if not value:
        return value
    return _get_fernet().decrypt(value.encode()).decode()
