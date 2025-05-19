from datetime import datetime
from sqlalchemy import Column, BigInteger, DateTime
from src.domain.models.base import BaseModel

class UserBalance(BaseModel):
    __tablename__ = 'user_balance'

    user_id = Column(BigInteger, primary_key=True)
    balance = Column(BigInteger, default=0)
    last_work_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 