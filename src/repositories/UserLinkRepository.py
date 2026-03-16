from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from src.domain.models.UserLink import UserLink
from src.infrastructure.database.Session import get_db_session
from src.repositories.SQLAlchemyRawRepository import SQLAlchemyRawRepository

logger = logging.getLogger(__name__)


class UserLinkRepository(SQLAlchemyRawRepository):
    def __init__(self, model=UserLink):
        super().__init__(model)

    async def get_by_discord_id(self, discord_user_id: str) -> Optional[UserLink]:
        try:
            with get_db_session() as session:
                link = (
                    session.query(self.model)
                    .filter_by(discord_user_id=discord_user_id)
                    .first()
                )
                if link is not None:
                    session.expunge(link)
                return link
        except Exception as e:
            logger.error("get_by_discord_id error: %s", e)
            return None

    async def upsert(
        self,
        discord_user_id: str,
        external_user_id: str,
        **kwargs,
    ) -> Optional[UserLink]:
        try:
            with get_db_session() as session:
                link = (
                    session.query(self.model)
                    .filter_by(discord_user_id=discord_user_id)
                    .first()
                )
                if link is None:
                    link = UserLink(
                        discord_user_id=discord_user_id,
                        external_user_id=external_user_id,
                        **kwargs,
                    )
                    session.add(link)
                else:
                    link.external_user_id = external_user_id
                    link.is_active = True
                    for k, v in kwargs.items():
                        setattr(link, k, v)
                session.commit()
                session.expunge(link)
                return link
        except Exception as e:
            logger.error("upsert error: %s", e)
            return None

    async def update_tokens(
        self,
        discord_user_id: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
    ) -> bool:
        try:
            with get_db_session() as session:
                link = (
                    session.query(self.model)
                    .filter_by(discord_user_id=discord_user_id)
                    .first()
                )
                if link is None:
                    return False
                link.access_token = access_token
                if refresh_token is not None:
                    link.refresh_token = refresh_token
                if token_expires_at is not None:
                    link.token_expires_at = token_expires_at
                session.commit()
                return True
        except Exception as e:
            logger.error("update_tokens error: %s", e)
            return False

    async def deactivate(self, discord_user_id: str) -> bool:
        try:
            with get_db_session() as session:
                link = (
                    session.query(self.model)
                    .filter_by(discord_user_id=discord_user_id)
                    .first()
                )
                if link is None:
                    return False
                link.is_active = False
                link.access_token = None
                link.refresh_token = None
                link.session_cookie = None
                session.commit()
                return True
        except Exception as e:
            logger.error("deactivate error: %s", e)
            return False
