from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config.settings.base import BaseConfig

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
