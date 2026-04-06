from sqlalchemy import Column, BigInteger, Boolean
from src.domain.models.Base import BaseModel


class ChannelLang(BaseModel):
    __tablename__ = "channel_lang"
    __table_args__ = {"mysql_collate": "utf8mb4_unicode_ci"}

    guild_id = Column(BigInteger, nullable=False, index=True)
    channel_id = Column(BigInteger, nullable=False, unique=True, index=True)
    enabled = Column(Boolean, default=True)
