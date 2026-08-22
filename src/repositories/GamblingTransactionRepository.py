import logging

from src.config.settings.gamblingSettings import INITIAL_JACKPOT
from src.domain.models.UserBalance import UserBalance
from src.domain.models.jackpot import Jackpot
from src.infrastructure.database.async_utils import offload_db
from src.infrastructure.database.session import get_db_session


logger = logging.getLogger(__name__)


class GamblingTransactionRepository:
    @offload_db
    def transfer(
        self,
        sender_id: int,
        recipient_id: int,
        server_id: int,
        amount: int,
        tax: int,
    ) -> int | None:
        try:
            with get_db_session() as session:
                balances = {}
                for user_id in sorted((sender_id, recipient_id)):
                    balance = (
                        session.query(UserBalance)
                        .filter_by(user_id=user_id, server_id=server_id)
                        .with_for_update()
                        .first()
                    )
                    if balance is None:
                        balance = UserBalance(user_id=user_id, server_id=server_id)
                        session.add(balance)
                        session.flush()
                    balances[user_id] = balance

                sender = balances[sender_id]
                if sender.balance < amount:
                    return None

                jackpot = (
                    session.query(Jackpot)
                    .filter_by(server_id=server_id)
                    .with_for_update()
                    .first()
                )
                if jackpot is None:
                    jackpot = Jackpot(server_id=server_id, amount=INITIAL_JACKPOT)
                    session.add(jackpot)

                sender.balance -= amount
                balances[recipient_id].balance += amount - tax
                jackpot.amount += tax
                session.flush()
                return sender.balance
        except Exception:
            logger.exception("송금 트랜잭션 실패")
            return None
