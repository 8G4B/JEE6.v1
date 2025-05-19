import logging
from typing import Generic, TypeVar, Type, Optional, List, Any, Dict, Tuple, Callable
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.domain.models.base import Base
from src.infrastructure.database.session import get_db_session
from src.domain.models.base import BaseModel

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class RawRepositoryBase:
    def __init__(self, model: Type[T]):
        self.model = model

    def create(self, **kwargs) -> Optional[Any]:
        try:
            with get_db_session() as session:
                instance = self.model(**kwargs)
                session.add(instance)
                session.commit()
                session.refresh(instance)
                logger.debug(f"생성됨: {self.model.__name__}({kwargs})")
                return instance
        except Exception as e:
            logger.error(f"생성 실패: {self.model.__name__}({kwargs}) - {e}")
            return None

    def get_by_id(self, id: Any) -> Optional[Any]:
        try:
            with get_db_session() as session:
                instance = session.query(self.model).get(id)
                return instance
        except Exception as e:
            logger.error(f"조회 실패: {self.model.__name__}(id={id}) - {e}")
            return None

    def get_by_filter(self, **kwargs) -> Optional[Any]:
        try:
            with get_db_session() as session:
                instance = session.query(self.model).filter_by(**kwargs).first()
                return instance
        except Exception as e:
            logger.error(f"필터 조회 실패: {self.model.__name__}({kwargs}) - {e}")
            return None

    def get_all(self, limit: int = 100, **kwargs) -> List[Any]:
        try:
            with get_db_session() as session:
                query = session.query(self.model)
                if kwargs:
                    query = query.filter_by(**kwargs)
                return query.limit(limit).all()
        except Exception as e:
            logger.error(f"전체 조회 실패: {self.model.__name__}({kwargs}) - {e}")
            return []

    def update(self, id: Any, **kwargs) -> bool:
        try:
            with get_db_session() as session:
                instance = session.query(self.model).get(id)
                if not instance:
                    logger.warning(
                        f"업데이트 실패: {self.model.__name__}(id={id}) - 항목이 없습니다"
                    )
                    return False

                for key, value in kwargs.items():
                    setattr(instance, key, value)

                session.commit()
                logger.debug(f"업데이트됨: {self.model.__name__}(id={id}, {kwargs})")
                return True
        except Exception as e:
            logger.error(
                f"업데이트 실패: {self.model.__name__}(id={id}, {kwargs}) - {e}"
            )
            return False

    def delete(self, id: Any) -> bool:
        try:
            with get_db_session() as session:
                instance = session.query(self.model).get(id)
                if not instance:
                    logger.warning(
                        f"삭제 실패: {self.model.__name__}(id={id}) - 항목이 없습니다"
                    )
                    return False

                session.delete(instance)
                session.commit()
                logger.debug(f"삭제됨: {self.model.__name__}(id={id})")
                return True
        except Exception as e:
            logger.error(f"삭제 실패: {self.model.__name__}(id={id}) - {e}")
            return False

    def execute_raw_sql(self, sql: str, params: Dict[str, Any] = None) -> List[Tuple]:
        try:
            with get_db_session() as session:
                result = session.execute(text(sql), params or {})
                return result.fetchall()
        except Exception as e:
            logger.error(f"SQL 실행 실패: {sql}, params={params} - {e}")
            return []

    def execute_transaction(self, callback: Callable[[Session], Any]) -> Optional[Any]:
        try:
            with get_db_session() as session:
                result = callback(session)
                session.commit()
                return result
        except Exception as e:
            logger.error(f"트랜잭션 실행 실패 - {e}")
            return None


class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T], db: Session):
        self.model = model
        self.db = db

    def get_by_id(self, id: int) -> Optional[T]:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self) -> List[T]:
        return self.db.query(self.model).all()

    def create(self, entity: T) -> T:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(self, entity: T) -> T:
        self.db.merge(entity)
        self.db.commit()
        return entity

    def delete(self, id: int) -> bool:
        entity = self.get_by_id(id)
        if entity:
            self.db.delete(entity)
            self.db.commit()
            return True
        return False
