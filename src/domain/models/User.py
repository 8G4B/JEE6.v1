from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    discord_id = Column(String, unique=True)
    points = Column(Integer, default=0)
    created_at = Column(DateTime)
