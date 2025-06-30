import logging
from datetime import datetime
from typing import Optional
from src.domain.models.Cooldown import Cooldown
from src.repositories.SQLAlchemyRawRepository import SQLAlchemyRawRepository
from src.infrastructure.database.Session import get_db_session

logger = logging.getLogger(__name__)


class CooldownRepository(SQLAlchemyRawRepository):
    def __init__(self, model=Cooldown):
        super().__init__(model)

    async def get_cooldown(self, user_id: int, action_type: str) -> Optional[datetime]:
        try:
            with get_db_session() as session:
                cooldown = (
                    session.query(self.model)
                    .filter_by(user_id=user_id, game_type=action_type)
                    .first()
                )

                if not cooldown:
                    return None

                return cooldown.last_played
        except Exception as e:
            logger.error(e)
            return None

    async def set_cooldown(self, user_id: int, action_type: str) -> None:
        try:
            with get_db_session() as session:
                cooldown = (
                    session.query(self.model)
                    .filter_by(user_id=user_id, game_type=action_type)
                    .first()
                )

                now = datetime.utcnow()

                if not cooldown:
                    cooldown = Cooldown(
                        user_id=user_id, action_type=action_type, last_used=now
                    )
                    session.add(cooldown)
                else:
                    cooldown.last_played = now

                session.commit()
        except Exception as e:
            logger.error(e)

    async def delete_cooldown(self, user_id: int, action_type: str) -> None:
        try:
            with get_db_session() as session:
                cooldown = (
                    session.query(self.model)
                    .filter_by(user_id=user_id, game_type=action_type)
                    .first()
                )

                if cooldown:
                    session.delete(cooldown)
                    session.commit()
        except Exception as e:
            logger.error(e)

    async def delete_all_cooldowns(self, user_id: int) -> None:
        try:
            with get_db_session() as session:
                cooldowns = session.query(self.model).filter_by(user_id=user_id).all()

                for cooldown in cooldowns:
                    session.delete(cooldown)

                session.commit()
        except Exception as e:
            logger.error(e)
