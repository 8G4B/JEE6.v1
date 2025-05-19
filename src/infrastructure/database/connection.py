import mysql.connector
from mysql.connector import Error, MySQLConnection
import logging
from typing import Optional, Callable, TypeVar, Generic
from src.config.settings.base import BaseConfig

T = TypeVar("T")
logger = logging.getLogger(__name__)


class DatabaseConnection:
    @staticmethod
    def get_config():
        return {
            "host": BaseConfig.DB_HOST,
            "user": BaseConfig.DB_USER,
            "password": BaseConfig.DB_PASSWORD,
            "database": BaseConfig.DB_NAME,
            "charset": "utf8mb4",
            "collation": "utf8mb4_unicode_ci",
        }

    @staticmethod
    def get_connection() -> Optional[MySQLConnection]:
        try:
            config = DatabaseConnection.get_config()
            logger.debug(
                f"Attempting to connect to MySQL - Host: {config['host']}, User: {config['user']}, DB: {config['database']}"
            )
            connection = mysql.connector.connect(**config)

            if connection.is_connected():
                logger.debug("Successfully connected to MySQL database")
                db_info = connection.get_server_info()
                logger.debug(f"MySQL server version: {db_info}")
            return connection
        except Error as e:
            logger.error(f"Error connecting to MySQL: {e}")
            return None

    @staticmethod
    def execute_query(func: Callable[[MySQLConnection], T]) -> Optional[T]:
        connection = None
        try:
            connection = DatabaseConnection.get_connection()
            if not connection:
                logger.error("Failed to get database connection")
                return None

            result = func(connection)
            return result
        except Error as e:
            logger.error(f"Database error: {e}")
            return None
        finally:
            if connection and connection.is_connected():
                connection.close()
                logger.debug("Database connection closed")


def get_connection():
    return DatabaseConnection.get_connection()


def init_db():
    def _init_tables(connection: MySQLConnection) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS justice_records (
                    user_id BIGINT NOT NULL,
                    server_id BIGINT NOT NULL,
                    count INT NOT NULL DEFAULT 0,
                    last_timeout DATETIME NOT NULL,
                    PRIMARY KEY (user_id, server_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS timeout_history (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    server_id BIGINT NOT NULL,
                    moderator_id BIGINT NOT NULL,
                    reason VARCHAR(1000),
                    duration INT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_server (user_id, server_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            )
            connection.commit()
        logger.info("Database tables created successfully")
        return True

    return DatabaseConnection.execute_query(_init_tables)


def test_connection() -> bool:
    def _test(connection: MySQLConnection) -> bool:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        logger.info("Database connection test successful")
        return True

    result = DatabaseConnection.execute_query(_test)
    return result is True
