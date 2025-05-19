import logging
from datetime import datetime
from typing import Optional
from src.domain.models.cooldown import Cooldown
from src.repositories.base_repository import RawRepositoryBase
from src.infrastructure.database.session import get_db_session

logger = logging.getLogger(__name__)

class CooldownRepository(RawRepositoryBase):
    def __init__(self, model=Cooldown):
        super().__init__(model)

    async def get_cooldown(self, user_id: int, action_type: str) -> Optional[datetime]:
        try:
            with get_db_session() as session:
                cooldown = session.query(self.model).filter_by(
                    user_id=user_id,
                    action_type=action_type
                ).first()
                
                if not cooldown:
                    return None
                    
                return cooldown.last_used
        except Exception as e:
            logger.error(f"쿨다운 조회 중 오류: {e}")
            return None

    async def set_cooldown(self, user_id: int, action_type: str) -> None:
        try:
            with get_db_session() as session:
                cooldown = session.query(self.model).filter_by(
                    user_id=user_id,
                    action_type=action_type
                ).first()
                
                now = datetime.utcnow()
                
                if not cooldown:
                    cooldown = Cooldown(user_id=user_id, action_type=action_type, last_used=now)
                    session.add(cooldown)
                else:
                    cooldown.last_used = now
                    
                session.commit()
        except Exception as e:
            logger.error(f"쿨다운 설정 중 오류: {e}")

    async def delete_cooldown(self, user_id: int, action_type: str) -> None:
        try:
            with get_db_session() as session:
                cooldown = session.query(self.model).filter_by(
                    user_id=user_id,
                    action_type=action_type
                ).first()
                
                if cooldown:
                    session.delete(cooldown)
                    session.commit()
        except Exception as e:
            logger.error(f"쿨다운 삭제 중 오류: {e}")

    async def delete_all_cooldowns(self, user_id: int) -> None:
        try:
            with get_db_session() as session:
                cooldowns = session.query(self.model).filter_by(
                    user_id=user_id
                ).all()
                
                for cooldown in cooldowns:
                    session.delete(cooldown)
                    
                session.commit()
        except Exception as e:
            logger.error(f"모든 쿨다운 삭제 중 오류: {e}") 