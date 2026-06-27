from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token
)
from app.api.dependencies import get_current_user
from app.models.models import User
from app.schemas.auth import UserRegister, UserLogin, Token, TokenRefreshRequest, UserOut
from app.core.audit import log_audit_event

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    """
    Registers a new corporate identity.
    """
    # Check if email is already taken
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise AppException(
            code="EMAIL_ALREADY_TAKEN",
            message="An account with this email address already exists.",
            status_code=status.HTTP_400_BAD_REQUEST
        )
        
    hashed_pwd = hash_password(user_in.password)
    
    new_user = User(
        name=user_in.name,
        email=user_in.email,
        role=user_in.role,
        hashed_password=hashed_pwd
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Audit log user registration
    log_audit_event(db, "USER_REGISTER", {"email": new_user.email}, new_user.id)
    
    return new_user

@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticates user and returns JWT access and refresh tokens.
    """
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not user.hashed_password:
        raise AppException(
            code="INVALID_CREDENTIALS",
            message="Incorrect email or password.",
            status_code=status.HTTP_400_BAD_REQUEST
        )
        
    if not verify_password(credentials.password, user.hashed_password):
        raise AppException(
            code="INVALID_CREDENTIALS",
            message="Incorrect email or password.",
            status_code=status.HTTP_400_BAD_REQUEST
        )
        
    access = create_access_token(subject=user.id, role=user.role, email=user.email)
    refresh = create_refresh_token(subject=user.id, role=user.role, email=user.email)
    
    # Audit log user login
    log_audit_event(db, "USER_LOGIN", {"email": user.email}, user.id)
    
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=Token)
def refresh_token(payload: TokenRefreshRequest, db: Session = Depends(get_db)):
    """
    Issues a new access token using a valid refresh token.
    """
    decoded = verify_token(payload.refresh_token, is_refresh=True)
    user_id = decoded.get("sub")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException(
            code="USER_NOT_FOUND",
            message="The user reference inside this token does not exist.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
        
    access = create_access_token(subject=user.id, role=user.role, email=user.email)
    new_refresh = create_refresh_token(subject=user.id, role=user.role, email=user.email)
    
    return {
        "access_token": access,
        "refresh_token": new_refresh,
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    """
    Retrieves the currently authenticated user's profile.
    """
    return current_user
