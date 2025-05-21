from sqlalchemy import Column, BigInteger, Integer
from src.domain.models.base import Base


class Jackpot(Base):
    __tablename__ = "jackpots"

    server_id = Column(BigInteger, primary_key=True)
    amount = Column(Integer, default=1_000_000, nullable=False)

    def __init__(self, server_id: int, amount: int = 1_000_000):
        self.server_id = server_id
        self.amount = amount
