from sqlalchemy import Column, BigInteger, Integer, Boolean, String
from src.domain.models.Base import BaseModel


class PeriodicClean(BaseModel):
    __tablename__ = "periodic_clean"
    __table_args__ = {"mysql_collate": "utf8mb4_unicode_ci"}

    guild_id = Column(BigInteger, nullable=False, index=True)
    channel_id = Column(BigInteger, nullable=False, index=True)
    channel_name = Column(String(100), nullable=False, index=True)
    interval_seconds = Column(Integer, nullable=False)
    enabled = Column(Boolean, default=True)
