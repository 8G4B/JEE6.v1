import logging
from src.domain.models.jackpot import Jackpot
from src.repositories.SQLAlchemyRawRepository import SQLAlchemyRawRepository
from src.infrastructure.database.session import get_db_session
from src.config.settings.gambling_settings import INITIAL_JACKPOT

logger = logging.getLogger(__name__)


class JackpotRepository(SQLAlchemyRawRepository):
    def __init__(self, model=Jackpot):
        super().__init__(model)

    async def get_jackpot(self, server_id: int) -> int:
        try:
            with get_db_session() as session:
                jackpot = (
                    session.query(self.model).filter_by(server_id=server_id).first()
                )

                if not jackpot:
                    logger.debug(
                        f"서버 {server_id}의 잭팟 정보가 없어 새로 생성합니다."
                    )
                    jackpot = Jackpot(server_id=server_id, amount=INITIAL_JACKPOT)
                    session.add(jackpot)
                    session.commit()

                return jackpot.amount
        except Exception as e:
            logger.error(f"잭팟 조회 중 오류: {e}")
            return INITIAL_JACKPOT

    async def set_jackpot(self, server_id: int, amount: int) -> None:
        try:
            with get_db_session() as session:
                jackpot = (
                    session.query(self.model).filter_by(server_id=server_id).first()
                )

                if not jackpot:
                    jackpot = Jackpot(server_id=server_id, amount=amount)
                    session.add(jackpot)
                else:
                    jackpot.amount = amount

                session.commit()
        except Exception as e:
            logger.error(f"잭팟 설정 중 오류: {e}")

    async def add_jackpot(self, server_id: int, amount: int) -> None:
        try:
            with get_db_session() as session:
                jackpot = (
                    session.query(self.model).filter_by(server_id=server_id).first()
                )

                if not jackpot:
                    jackpot = Jackpot(
                        server_id=server_id, amount=INITIAL_JACKPOT + amount
                    )
                    session.add(jackpot)
                else:
                    jackpot.amount += amount

                session.commit()
        except Exception as e:
            logger.error(f"잭팟 증가 중 오류: {e}")

    async def subtract_jackpot(self, server_id: int, amount: int) -> None:
        try:
            with get_db_session() as session:
                jackpot = (
                    session.query(self.model).filter_by(server_id=server_id).first()
                )

                if not jackpot:
                    jackpot = Jackpot(server_id=server_id, amount=INITIAL_JACKPOT)
                    session.add(jackpot)
                else:
                    jackpot.amount = max(INITIAL_JACKPOT, jackpot.amount - amount)

                session.commit()
        except Exception as e:
            logger.error(f"잭팟 감소 중 오류: {e}")

    async def reset_jackpot(self, server_id: int) -> None:
        try:
            with get_db_session() as session:
                jackpot = (
                    session.query(self.model).filter_by(server_id=server_id).first()
                )

                if not jackpot:
                    jackpot = Jackpot(server_id=server_id, amount=INITIAL_JACKPOT)
                    session.add(jackpot)
                else:
                    jackpot.amount = INITIAL_JACKPOT

                session.commit()
        except Exception as e:
            logger.error(f"잭팟 초기화 중 오류: {e}")
