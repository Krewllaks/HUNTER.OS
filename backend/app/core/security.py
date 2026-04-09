"""
HUNTER.OS / ARES - JWT Authentication & RBAC (Modernized)
Includes refresh token rotation with reuse detection.
"""
import bcrypt
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Union

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

# Swagger'ın token'ı nereden alacağını belirtir
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


# ── Password Hashing (Direct Bcrypt) ───────────────────
def hash_password(password: str) -> str:
    """Şifreyi passlib olmadan, doğrudan bcrypt ile hashler."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """Hashlenmiş şifreyi doğrular."""
    try:
        return bcrypt.checkpw(
            plain.encode('utf-8'), 
            hashed.encode('utf-8')
        )
    except Exception:
        return False


# ── JWT Token ────────────────────────────────────────────
def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    JWT Access Token üretir. 
    'subject' parametresi genellikle user_id olur.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    # Payload yapısı (sub: subject)
    to_encode = {"exp": expire, "sub": str(subject)}
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Token'ı çözer ve içindeki bilgileri (payload) döner."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Current User Dependency ─────────────────────────────
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    from app.models.user import User

    payload = decode_token(token)
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def require_role(required_role: str):
    """Yetki kontrolü (RBAC) için kullanılan fabrika fonksiyonu."""
    def role_checker(current_user=Depends(get_current_user)):
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return current_user

    return role_checker


# ── Refresh Token Rotation ───────────────────────────────

def create_refresh_token(user_id: int, db: Session) -> str:
    """Create a new refresh token, store hashed in DB, return raw token."""
    from app.models.refresh_token import RefreshToken

    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    db_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires,
    )
    db.add(db_token)
    db.commit()

    return raw_token


def rotate_refresh_token(old_raw_token: str, db: Session) -> tuple[str, int]:
    """
    Validate old refresh token, revoke it, issue new one.
    Returns (new_raw_token, user_id).
    Reuse detection: if a revoked token is presented, ALL user tokens are revoked.
    """
    from app.models.refresh_token import RefreshToken

    old_hash = hashlib.sha256(old_raw_token.encode()).hexdigest()
    stored = db.query(RefreshToken).filter(RefreshToken.token_hash == old_hash).first()

    if not stored:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Token reuse detected — potential compromise, revoke everything
    if stored.revoked:
        db.query(RefreshToken).filter(
            RefreshToken.user_id == stored.user_id,
        ).update({
            "revoked": True,
            "revoked_at": datetime.now(timezone.utc),
        })
        db.commit()
        raise HTTPException(
            status_code=401,
            detail="Token reuse detected. All sessions revoked.",
        )

    if stored.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # Revoke old token
    now = datetime.now(timezone.utc)
    stored.revoked = True
    stored.revoked_at = now

    # Issue new refresh token
    new_raw = secrets.token_urlsafe(48)
    new_hash = hashlib.sha256(new_raw.encode()).hexdigest()
    stored.replaced_by = new_hash

    new_token = RefreshToken(
        user_id=stored.user_id,
        token_hash=new_hash,
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_token)
    db.commit()

    return new_raw, stored.user_id


def revoke_all_user_tokens(user_id: int, db: Session) -> None:
    """Revoke all refresh tokens for a user (logout everywhere)."""
    from app.models.refresh_token import RefreshToken

    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False,  # noqa: E712
    ).update({
        "revoked": True,
        "revoked_at": datetime.now(timezone.utc),
    })
    db.commit()