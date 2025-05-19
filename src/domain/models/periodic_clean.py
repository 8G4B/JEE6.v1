from sqlalchemy import Column, BigInteger, Integer, Boolean
from src.domain.models.base import BaseModel

class PeriodicClean(BaseModel):
    __tablename__ = 'periodic_clean'

    guild_id = Column(BigInteger, nullable=False, index=True)
    channel_id = Column(BigInteger, nullable=False, index=True)
    interval_seconds = Column(Integer, nullable=False)
    enabled = Column(Boolean, default=True) 