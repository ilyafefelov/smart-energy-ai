"""
Database connection & ORM configuration for Smart Energy AI
Uses SQLAlchemy for PostgreSQL connection pooling
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.sql import text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
import logging

from src.infrastructure.settings import get_database_url

logger = logging.getLogger(__name__)

# Database configuration - uses centralized settings
DATABASE_URL = get_database_url()

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
    echo=False,  # Set to True for SQL debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db():
    """Dependency for getting DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database (create tables)"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


def health_check():
    """Check database connectivity"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database health check: OK")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


# Connection pool event listeners for better logging
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    logger.debug("New database connection established")


@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    logger.debug("Connection returned to pool")


if __name__ == "__main__":
    # Test connection
    logging.basicConfig(level=logging.DEBUG)
    if health_check():
        print("✓ Database connection successful")
    else:
        print("✗ Database connection failed")
