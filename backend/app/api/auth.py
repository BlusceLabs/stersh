"""Authentication utilities for stersh backend."""
from __future__ import annotations

import os
import jwt
import hashlib
import secrets
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict

from app.database import Session, User, get_db

# Configuration
_DEFAULT_JWT_SECRET = "your-secret-key-change-this"
JWT_SECRET = os.environ.get("JWT_SECRET", _DEFAULT_JWT_SECRET)
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 days

if os.environ.get("ENV", "development").lower() in {"prod", "production"} and JWT_SECRET == _DEFAULT_JWT_SECRET:
    raise RuntimeError("JWT_SECRET must be set in production")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
router = APIRouter(prefix="/api/auth", tags=["auth"])

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

class UserOut(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserResponse(BaseModel):
    user: UserOut
    access_token: str
    refresh_token: str

class TokenRefreshRequest(BaseModel):
    refresh_token: str

# Password hashing utilities
def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with a random salt."""
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
        return hmac.compare_digest(pwdhash, hashed.hex())
    except Exception:
        return False

# Token utilities
def create_access_token(data: Dict[str, Any], expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    """Create an access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_in)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a refresh token."""
    refresh_data = {
        **data,
        "type": "refresh",
        "random": secrets.token_urlsafe(16),
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
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
    except jwt.InvalidTokenError:
        return None

def _issue_tokens(user: User) -> UserResponse:
    payload = {"username": user.username, "user_id": user.id, "permissions": ["admin"] if user.is_admin else []}
    return UserResponse(
        user=_user_out(user),
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
    )

def _user_out(user: User) -> UserOut:
    return UserOut.model_validate(user)

# Auth dependency
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
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
    """Update user information.

    Only the fields in `_UPDATABLE_USER_FIELDS` may be modified. Privilege-
    sensitive columns (`is_admin`, `is_active`) and credential columns
    (`password_hash`, `id`) are never writable through this path, even if
    a caller forwards a request body that includes them.
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if not isinstance(updates, dict):
        raise HTTPException(status_code=400, detail="updates must be an object")

    for key in updates:
        if key not in _UPDATABLE_USER_FIELDS:
            raise HTTPException(
                status_code=400,
                detail=f"Field '{key}' is not updatable",
            )

    for key, value in updates.items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return db_user


# Fields that update_user() will persist. Anything else is rejected
# before it reaches the ORM to prevent mass-assignment privilege
# escalation (e.g. `is_admin: True`).
_UPDATABLE_USER_FIELDS = frozenset({"email", "username"})

def delete_user(db, user_id: int) -> None:
    """Delete a user (soft delete by setting is_active=False)."""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.is_active = False
    db.commit()
    db.refresh(db_user)


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db=Depends(get_db)) -> UserResponse:
    db_user = create_user(db, user)
    return _issue_tokens(db_user)


@router.post("/token", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)) -> Token:
    user = authenticate_user(db, form.username, form.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    payload = {"username": user.username, "user_id": user.id, "permissions": ["admin"] if user.is_admin else []}
    return Token(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(body: TokenRefreshRequest, db=Depends(get_db)) -> Token:
    try:
        payload = jwt.decode(body.refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh" or not payload.get("user_id"):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    token_payload = {"username": user.username, "user_id": user.id, "permissions": ["admin"] if user.is_admin else []}
    return Token(
        access_token=create_access_token(token_payload),
        refresh_token=create_refresh_token(token_payload),
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_active_user)) -> UserOut:
    return _user_out(current_user)


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None


@router.patch("/me", response_model=UserOut)
async def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
) -> UserOut:
    updates: Dict[str, Any] = {}
    if body.username is not None:
        if db.query(User).filter(User.username == body.username, User.id != current_user.id).first():
            raise HTTPException(status_code=409, detail="Username already taken")
        updates["username"] = body.username
    if body.email is not None:
        if db.query(User).filter(User.email == body.email, User.id != current_user.id).first():
            raise HTTPException(status_code=409, detail="Email already registered")
        updates["email"] = body.email
    if not updates:
        return _user_out(current_user)
    updated = update_user(db, current_user.id, updates)
    return _user_out(updated)
