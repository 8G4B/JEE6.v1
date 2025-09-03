from sqlalchemy import Column, BigInteger, Boolean, String, DateTime
from datetime import datetime
from src.domain.models.Base import BaseModel


class ChannelSlowMode(BaseModel):
    __tablename__ = "channel_slow_mode"
    __table_args__ = {"mysql_collate": "utf8mb4_unicode_ci"}

    guild_id = Column(BigInteger, nullable=False, index=True)
    channel_id = Column(BigInteger, nullable=False, index=True)
    channel_name = Column(String(100), nullable=False, index=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
