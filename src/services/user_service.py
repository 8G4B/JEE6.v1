from typing import List, Tuple
from sqlalchemy.orm import Session
from src.repositories.user_balance_repository import UserBalanceRepository

class UserService:
    def __init__(self, user_repository: UserBalanceRepository):
        self.user_repository = user_repository

    def get_user_balance(self, db: Session, user_id: int) -> int:
        return self.user_repository.get_balance(db, user_id)

    def set_user_balance(self, db: Session, user_id: int, amount: int) -> bool:
        return self.user_repository.set_balance(db, user_id, amount)

    def get_leaderboard(self, db: Session) -> List[Tuple[int, int]]:
        return self.user_repository.get_sorted_balances(db)

    def update_work_time(self, db: Session, user_id: int) -> bool:
        return self.user_repository.update_work_time(db, user_id)

    def add_balance(self, db: Session, user_id: int, amount: int) -> bool:
        current_balance = self.get_user_balance(db, user_id)
        new_balance = current_balance + amount
        return self.set_user_balance(db, user_id, new_balance)

    def subtract_balance(self, db: Session, user_id: int, amount: int) -> bool:
        current_balance = self.get_user_balance(db, user_id)
        if current_balance < amount:
            return False
        new_balance = current_balance - amount
        return self.set_user_balance(db, user_id, new_balance) 