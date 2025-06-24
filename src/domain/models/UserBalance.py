from sqlalchemy import Column, BigInteger, Integer
from src.domain.models.Base import Base


class UserBalance(Base):
    __tablename__ = "user_balances"

    user_id = Column(BigInteger, primary_key=True)
    server_id = Column(BigInteger, primary_key=True)
    balance = Column(Integer, default=0, nullable=False)

    def __init__(self, user_id: int, server_id: int, balance: int = 0):
        self.user_id = user_id
        self.server_id = server_id
        self.balance = balance
