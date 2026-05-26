#!/usr/bin/env python3
"""Setup development database with sample data."""
import os
import sys
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, User, Movie, TVShow, Favorite, Watchlist, PlaybackHistory, Rating, Ad, AnalyticsEvent
from auth import hash_password

def setup_dev_db():
    """Setup development database with sample data."""
    # Use SQLite for development
    engine = create_engine("sqlite:///watchfy_dev.db")
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # Create sample user
    sample_user = User(
        email="user@example.com",
        username="sampleuser",
        password_hash=hash_password("password123"),
        is_active=True,
        is_admin=False
    )
    db.add(sample_user)
    
    # Create sample movies (using TMDB IDs)
    sample_movies = [
        {
            "tmdb_id": 550,  # Fight Club
            "title": "Fight Club",
            "overview": "A ticking-time-bomb insomniac and a slippery soap salesman channel primal male aggression...",
            "release_date": "1999-10-15",
            "poster_path": "/adw6Cq3UqY8b1qV3z7bK9h1wf1i.jpg",
            "backdrop_path": "/4i0VG8qSOc4P1jiac9QpW6tIyyK.jpg",
            "original_language": "en",
            "popularity": 50.5,
            "vote_average": 8.4,
            "vote_count": 20000,
            "runtime": 139,
            "status": "Released",
            "tagline": "How much can you know about yourself if you've never been in a fight?",
            "genres": [{"id": 18, "name": "Drama"}, {"id": 53, "name": "Thriller"}],
        },
        {
            "tmdb_id": 680,  # Pulp Fiction
            "title": "Pulp Fiction",
            "overview": "A burger-loving hit man, his philosophical partner, a drug-addled gangster's moll...",
            "release_date": "1994-09-10",
            "poster_path": "/dM2w364MS1A9hmr5t5jWuT3MRm.jpg",
            "backdrop_path": "/lC2Kq5A5q7kW0C5b9sQc6lFqXxq.jpg",
            "original_language": "en",
            "popularity": 45.2,
            "vote_average": 8.5,
            "vote_count": 18000,
            "runtime": 154,
            "status": "Released",
            "tagline": "You won't know the facts until you've seen the fiction.",
            "genres": [{"id": 53, "name": "Thriller"}, {"id": 80, "name": "Crime"}],
        },
        {
            "tmdb_id": 19995,  # Avatar
            "title": "Avatar",
            "overview": "In the 22nd century, a paraplegic Marine is dispatched to the moon Pandora...",
            "release_date": "2009-12-10",
            "poster_path": "/kL9a6x9j9k5F9t3QY6aZ6aZ6aZ6.jpg",
            "backdrop_path": "/kL9a6aZ6aZ6aZ6aZ6aZ6aZ6aZ6.jpg",
            "original_language": "en",
            "popularity": 60.1,
            "vote_average": 7.8,
            "vote_count": 22000,
            "runtime": 162,
            "status": "Released",
            "tagline": "Enter the World of Pandora.",
            "genres": [{"id": 28, "name": "Action"}, {"id": 12, "name": "Adventure"}, {"id": 14, "name": "Fantasy"}],
        },
    ]
    
    for movie_data in sample_movies:
        movie = Movie(**movie_data)
        db.add(movie)
    
    # Create sample TV shows
    sample_tv = [
        {
            "tmdb_id": 1399,  # Game of Thrones
            "name": "Game of Thrones",
            "overview": "Seven noble families fight for control of the mythical land of Westeros...",
            "first_air_date": "2011-04-17",
            "poster_path": "/u3bZ9giQLc9ZQkDT7kx0sM2ZxTn.jpg",
            "backdrop_path": "/p0p9aJT9F7G0U6nY5lq4R8lG8yT.jpg",
            "original_language": "en",
            "popularity": 55.3,
            "vote_average": 8.1,
            "vote_count": 12000,
            "origin_country": ["US"],
            "genres": [{"id": 28, "name": "Action"}, {"id": 10759, "name": "Adventure"}, {"id": 18, "name": "Drama"}],
        },
        {
            "tmdb_id": 1402,  # Breaking Bad
            "name": "Breaking Bad",
            "overview": "When Walter White, a New Mexico chemistry teacher...",
            "first_air_date": "2008-01-20",
            "poster_path": "/ggkF52Y2uK9l6XSKy0O8w5qjU8v.jpg",
            "backdrop_path": "/jpw4Saf7t4wgSxfVvKY0r0W4z2K.jpg",
            "original_language": "en",
            "popularity": 48.7,
            "vote_average": 8.4,
            "vote_count": 15000,
            "origin_country": ["US"],
            "genres": [{"id": 18, "name": "Drama"}, {"id": 80, "name": "Crime"}],
        },
    ]
    
    for tv_data in sample_tv:
        tv_show = TVShow(**tv_data)
        db.add(tv_show)
    
    # Create some favorites for sample user
    for tmdb_id in [550, 680]:
        favorite = Favorite(
            user_id=sample_user.id,
            tmdb_id=tmdb_id,
            media_type="movie"
        )
        db.add(favorite)
    
    # Create some watchlist items
    for tmdb_id in [19995, 1399]:
        watchlist = Watchlist(
            user_id=sample_user.id,
            tmdb_id=tmdb_id,
            media_type="movie" if tmdb_id == 19995 else "tv",
            watched=False
        )
        db.add(watchlist)
    
    # Create some playback history
    history = PlaybackHistory(
        user_id=sample_user.id,
        tmdb_id=550,
        media_type="movie",
        progress=3600,  # 1 hour
        total_duration=8460,  # 2h 21min
    )
    db.add(history)
    
    # Create some ratings
    rating = Rating(
        user_id=sample_user.id,
        tmdb_id=550,
        media_type="movie",
        rating=5,
        review="Best movie ever!"
    )
    db.add(rating)
    
    # Create sample ad
    ad = Ad(
        ad_type="pre-roll",
        title="Test Ad",
        description="This is a test advertisement",
        video_url="https://example.com/ad.mp4",
        target_url="https://example.com",
        duration=15,
        active=True
    )
    db.add(ad)
    
    # Create sample analytics event
    event = AnalyticsEvent(
        user_id=sample_user.id,
        event_type="play",
        event_data={"movie_id": 550, "progress": 0}
    )
    db.add(event)
    
    db.commit()
    db.refresh(sample_user)
    
    print(f"Sample user created: {sample_user.username} ({sample_user.email})")
    print("Password: password123")
    print("Setup complete!")

if __name__ == "__main__":
    setup_dev_db()