"""Database models and connection pooling for watchfy backend."""
from __future__ import annotations

import os
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, pool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.sql import func

# Configuration
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///watchfy.db")
DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "20"))
DB_POOL_RECYCLE = int(os.environ.get("DB_POOL_RECYCLE", "3600"))  # 1 hour
DB_POOL_PRE_PING = os.environ.get("DB_POOL_PRE_PING", "true").lower() == "true"

Base = declarative_base()

# Session factory with pooling
if "sqlite" in DATABASE_URL.lower():
    # SQLite in-memory or file
    engine = create_engine(
        DATABASE_URL,
        echo=False,  # Set to True for debugging
        future=True,
    )
else:
    # PostgreSQL with connection pooling
    engine = create_engine(
        DATABASE_URL,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_recycle=DB_POOL_RECYCLE,
        pool_pre_ping=DB_POOL_PRE_PING,
        future=True,
        echo=False,
    )

SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))

def get_db():
    """Dependency for SQLAlchemy session with connection pooling."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize the database and create tables."""
    Base.metadata.create_all(bind=engine)
    logging.info("Database initialized with connection pool")
    return engine

def get_engine():
    """Get the engine instance (for testing)."""
    return engine