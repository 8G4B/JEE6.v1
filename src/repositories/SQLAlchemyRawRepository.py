import logging
from typing import TypeVar, Type, Optional, List, Any, Dict, Tuple, Callable
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.infrastructure.database.session import get_db_session
from src.domain.models.base import BaseModel

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class SQLAlchemyRawRepository:
    def __init__(self, model: Type[T]):
        self.model = model

    def create(self, **kwargs) -> Optional[Any]:
        try:
            with get_db_session() as session:
                instance = self.model(**kwargs)
                session.add(instance)
                session.commit()
                session.refresh(instance)
                logger.debug(f"CREATE: {self.model.__name__}({kwargs})")
                return instance
        except Exception as e:
            logger.error(f"CREATE: {self.model.__name__}({kwargs}) - {e}")
            return None

    def get_by_id(self, id: Any) -> Optional[Any]:
        try:
            with get_db_session() as session:
                instance = session.query(self.model).get(id)
                return instance
        except Exception as e:
            logger.error(f"GET BY ID: {self.model.__name__}(id={id}) - {e}")
            return None

    def get_by_filter(self, **kwargs) -> Optional[Any]:
        try:
            with get_db_session() as session:
                instance = session.query(self.model).filter_by(**kwargs).first()
                return instance
        except Exception as e:
            logger.error(f"GET BY FILTER: {self.model.__name__}({kwargs}) - {e}")
            return None

    def get_all(self, limit: int = 100, **kwargs) -> List[Any]:
        try:
            with get_db_session() as session:
                query = session.query(self.model)
                if kwargs:
                    query = query.filter_by(**kwargs)
                return query.limit(limit).all()
        except Exception as e:
            logger.error(f"GET ALL: {self.model.__name__}({kwargs}) - {e}")
            return []

    def update(self, id: Any, **kwargs) -> bool:
        try:
            with get_db_session() as session:
                instance = session.query(self.model).get(id)
                if not instance:
                    logger.warning(
                        f"UPDATE: {self.model.__name__}(id={id}) - 항목이 없습니다"
                    )
                    return False

                for key, value in kwargs.items():
                    setattr(instance, key, value)

                session.commit()
                logger.debug(f"UPDATE: {self.model.__name__}(id={id}, {kwargs})")
                return True
        except Exception as e:
            logger.error(f"UPDATE: {self.model.__name__}(id={id}, {kwargs}) - {e}")
            return False

    def delete(self, id: Any) -> bool:
        try:
            with get_db_session() as session:
                instance = session.query(self.model).get(id)
                if not instance:
                    logger.warning(
                        f"DELETE: {self.model.__name__}(id={id}) - 항목이 없습니다"
                    )
                    return False

                session.delete(instance)
                session.commit()
                logger.debug(f"DELETE: {self.model.__name__}(id={id})")
                return True
        except Exception as e:
            logger.error(f"DELETE: {self.model.__name__}(id={id}) - {e}")
            return False

    def execute_raw_sql(self, sql: str, params: Dict[str, Any] = None) -> List[Tuple]:
        try:
            with get_db_session() as session:
                result = session.execute(text(sql), params or {})
                return result.fetchall()
        except Exception as e:
            logger.error(f"SQL EXECUTE: {sql}, params={params} - {e}")
            return []

    def execute_transaction(self, callback: Callable[[Session], Any]) -> Optional[Any]:
        try:
            with get_db_session() as session:
                result = callback(session)
                session.commit()
                return result
        except Exception as e:
            logger.error(f"TRANSACTION EXECUTE: {e}")
            return None
