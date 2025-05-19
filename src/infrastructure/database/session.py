from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from src.config.settings.base import BaseConfig
from src.domain.models.base import Base
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = (
    f"mysql+mysqlconnector://{BaseConfig.DB_USER}:{BaseConfig.DB_PASSWORD}"
    f"@{BaseConfig.DB_HOST}/{BaseConfig.DB_NAME}?charset=utf8mb4"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"collation": "utf8mb4_unicode_ci"}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    return SessionLocal()

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
