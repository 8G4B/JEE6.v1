from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from src.domain.models.user_balance import UserBalance
from src.repositories.base_repository import BaseRepository

class UserBalanceRepository(BaseRepository[UserBalance]):
    def get_by_user_id(self, db: Session, user_id: int) -> Optional[UserBalance]:
        return db.query(self.model).filter(self.model.user_id == user_id).first()

    def get_balance(self, db: Session, user_id: int) -> int:
        user = self.get_by_user_id(db, user_id)
        return user.balance if user else 0

    def set_balance(self, db: Session, user_id: int, amount: int) -> bool:
        try:
            user = self.get_by_user_id(db, user_id)
            if user:
                user.balance = amount
                user.updated_at = datetime.utcnow()
            else:
                user = UserBalance(
                    user_id=user_id,
                    balance=amount,
                    last_work_time=datetime.utcnow()
                )
                db.add(user)
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False

    def get_sorted_balances(self, db: Session) -> List[Tuple[int, int]]:
        users = db.query(self.model).order_by(self.model.balance.desc()).all()
        return [(user.user_id, user.balance) for user in users]

    def update_work_time(self, db: Session, user_id: int) -> bool:
        try:
            user = self.get_by_user_id(db, user_id)
            if user:
                user.last_work_time = datetime.utcnow()
                db.commit()
                return True
            return False
        except Exception:
            db.rollback()
            return False 