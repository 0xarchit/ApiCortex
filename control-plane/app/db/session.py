"""Database session factory and connection management.

Provides database engine initialization and session dependency for FastAPI
route handlers with automatic cleanup.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session.
    
    Yields a database session and ensures cleanup on completion.
    
    Yields:
        SQLAlchemy Session object.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
