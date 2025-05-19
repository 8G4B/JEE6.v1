import mysql.connector
from mysql.connector import Error
import logging
from src.config.settings.base import BaseConfig

logger = logging.getLogger(__name__)

def get_connection():
    try:
        connection = mysql.connector.connect(
            host=BaseConfig.DB_HOST,
            user=BaseConfig.DB_USER,
            password=BaseConfig.DB_PASSWORD,
            database=BaseConfig.DB_NAME,
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        return connection
    except Error as e:
        logger.error(f"Error connecting to MySQL: {e}")
        return None

def init_db():
    try:
        connection = get_connection()
        if connection:
            cursor = connection.cursor()
            
            # Create justice_records table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS justice_records (
                    user_id BIGINT NOT NULL,
                    server_id BIGINT NOT NULL,
                    count INT NOT NULL DEFAULT 0,
                    last_timeout DATETIME NOT NULL,
                    PRIMARY KEY (user_id, server_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Create timeout_history table
            cursor.execute("""
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
            """)
            
            connection.commit()
            cursor.close()
            connection.close()
            logger.info("Database tables created successfully")
            return True
    except Error as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def test_connection() -> bool:
    try:
        connection = get_connection()
        if connection and connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            connection.close()
            logger.info("Database connection test successful")
            return True
        return False
    except Error as e:
        logger.error(f"Database connection test failed: {e}")
        return False
