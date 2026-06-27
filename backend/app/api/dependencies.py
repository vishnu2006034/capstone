from typing import List
from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import verify_token
from app.models.models import User

# OAuth2 scheme looking for token in the Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Decodes the JWT access token and returns the corresponding User entity.
    """
    payload = verify_token(token, is_refresh=False)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AppException(
            code="INVALID_TOKEN",
            message="Token payload is missing user identifier.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
        
    try:
        import uuid
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise AppException(
            code="INVALID_TOKEN",
            message="Token payload user identifier is invalid.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException(
            code="USER_NOT_FOUND",
            message="The user registered in this token does not exist.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
        
    return user


class RoleChecker:
    """
    Enforces Role-Based Access Control (RBAC).
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise AppException(
                code="FORBIDDEN",
                message=f"Access denied. Required roles: {self.allowed_roles}. Current role: {current_user.role}",
                status_code=status.HTTP_403_FORBIDDEN
            )
        return current_user
