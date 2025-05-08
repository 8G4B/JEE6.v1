import mysql.connector
from mysql.connector import Error
import os
import asyncio
import logging
from functools import partial
from datetime import datetime, timedelta

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
                charset=DB_CHARSET
            )
        )
        logger.info(f"{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME} connection OKAY")
        return connection
    except Error as e:
        logger.error(f"{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME} connection FAIL: {e}")
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

asyncio.create_task(create_tables()) 