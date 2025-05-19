import logging
from typing import Optional, Callable
from datetime import datetime, timedelta
from mysql.connector import MySQLConnection
from src.domain.models.justice_record import JusticeRecord
from src.domain.models.timeout_history import TimeoutHistory

logger = logging.getLogger(__name__)

class JusticeRepository:
    def __init__(self, get_connection: Callable[[], Optional[MySQLConnection]]):
        logger.debug(f"Initializing JusticeRepository with get_connection type: {type(get_connection)}")
        self._get_connection = get_connection

    async def get_user_count(self, user_id: int, server_id: int) -> int:
        try:
            logger.debug(f"Getting connection for get_user_count")
            connection = self._get_connection()
            logger.debug(f"Connection result type: {type(connection)}")
            
            if not connection:
                logger.error("Failed to get database connection")
                return 0
                
            with connection.cursor(dictionary=True) as cursor:
                sql = "SELECT count FROM justice_records WHERE user_id = %s AND server_id = %s"
                logger.debug(f"Executing SQL: {sql} with params: {(user_id, server_id)}")
                cursor.execute(sql, (user_id, server_id))
                result = cursor.fetchone()
                logger.debug(f"Query result: {result}")
            
            connection.close()
            return result['count'] if result else 0
        except Exception as e:
            logger.error(f"get_user_count({user_id}, {server_id}) FAIL: {e}")
            logger.exception("Detailed error:")
            return 0

    async def set_user_count(self, user_id: int, server_id: int, count: int) -> bool:
        try:
            logger.debug(f"Getting connection for set_user_count")
            connection = self._get_connection()
            logger.debug(f"Connection result type: {type(connection)}")
            
            if not connection:
                logger.error("Failed to get database connection")
                return False
                
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO justice_records (user_id, server_id, count, last_timeout) 
                VALUES (%s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE count = %s, last_timeout = NOW()
                """
                logger.debug(f"Executing SQL: {sql} with params: {(user_id, server_id, count, count)}")
                cursor.execute(sql, (user_id, server_id, count, count))
                connection.commit()
                logger.debug("SQL executed and committed successfully")
            
            connection.close()
            logger.info(f"set_user_count({user_id}, {server_id}, {count}) OKAY")
            return True
        except Exception as e:
            logger.error(f"set_user_count({user_id}, {server_id}, {count}) FAIL: {e}")
            logger.exception("Detailed error:")
            return False

    async def add_timeout_history(self, history: TimeoutHistory) -> bool:
        try:
            logger.debug(f"Getting connection for add_timeout_history")
            connection = self._get_connection()
            logger.debug(f"Connection result type: {type(connection)}")
            
            if not connection:
                logger.error("Failed to get database connection")
                return False
                
            with connection.cursor() as cursor:
                duration_seconds = int(history.duration.total_seconds())
                sql = """
                INSERT INTO timeout_history 
                (user_id, server_id, moderator_id, reason, duration) 
                VALUES (%s, %s, %s, %s, %s)
                """
                logger.debug(f"Executing SQL: {sql} with params: {(history.user_id, history.server_id, history.moderator_id, history.reason, duration_seconds)}")
                cursor.execute(sql, (
                    history.user_id,
                    history.server_id,
                    history.moderator_id,
                    history.reason,
                    duration_seconds
                ))
                connection.commit()
                logger.debug("SQL executed and committed successfully")
            
            connection.close()
            logger.info(f"add_timeout_history({history.user_id}, {history.server_id}, {history.moderator_id}) OKAY")
            return True
        except Exception as e:
            logger.error(f"add_timeout_history FAIL: {e}")
            logger.exception("Detailed error:")
            return False 