"""
HUNTER.OS - Auth API Endpoints
Updated to support Swagger OAuth2 Password Flow.
Rate limited: login 5/min, register 3/min per IP. Account lockout after 5 failed logins.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    hash_password, verify_password, create_access_token, get_current_user,
    create_refresh_token, rotate_refresh_token, revoke_all_user_tokens,
)
from app.core.rate_limiter import (
    login_rate_limiter,
    register_rate_limiter,
    login_attempt_tracker,
)
from app.models.user import User
from app.schemas.auth import RegisterRequest, RefreshRequest, TokenResponse, UserResponse
from app.services.audit_service import log_audit

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """Register a new user."""
    client_ip = request.client.host if request.client else "unknown"
    if not register_rate_limiter.check(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Try again later.",
        )

    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role="member",  # Default role; first user can be promoted via DB
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_audit(
        db,
        action="register",
        resource_type="user",
        resource_id=str(user.id),
        user_id=user.id,
        ip_address=client_ip,
        detail=f"New user registered: {user.email}",
    )
    db.commit()

    return user


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    Login endpoint: Swagger 'Authorize' butonundan gelen verileri (username/password) kabul eder.
    'username' alanı e-posta olarak işlenir.
    Rate limited: 5 requests/min per IP. Account locks after 5 consecutive failed attempts.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not login_rate_limiter.check(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Try again later.",
        )

    email = form_data.username

    # Check account lockout before doing any DB work
    if login_attempt_tracker.is_locked(email):
        raise HTTPException(
            status_code=423,
            detail="Account temporarily locked. Try again in 15 minutes.",
        )

    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        # Record failure for the attempted email (even if user doesn't exist,
        # to prevent email enumeration timing attacks)
        login_attempt_tracker.record_failure(email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # Successful login — clear failure history
    login_attempt_tracker.record_success(email)

    log_audit(
        db,
        action="login",
        resource_type="user",
        resource_id=str(user.id),
        user_id=user.id,
        ip_address=client_ip,
        detail=f"User logged in: {user.email}",
    )
    db.commit()

    # Issue access + refresh token pair
    access_token = create_access_token(subject=user.id)
    refresh_tok = create_refresh_token(user_id=user.id, db=db)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_tok,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(req: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access + refresh token pair (rotation)."""
    new_refresh, user_id = rotate_refresh_token(req.refresh_token, db)
    access_token = create_access_token(subject=user_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
def logout(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke all refresh tokens for the current user (logout everywhere)."""
    revoke_all_user_tokens(current_user.id, db)
    return {"detail": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return current_user


@router.patch("/profile", response_model=UserResponse)
def update_profile(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update current user's profile (full_name, email)."""
    allowed_fields = {"full_name", "email"}
    for field, value in data.items():
        if field in allowed_fields and value is not None:
            setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user