from sqlalchemy import create_engine, Column, Integer, BigInteger, String, DateTime, ForeignKey, Text, Interval, UniqueConstraint, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class UserBalance(Base):
    __tablename__ = "user_balance"

    user_id = Column(BigInteger, primary_key=True)
    balance = Column(BigInteger, default=0)
    last_work_time = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Jackpot(Base):
    __tablename__ = "jackpot"

    id = Column(Integer, primary_key=True)
    amount = Column(BigInteger, default=1000000)
    last_reset = Column(DateTime)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Cooldown(Base):
    __tablename__ = "cooldowns"

    user_id = Column(BigInteger, primary_key=True)
    game_type = Column(String(50), primary_key=True)
    last_played = Column(DateTime)

class JusticeRecord(Base):
    __tablename__ = "justice_records"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    server_id = Column(BigInteger)
    count = Column(Integer, default=0)
    last_timeout = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'server_id', name='unique_user_server'),
    )

class TimeoutHistory(Base):
    __tablename__ = "timeout_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    server_id = Column(BigInteger)
    moderator_id = Column(BigInteger)
    reason = Column(Text)
    duration = Column(Interval)
    created_at = Column(DateTime, default=func.now())

    justice_record = relationship("JusticeRecord", 
        foreign_keys=[user_id, server_id],
        primaryjoin="and_(TimeoutHistory.user_id==JusticeRecord.user_id, "
                    "TimeoutHistory.server_id==JusticeRecord.server_id)")

def init_db():
    Base.metadata.create_all(bind=engine)

class DatabaseSession:
    def __init__(self):
        self.db = SessionLocal()

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.db.close()

def test_connection():
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
            print("Database connection successful!")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False 