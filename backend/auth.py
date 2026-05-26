"""Authentication utilities for watchfy backend."""
from __future__ import annotations

import os
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from .database import SessionLocal, User, get_db

# Configuration
JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key-change-this")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 days

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

# Pydantic models
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None
    permissions: Optional[List[str]] = None

class UserBase(BaseModel):
    email: str
    username: str
    password: str

class UserCreate(UserBase):
    pass

class UserResponse(BaseModel):
    user: User
    access_token: str
    refresh_token: str

class UserOut(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    is_admin: bool
    created_at: datetime

class TokenRefreshRequest(BaseModel):
    refresh_token: str

# Password hashing utilities
def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    # Use secrets to generate a salt
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000,
        dklen=32
    )
    return '$'.join([str(100000), salt.decode('ascii'), pwdhash.hex()])

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    try:
        parts = hashed_password.split('$')
        if len(parts) != 3:
            return False
        iterations, salt, pwdhash = parts
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('ascii'),
            int(iterations),
            dklen=32
        )
        return pwdhash == hashed.hex()
    except Exception:
        return False

# Token utilities
def create_access_token(data: Dict[str, Any], expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    """Create an access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_in)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token() -> str:
    """Create a refresh token."""
    refresh_data = {
        "type": "refresh",
        "random": secrets.token_urlsafe(16),
        "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    }
    return jwt.encode(refresh_data, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> Optional[TokenData]:
    """Decode a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: Optional[str] = payload.get("username")
        user_id: Optional[int] = payload.get("user_id")
        permissions: Optional[List[str]] = payload.get("permissions")
        return TokenData(username=username, user_id=user_id, permissions=permissions)
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None

# Auth dependency
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: SessionLocal = Depends(get_db),
) -> User:
    """Get the current user from token."""
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = db.query(User).filter(User.id == payload.user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")
    
    return user

async def get_current_active_user(
    current_user: User = Security(get_current_user),
) -> User:
    """Get the current active user."""
    return current_user

# Auth service functions
def create_user(db, user: UserCreate) -> User:
    """Create a new user."""
    # Check if user exists
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Hash password
    hashed_password = hash_password(user.password)
    
    db_user = User(
        email=user.email,
        username=user.username,
        password_hash=hashed_password,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db, username: str, password: str) -> Optional[User]:
    """Authenticate a user."""
    user = db.query(User).filter(
        (User.email == username) | (User.username == username)
    ).first()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")
    return user

def update_user(db, user_id: int, updates: Dict[str, Any]) -> User:
    """Update user information."""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    for key, value in updates.items():
        if hasattr(db_user, key) and key != "id" and key != "password_hash":
            setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db, user_id: int) -> None:
    """Delete a user (soft delete by setting is_active=False)."""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.is_active = False
    db.commit()
    db.refresh(db_user)