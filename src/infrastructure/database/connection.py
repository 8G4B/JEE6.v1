from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
import logging
from src.config.settings.base import BaseConfig

logger = logging.getLogger(__name__)

engine = create_engine(
    BaseConfig.DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    db = SessionLocal()
    try:
        return db
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    from src.domain.models.base import Base
    try:
        Base.metadata.create_all(bind=engine)
        db = get_db_session()
        try:
            db.execute(text("SELECT 1"))
            db.commit()
        finally:
            db.close()
        logger.info("Database tables created successfully")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def test_connection() -> bool:
    try:
        db = get_db_session()
        try:
            db.execute(text("SELECT 1"))
            db.commit()
            logger.info("Database connection test successful")
            return True
        finally:
            db.close()
    except SQLAlchemyError as e:
        logger.error(f"Database connection test failed: {e}")
        return False
