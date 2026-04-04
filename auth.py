# auth.py — JWT creation/decoding + FastAPI dependencies for auth and role checks

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import config
from database import get_db
from models import User, Role

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer()


# ── Password helpers ───────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd.verify(plain, hashed)


# ── Token helpers ──────────────────────────────────────────────────────────────

def create_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=config.settings.TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, config.settings.SECRET_KEY, algorithm=config.settings.ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, config.settings.SECRET_KEY, algorithms=[config.settings.ALGORITHM])
    except JWTError:
        return None


# ── FastAPI dependencies ───────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require(role: Role):
    """
    Role hierarchy:  viewer < analyst < admin
    Passing Role.analyst means analyst OR admin can access.
    """
    hierarchy = [Role.viewer, Role.analyst, Role.admin]

    def check(current_user: User = Depends(get_current_user)) -> User:
        if hierarchy.index(current_user.role) < hierarchy.index(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires '{role.value}' role or higher",
            )
        return current_user

    return check
