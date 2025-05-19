import logging
from mysql.connector import MySQLConnection
from src.domain.models.timeout_history import TimeoutHistory
from src.repositories.raw_repository_base import RawRepositoryBase

logger = logging.getLogger(__name__)


class JusticeRepository(RawRepositoryBase):
    def __init__(self):
        super().__init__()

    async def get_user_count(self, user_id: int, server_id: int) -> int:
        def _get_count(connection: MySQLConnection) -> int:
            with connection.cursor(dictionary=True) as cursor:
                sql = "SELECT count FROM justice_records WHERE user_id = %s AND server_id = %s"
                logger.debug(
                    f"Executing SQL: {sql} with params: {(user_id, server_id)}"
                )
                cursor.execute(sql, (user_id, server_id))
                result = cursor.fetchone()
                logger.debug(f"Query result: {result}")
            return result["count"] if result else 0

        try:
            result = self.execute_query(_get_count)
            return result if result is not None else 0
        except Exception as e:
            logger.error(f"get_user_count({user_id}, {server_id}) FAIL: {e}")
            logger.exception("Detailed error:")
            return 0

    async def set_user_count(self, user_id: int, server_id: int, count: int) -> bool:
        def _set_count(connection: MySQLConnection) -> bool:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO justice_records (user_id, server_id, count, last_timeout) 
                VALUES (%s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE count = %s, last_timeout = NOW()
                """
                cursor.execute(sql, (user_id, server_id, count, count))
                connection.commit()
            return True

        try:
            result = self.execute_query(_set_count)
            success = result is True
            self.log_operation(
                "set_user_count", f"{user_id}, {server_id}, {count}", success=success
            )
            return success
        except Exception as e:
            logger.error(f"set_user_count({user_id}, {server_id}, {count}) FAIL: {e}")
            logger.exception("Detailed error:")
            return False

    async def add_timeout_history(self, history: TimeoutHistory) -> bool:
        def _add_history(connection: MySQLConnection) -> bool:
            with connection.cursor() as cursor:
                duration_seconds = int(history.duration.total_seconds())
                sql = """
                INSERT INTO timeout_history 
                (user_id, server_id, moderator_id, reason, duration) 
                VALUES (%s, %s, %s, %s, %s)
                """
                params = (
                    history.user_id,
                    history.server_id,
                    history.moderator_id,
                    history.reason,
                    duration_seconds,
                )
                cursor.execute(sql, params)
                connection.commit()
            return True

        try:
            result = self.execute_query(_add_history)
            success = result is True
            self.log_operation(
                "add_timeout_history",
                f"{history.user_id}, {history.server_id}, {history.moderator_id}",
                success=success,
            )
            return success
        except Exception as e:
            logger.error(f"add_timeout_history FAIL: {e}")
            logger.exception("Detailed error:")
            return False
