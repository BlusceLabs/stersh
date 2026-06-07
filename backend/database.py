"""Database models and connection pooling for watchfy backend."""
from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    create_engine, pool,
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session, relationship
from sqlalchemy.sql import func

# Configuration
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///watchfy.db")
DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "20"))
DB_POOL_RECYCLE = int(os.environ.get("DB_POOL_RECYCLE", "3600"))  # 1 hour
DB_POOL_PRE_PING = os.environ.get("DB_POOL_PRE_PING", "true").lower() == "true"

Base = declarative_base()


# ── Models ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(512), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    watchlist = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    playback_history = relationship("PlaybackHistory", back_populates="user", cascade="all, delete-orphan")
    ratings = relationship("Rating", back_populates="user", cascade="all, delete-orphan")
    ad_interactions = relationship("UserAdInteraction", back_populates="user", cascade="all, delete-orphan")
    analytics_events = relationship("AnalyticsEvent", back_populates="user", cascade="all, delete-orphan")


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tmdb_id = Column(Integer, unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False)
    overview = Column(Text)
    poster_path = Column(String(500))
    backdrop_path = Column(String(500))
    release_date = Column(String(20))
    vote_average = Column(Float, default=0)
    vote_count = Column(Integer, default=0)
    popularity = Column(Float, default=0)
    genre_ids = Column(String(500))  # JSON-serialized list
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))


class TVShow(Base):
    __tablename__ = "tv_shows"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tmdb_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(500), nullable=False)
    overview = Column(Text)
    poster_path = Column(String(500))
    backdrop_path = Column(String(500))
    first_air_date = Column(String(20))
    vote_average = Column(Float, default=0)
    vote_count = Column(Integer, default=0)
    popularity = Column(Float, default=0)
    genre_ids = Column(String(500))
    number_of_seasons = Column(Integer, default=0)
    number_of_episodes = Column(Integer, default=0)
    status = Column(String(50))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "tmdb_id", "media_type", name="uq_favorite_user_item"),
        Index("ix_favorite_user", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tmdb_id = Column(Integer, nullable=False)
    media_type = Column(String(10), nullable=False)  # 'movie' or 'tv'
    title = Column(String(500))
    poster_path = Column(String(500))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="favorites")


class Watchlist(Base):
    __tablename__ = "watchlist"
    __table_args__ = (
        UniqueConstraint("user_id", "tmdb_id", "media_type", name="uq_watchlist_user_item"),
        Index("ix_watchlist_user", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tmdb_id = Column(Integer, nullable=False)
    media_type = Column(String(10), nullable=False)  # 'movie' or 'tv'
    title = Column(String(500))
    poster_path = Column(String(500))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="watchlist")


class PlaybackHistory(Base):
    __tablename__ = "playback_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # nullable for anonymous
    tmdb_id = Column(Integer, nullable=False)
    media_type = Column(String(10), nullable=False)  # 'movie' or 'tv'
    title = Column(String(500))
    poster_path = Column(String(500))
    season = Column(Integer)
    episode = Column(Integer)
    current_time = Column(Float, default=0)  # seconds
    duration = Column(Float, default=0)  # seconds
    progress_pct = Column(Float, default=0)  # 0-100
    source_server = Column(String(50))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    user = relationship("User", back_populates="playback_history")

    __table_args__ = (
        Index("ix_playback_user_updated", "user_id", "updated_at"),
        Index("ix_playback_user_item", "user_id", "tmdb_id", "media_type", "season", "episode"),
    )


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "tmdb_id", "media_type", name="uq_rating_user_item"),
        Index("ix_rating_user", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tmdb_id = Column(Integer, nullable=False)
    media_type = Column(String(10), nullable=False)  # 'movie' or 'tv'
    rating = Column(Float, nullable=False)  # 0-10
    review = Column(Text)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    user = relationship("User", back_populates="ratings")


class Ad(Base):
    __tablename__ = "ads"
    __table_args__ = (
        Index("ix_ad_placement_active", "placement", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    image_url = Column(String(1000))
    target_url = Column(String(1000))
    placement = Column(String(50), default="banner")  # banner, interstitial, sidebar
    is_active = Column(Boolean, default=True)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    interactions = relationship("UserAdInteraction", back_populates="ad", cascade="all, delete-orphan")


class UserAdInteraction(Base):
    __tablename__ = "user_ad_interactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ad_id = Column(Integer, ForeignKey("ads.id"), nullable=False)
    interaction_type = Column(String(20), nullable=False)  # 'impression', 'click'
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="ad_interactions")
    ad = relationship("Ad", back_populates="interactions")


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    __table_args__ = (
        Index("ix_analytics_type_created", "event_type", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(String(50), nullable=False)  # 'play', 'pause', 'stop', 'search', 'click'
    event_data = Column(Text)  # JSON blob
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="analytics_events")


# Session factory with pooling
if "sqlite" in DATABASE_URL.lower():
    # SQLite in-memory or file
    engine = create_engine(
        DATABASE_URL,
        echo=False,  # Set to True for debugging
        future=True,
        connect_args={"check_same_thread": False},
    )
    # Enable WAL mode for better concurrent read performance
    from sqlalchemy import event as sa_event

    @sa_event.listens_for(engine, "connect")
    def _set_sqlite_wal(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA journal_mode=WAL")
        dbapi_connection.execute("PRAGMA synchronous=NORMAL")
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
