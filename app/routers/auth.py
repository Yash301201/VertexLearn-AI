import logging
import smtplib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.schemas.user import (
    PasswordResetConfirm,
    PasswordResetRequest,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.routers.dependencies import get_current_user
from app.services.auth_service import (
    create_access_token,
    create_password_reset_token,
    get_user_id_from_password_reset_token,
    hash_password,
    verify_password,
)
from app.services.password_reset import send_password_reset_email

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.get("/me", response_model=UserResponse)
def get_authenticated_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/")
def auth_home():
    return {
        "message": "Authentication API is working"
    }


@router.post("/register")
def register(student: UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == student.email)) is not None:
        raise HTTPException(status_code=409, detail="Email is already registered")

    user = User(
        name=student.name,
        email=str(student.email),
        password_hash=hash_password(student.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered") from exc
    db.refresh(user)
    return {
        "message": "Student registered successfully",
        "student": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
    }


@router.post("/login")
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(credentials.email)))
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {
        "message": "Login request received",
        "email": user.email,
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "role": user.role,
    }


@router.post("/forgot-password")
def forgot_password(
    request: PasswordResetRequest, db: Session = Depends(get_db)
):
    user = db.scalar(select(User).where(User.email == str(request.email)))
    if user is not None:
        token = create_password_reset_token(user.id, user.password_hash)
        try:
            send_password_reset_email(user.email, token)
        except (OSError, smtplib.SMTPException, ValueError):
            logger.exception("Password reset email could not be sent")
    return {
        "message": "If an account exists and email delivery is configured, reset instructions will be sent."
    }


@router.post("/reset-password")
def reset_password(
    request: PasswordResetConfirm, db: Session = Depends(get_db)
):
    user_id = get_user_id_from_password_reset_token(request.token)
    if user_id is None:
        raise HTTPException(status_code=400, detail="Reset link is invalid or has expired")
    user = db.get(User, user_id)
    if user is None or get_user_id_from_password_reset_token(
        request.token, user.password_hash
    ) is None:
        raise HTTPException(status_code=400, detail="Reset link is invalid or has expired")

    user.password_hash = hash_password(request.password)
    db.commit()
    return {"message": "Password updated successfully"}