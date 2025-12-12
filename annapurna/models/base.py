"""Base model and database session configuration"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from annapurna.config import settings

# Create database engine with optimized connection pooling
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Test connections before use (prevents stale connections)
    pool_size=20,  # Increased from 10 for better concurrency (8 workers + API)
    max_overflow=10,  # Reduced from 20 (total capacity = 30 connections)
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=settings.environment == "development",
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


def get_db():
    """Dependency for getting database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
