from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean
from src.domain.models.Base import BaseModel


class UserLink(BaseModel):
    __tablename__ = "user_links"

    discord_user_id = Column(String(50), unique=True, nullable=False, index=True)
    external_user_id = Column(String(100), nullable=False)

    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)

    session_cookie = Column(Text, nullable=True)
    session_expires_at = Column(DateTime, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    def __init__(
        self,
        discord_user_id: str,
        external_user_id: str,
        access_token: str = None,
        refresh_token: str = None,
        token_expires_at: datetime = None,
        session_cookie: str = None,
        session_expires_at: datetime = None,
        is_active: bool = True,
    ):
        self.discord_user_id = discord_user_id
        self.external_user_id = external_user_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires_at = token_expires_at
        self.session_cookie = session_cookie
        self.session_expires_at = session_expires_at
        self.is_active = is_active

    def __repr__(self) -> str:
        return (
            f"<UserLink discord={self.discord_user_id} "
            f"external={self.external_user_id}>"
        )
