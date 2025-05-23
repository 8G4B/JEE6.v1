import logging
from typing import List, Tuple
from src.domain.models.UserBalance import UserBalance
from src.repositories.SQLAlchemyRawRepository import SQLAlchemyRawRepository
from src.infrastructure.database.session import get_db_session

logger = logging.getLogger(__name__)


class UserBalanceRepository(SQLAlchemyRawRepository):
    def __init__(self, model=UserBalance):
        super().__init__(model)

    async def get_user_balance(self, user_id: int, server_id: int) -> int:
        try:
            with get_db_session() as session:
                user_balance = (
                    session.query(self.model)
                    .filter_by(user_id=user_id, server_id=server_id)
                    .first()
                )

                if not user_balance:
                    logger.debug(
                        f"사용자 {user_id}의 잔액 정보가 없어 새로 생성합니다."
                    )
                    user_balance = UserBalance(user_id=user_id, server_id=server_id)
                    session.add(user_balance)
                    session.commit()

                return user_balance.balance
        except Exception as e:
            logger.error(e)
            return 0

    async def set_user_balance(
        self, user_id: int, server_id: int, balance: int
    ) -> None:
        try:
            with get_db_session() as session:
                user_balance = (
                    session.query(self.model)
                    .filter_by(user_id=user_id, server_id=server_id)
                    .first()
                )

                if not user_balance:
                    user_balance = UserBalance(
                        user_id=user_id, server_id=server_id, balance=balance
                    )
                    session.add(user_balance)
                else:
                    user_balance.balance = balance

                session.commit()
        except Exception as e:
            logger.error(e)

    async def add_user_balance(self, user_id: int, server_id: int, amount: int) -> None:
        try:
            with get_db_session() as session:
                user_balance = (
                    session.query(self.model)
                    .filter_by(user_id=user_id, server_id=server_id)
                    .first()
                )

                if not user_balance:
                    user_balance = UserBalance(
                        user_id=user_id, server_id=server_id, balance=amount
                    )
                    session.add(user_balance)
                else:
                    user_balance.balance += amount

                session.commit()
        except Exception as e:
            logger.error(e)

    async def subtract_user_balance(
        self, user_id: int, server_id: int, amount: int
    ) -> None:
        try:
            with get_db_session() as session:
                user_balance = (
                    session.query(self.model)
                    .filter_by(user_id=user_id, server_id=server_id)
                    .first()
                )

                if not user_balance:
                    user_balance = UserBalance(
                        user_id=user_id, server_id=server_id, balance=0
                    )
                    session.add(user_balance)
                else:
                    user_balance.balance = max(0, user_balance.balance - amount)

                session.commit()
        except Exception as e:
            logger.error(e)

    async def get_rankings(
        self, server_id: int, limit: int = 10
    ) -> List[Tuple[int, int]]:
        try:
            with get_db_session() as session:
                result = (
                    session.query(self.model.user_id, self.model.balance)
                    .filter(self.model.server_id == server_id)
                    .order_by(self.model.balance.desc())
                    .limit(limit)
                    .all()
                )
                return result
        except Exception as e:
            logger.error(e)
            return []

    async def get_sorted_balances(
        self, server_id: int, limit: int = 100
    ) -> List[Tuple[int, int]]:
        try:
            with get_db_session() as session:
                query = (
                    session.query(self.model.user_id, self.model.balance)
                    .filter_by(server_id=server_id)
                    .order_by(self.model.balance.desc())
                    .limit(limit)
                )

                result = [(row[0], row[1]) for row in query.all()]
                return result
        except Exception as e:
            logger.error(e)
            return []
