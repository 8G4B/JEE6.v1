from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, BigInteger
from sqlalchemy.sql import func
from src.domain.models.base import Base


class LangFeedback(Base):
    __tablename__ = "lang_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)

    guild_id = Column(BigInteger, nullable=False, index=True)
    channel_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False, index=True)

    user_message = Column(Text, nullable=False)

    llm_raw_response = Column(Text, nullable=True)
    parsed_action = Column(String(20), nullable=False)
    tool_name = Column(String(50), nullable=True)
    tool_args = Column(Text, nullable=True)

    tool_success = Column(Boolean, nullable=True) 
    tool_error = Column(Text, nullable=True)
    result_type = Column(String(30), nullable=True)

    signal = Column(String(30), nullable=True) 
    signal_detail = Column(Text, nullable=True)

    label = Column(String(20), nullable=True) 
    correct_response = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
