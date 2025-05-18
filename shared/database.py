import mysql.connector
from mysql.connector import Error
import os
import asyncio
import logging
from functools import partial
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

DB_HOST = os.getenv('DB_HOST')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_CHARSET = 'utf8mb4'

async def get_connection():
    try:
        loop = asyncio.get_event_loop()
        connection = await loop.run_in_executor(
            None,
            partial(
                mysql.connector.connect,
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET,
                collation='utf8mb4_general_ci'
            )
        )
        logger.info(f"{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME} 연결 성공")
        return connection
    except Error as e:
        logger.error(f"{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME} 연결 실패: {e}")
        return None

async def create_tables():
    connection = await get_connection()
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_balance (
                    user_id BIGINT PRIMARY KEY,
                    balance BIGINT DEFAULT 0,
                    last_work_time DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
                ''')

                cursor.execute('''
                CREATE TABLE IF NOT EXISTS jackpot (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    amount BIGINT DEFAULT 1000000,
                    last_reset DATETIME,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
                ''')

                cursor.execute('''
                CREATE TABLE IF NOT EXISTS cooldowns (
                    user_id BIGINT,
                    game_type VARCHAR(50),
                    last_played DATETIME,
                    PRIMARY KEY (user_id, game_type)
                )
                ''')

                cursor.execute('''
                CREATE TABLE IF NOT EXISTS justice_records (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT,
                    server_id BIGINT,
                    count INT DEFAULT 0,
                    last_timeout DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_user_server (user_id, server_id)
                )
                ''')

                cursor.execute('''
                CREATE TABLE IF NOT EXISTS timeout_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT,
                    server_id BIGINT,
                    moderator_id BIGINT,
                    reason TEXT,
                    duration INT,  # Store duration in seconds
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                ''')

            connection.commit()
            logger.info("create_tables OKAY")
        except Exception as e:
            logger.error(f"create_tables FAIL: {e}")
        finally:
            connection.close()
    else:
        logger.error("DB 연결이 안됐는데 CREATE TABLE이 되겠노")

async def get_user_count(user_id: str, server_id: str) -> int:
    connection = await get_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            sql = "SELECT count FROM justice_records WHERE user_id = %s AND server_id = %s"
            cursor.execute(sql, (user_id, server_id))
            result = cursor.fetchone()
            cursor.close()
            if result:
                return result['count']
            return 0
        except Exception as e:
            logger.error(f"get_user_count({user_id}, {server_id}) FAIL: {e}")
            return 0
        finally:
            connection.close()
    return 0

async def set_user_count(user_id: str, server_id: str, count: int) -> bool:
    connection = await get_connection()
    if connection:
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO justice_records (user_id, server_id, count, last_timeout) 
                VALUES (%s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE count = %s, last_timeout = NOW()
                """
                cursor.execute(sql, (user_id, server_id, count, count))
            connection.commit()
            logger.info(f"set_user_count({user_id}, {server_id}, {count}) OKAY")
            return True
        except Exception as e:
            logger.error(f"set_user_count({user_id}, {server_id}, {count}) FAIL: {e}")
        finally:
            connection.close()
    return False

async def add_timeout_history(user_id: str, server_id: str, moderator_id: str, reason: str, duration: timedelta) -> bool:
    connection = await get_connection()
    if connection:
        try:
            with connection.cursor() as cursor:
                duration_seconds = int(duration.total_seconds())
                sql = """
                INSERT INTO timeout_history 
                (user_id, server_id, moderator_id, reason, duration) 
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (user_id, server_id, moderator_id, reason, duration_seconds))
            connection.commit()
            logger.info(f"add_timeout_history({user_id}, {server_id}, {moderator_id}) OKAY")
            return True
        except Exception as e:
            logger.error(f"add_timeout_history FAIL: {e}")
        finally:
            connection.close()
    return False

async def get_user_balance(user_id: int) -> int:
    connection = await get_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            sql = "SELECT balance FROM user_balance WHERE user_id = %s"
            cursor.execute(sql, (user_id,))
            result = cursor.fetchone()
            cursor.close()
            if result:
                return result['balance']
            return 0
        except Exception as e:
            logger.error(f"get_user_balance({user_id}) FAIL: {e}")
            return 0
        finally:
            connection.close()
    return 0

async def set_user_balance(user_id: int, amount: int) -> bool:
    connection = await get_connection()
    if connection:
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO user_balance (user_id, balance, last_work_time) 
                VALUES (%s, %s, NOW())
                ON DUPLICATE KEY UPDATE balance = %s, updated_at = NOW()
                """
                cursor.execute(sql, (user_id, amount, amount))
            connection.commit()
            logger.info(f"set_user_balance({user_id}, {amount}) OKAY")
            return True
        except Exception as e:
            logger.error(f"set_user_balance({user_id}, {amount}) FAIL: {e}")
        finally:
            connection.close()
    return False

async def get_jackpot() -> int:
    connection = await get_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            sql = "SELECT amount FROM jackpot ORDER BY id DESC LIMIT 1"
            cursor.execute(sql)
            result = cursor.fetchone()
            cursor.close()
            if result:
                return result['amount']
            return 1000000  
        except Exception as e:
            logger.error(f"get_jackpot FAIL: {e}")
            return 1000000
        finally:
            connection.close()
    return 1000000

async def set_jackpot(amount: int) -> bool:
    connection = await get_connection()
    if connection:
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO jackpot (amount, last_reset) 
                VALUES (%s, NOW())
                ON DUPLICATE KEY UPDATE amount = %s, updated_at = NOW()
                """
                cursor.execute(sql, (amount, amount))
            connection.commit()
            logger.info(f"set_jackpot({amount}) OKAY")
            return True
        except Exception as e:
            logger.error(f"set_jackpot({amount}) FAIL: {e}")
        finally:
            connection.close()
    return False

async def get_cooldown(user_id: int, game_type: str) -> Optional[datetime]:
    connection = await get_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            sql = "SELECT last_played FROM cooldowns WHERE user_id = %s AND game_type = %s"
            cursor.execute(sql, (user_id, game_type))
            result = cursor.fetchone()
            cursor.close()
            if result:
                return result['last_played']
            return None
        except Exception as e:
            logger.error(f"get_cooldown({user_id}, {game_type}) FAIL: {e}")
            return None
        finally:
            connection.close()
    return None

async def set_cooldown(user_id: int, game_type: str) -> bool:
    connection = await get_connection()
    if connection:
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO cooldowns (user_id, game_type, last_played) 
                VALUES (%s, %s, NOW())
                ON DUPLICATE KEY UPDATE last_played = NOW()
                """
                cursor.execute(sql, (user_id, game_type))
            connection.commit()
            logger.info(f"set_cooldown({user_id}, {game_type}) OKAY")
            return True
        except Exception as e:
            logger.error(f"set_cooldown({user_id}, {game_type}) FAIL: {e}")
        finally:
            connection.close()
    return False

async def get_sorted_balances() -> List[Tuple[int, int]]:
    connection = await get_connection()
    if connection:
        try:
            cursor = connection.cursor()
            sql = "SELECT user_id, balance FROM user_balance ORDER BY balance DESC"
            cursor.execute(sql)
            results = cursor.fetchall()
            cursor.close()
            return [(int(row[0]), int(row[1])) for row in results]
        except Exception as e:
            logger.error(f"get_sorted_balances FAIL: {e}")
            return []
        finally:
            connection.close()
    return []

async def init_db():
    try:
        await create_tables()
        logger.info("Database initialization completed successfully")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

async def test_connection():
    try:
        connection = await get_connection()
        if connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            connection.close()
            logger.info("Database connection test successful!")
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
    return False 