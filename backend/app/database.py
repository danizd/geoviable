"""
GeoViable — Database Session Management

Provides the SQLAlchemy engine, session factory, and FastAPI dependency
for database access.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings

# ── Load configuration ──
settings = get_settings()

# ── Database engine (lazy-initialized) ──
engine = create_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    FastAPI dependency that yields a database session.

    Ensures the session is closed after the request, even on errors.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
