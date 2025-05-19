from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from src.domain.models.base import Base
from src.infrastructure.database.connection import DatabaseConnection
import logging
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)

config = DatabaseConnection.get_config()
DATABASE_URL = (
    f"mysql+mysqlconnector://{config['user']}:{config['password']}"
    f"@{config['host']}/{config['database']}?charset={config['charset']}"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"collation": config['collation']}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()

def create_tables():
    Base.metadata.create_all(bind=engine)
    update_schema()

def update_schema():
    try:
        inspector = inspect(engine)
        if 'periodic_clean' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('periodic_clean')]
            if 'channel_name' not in columns:
                logger.info("periodic_clean 테이블에 channel_name 컬럼 추가 중...")
                with engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE periodic_clean "
                        "ADD COLUMN channel_name VARCHAR(100) NOT NULL DEFAULT '', "
                        "ADD INDEX idx_channel_name (channel_name)"
                    ))
                    conn.commit()
                logger.info("channel_name 컬럼 추가 완료")
    except Exception as e:
        logger.error(f"테이블 스키마 업데이트 중 오류 발생: {e}")
