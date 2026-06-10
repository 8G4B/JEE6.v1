import logging
from typing import Optional, TypeVar, Callable, Any
from mysql.connector import MySQLConnection
from src.infrastructure.database.connection import DatabaseConnection

T = TypeVar("T")
R = TypeVar("R")

logger = logging.getLogger(__name__)


class MySQLRawRepository:
    def __init__(self):
        self.db_connection = DatabaseConnection

    def execute_query(self, func: Callable[[MySQLConnection], T]) -> Optional[T]:
        return self.db_connection.execute_query(func)

    def log_operation(self, operation: str, params: Any = None, success: bool = True):
        status = "OKAY" if success else "FAIL"
        if params:
            logger.info(f"{operation}({params}) {status}")
        else:
            logger.info(f"{operation} {status}")
