from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config.settings.base import BaseConfig

engine = create_engine(BaseConfig.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
