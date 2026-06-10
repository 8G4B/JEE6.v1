import logging
from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.orm import Session
from src.domain.models.base import BaseModel
from src.infrastructure.database.session import SessionLocal

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T], db: Session = None):
        self.model = model
        self.db = db if db is not None else SessionLocal()

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

    def __del__(self):
        if hasattr(self, "db") and self.db is not None:
            self.db.close()
