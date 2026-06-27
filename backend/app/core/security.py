import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.core.exceptions import AppException
from fastapi import status

def hash_password(password: str) -> str:
    """
    Hashes a plain text password using bcrypt.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain text password against its hashed value.
    """
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(subject: str, role: str, email: str) -> str:
    """
    Generates a JWT access token.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(subject),
        "role": role,
        "email": email,
        "type": "access",
        "exp": int(expire.timestamp())
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(subject: str, role: str, email: str) -> str:
    """
    Generates a JWT refresh token.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(subject),
        "role": role,
        "email": email,
        "type": "refresh",
        "exp": int(expire.timestamp())
    }
    return jwt.encode(payload, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def verify_token(token: str, is_refresh: bool = False) -> dict:
    """
    Decodes and validates a JWT token.
    """
    secret = settings.JWT_REFRESH_SECRET_KEY if is_refresh else settings.JWT_SECRET_KEY
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
        token_type = "refresh" if is_refresh else "access"
        if payload.get("type") != token_type:
            raise AppException(
                code="INVALID_TOKEN",
                message="Invalid token scope or type.",
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise AppException(
            code="EXPIRED_TOKEN",
            message="Token signature has expired.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    except jwt.PyJWTError:
        raise AppException(
            code="INVALID_TOKEN",
            message="Could not validate credentials.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
