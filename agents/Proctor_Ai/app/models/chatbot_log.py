from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class ChatbotActionType(str, enum.Enum):
    LOG_STUDY = "log_study"
    GET_STATUS = "get_status"
    TRIGGER_REMINDER = "trigger_reminder"
    GET_INSIGHTS = "get_insights"


class ChatbotLog(Base):
    __tablename__ = "chatbot_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action_type = Column(Enum(ChatbotActionType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    request_data = Column(Text, nullable=True)
    response_data = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="chatbot_logs")
