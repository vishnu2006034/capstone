from typing import Generator
from fastapi import Depends, Header, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.exceptions import AppException
from app.models.models import User

# Re-export get_db
get_db = get_db

async def get_current_user(
    db: Session = Depends(get_db),
    x_user_email: str = Header(None, alias="X-User-Email")
) -> User:
    """
    Dependency to resolve the acting User from request headers.
    In production, this would validate JWT tokens / Active Directory scopes.
    """
    if not x_user_email:
        raise AppException(
            code="UNAUTHORIZED",
            message="Missing X-User-Email identity header.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
        
    user = db.query(User).filter(User.email == x_user_email).first()
    if not user:
        raise AppException(
            code="USER_NOT_FOUND",
            message=f"No corporate identity registered for email: {x_user_email}",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
        
    return user
