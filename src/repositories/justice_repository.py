import logging
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from src.domain.models.justice_record import JusticeRecord
from src.domain.models.timeout_history import TimeoutHistory

logger = logging.getLogger(__name__)

class JusticeRepository:
    def __init__(self, db):
        self.get_db = db

    async def get_user_count(self, user_id: int, server_id: int) -> int:
        try:
            with self.get_db() as db:
                result = db.execute(text(
                    "SELECT count FROM justice_records WHERE user_id = :user_id AND server_id = :server_id"
                ), {"user_id": user_id, "server_id": server_id}).fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"get_user_count({user_id}, {server_id}) FAIL: {e}")
            return 0

    async def set_user_count(self, user_id: int, server_id: int, count: int) -> bool:
        try:
            with self.get_db() as db:
                db.execute(text("""
                    INSERT INTO justice_records (user_id, server_id, count, last_timeout) 
                    VALUES (:user_id, :server_id, :count, NOW())
                    ON DUPLICATE KEY UPDATE count = :count, last_timeout = NOW()
                """), {
                    "user_id": user_id,
                    "server_id": server_id,
                    "count": count
                })
                db.commit()
                logger.info(f"set_user_count({user_id}, {server_id}, {count}) OKAY")
                return True
        except Exception as e:
            logger.error(f"set_user_count({user_id}, {server_id}, {count}) FAIL: {e}")
            return False

    async def add_timeout_history(self, history: TimeoutHistory) -> bool:
        try:
            with self.get_db() as db:
                duration_seconds = int(history.duration.total_seconds())
                db.execute(text("""
                    INSERT INTO timeout_history 
                    (user_id, server_id, moderator_id, reason, duration) 
                    VALUES (:user_id, :server_id, :moderator_id, :reason, :duration)
                """), {
                    "user_id": history.user_id,
                    "server_id": history.server_id,
                    "moderator_id": history.moderator_id,
                    "reason": history.reason,
                    "duration": duration_seconds
                })
                db.commit()
                logger.info(f"add_timeout_history({history.user_id}, {history.server_id}, {history.moderator_id}) OKAY")
                return True
        except Exception as e:
            logger.error(f"add_timeout_history FAIL: {e}")
            return False 