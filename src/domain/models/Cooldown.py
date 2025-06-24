from sqlalchemy import Column, BigInteger, String, DateTime
from datetime import datetime
from src.domain.models.Base import Base


class Cooldown(Base):
    __tablename__ = "cooldowns"

    user_id = Column(BigInteger, primary_key=True)
    game_type = Column(String(50), primary_key=True)
    last_played = Column(DateTime, default=datetime.utcnow)

    def __init__(self, user_id: int, action_type: str, last_used: datetime = None):
        self.user_id = user_id
        self.game_type = action_type
        self.last_played = last_used or datetime.utcnow()
