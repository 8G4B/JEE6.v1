from sqlalchemy import Column, String, Text, UniqueConstraint
from src.domain.models.Base import BaseModel


class Meal(BaseModel):
    __tablename__ = "meals"

    date = Column(String(8), nullable=False, index=True)
    meal_code = Column(String(1), nullable=False)
    menu = Column(Text, nullable=False)
    cal_info = Column(String(100), nullable=True)

    __table_args__ = (UniqueConstraint("date", "meal_code", name="uix_date_meal_code"),)
