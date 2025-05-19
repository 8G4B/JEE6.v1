import logging
from typing import Optional
from datetime import datetime, timedelta
from src.domain.models.justice_record import JusticeRecord
from src.domain.models.timeout_history import TimeoutHistory

logger = logging.getLogger(__name__)

class JusticeRepository:
    def __init__(self, db):
        self.db = db

    async def get_user_count(self, user_id: int, server_id: int) -> int:
        try:
            cursor = self.db.cursor(dictionary=True)
            sql = "SELECT count FROM justice_records WHERE user_id = %s AND server_id = %s"
            cursor.execute(sql, (user_id, server_id))
            result = cursor.fetchone()
            cursor.close()
            return result['count'] if result else 0
        except Exception as e:
            logger.error(f"get_user_count({user_id}, {server_id}) FAIL: {e}")
            return 0

    async def set_user_count(self, user_id: int, server_id: int, count: int) -> bool:
        try:
            with self.db.cursor() as cursor:
                sql = """
                INSERT INTO justice_records (user_id, server_id, count, last_timeout) 
                VALUES (%s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE count = %s, last_timeout = NOW()
                """
                cursor.execute(sql, (user_id, server_id, count, count))
            self.db.commit()
            logger.info(f"set_user_count({user_id}, {server_id}, {count}) OKAY")
            return True
        except Exception as e:
            logger.error(f"set_user_count({user_id}, {server_id}, {count}) FAIL: {e}")
            return False

    async def add_timeout_history(self, history: TimeoutHistory) -> bool:
        try:
            with self.db.cursor() as cursor:
                duration_seconds = int(history.duration.total_seconds())
                sql = """
                INSERT INTO timeout_history 
                (user_id, server_id, moderator_id, reason, duration) 
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    history.user_id,
                    history.server_id,
                    history.moderator_id,
                    history.reason,
                    duration_seconds
                ))
            self.db.commit()
            logger.info(f"add_timeout_history({history.user_id}, {history.server_id}, {history.moderator_id}) OKAY")
            return True
        except Exception as e:
            logger.error(f"add_timeout_history FAIL: {e}")
            return False 