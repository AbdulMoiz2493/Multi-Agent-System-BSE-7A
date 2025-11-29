from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class InsightType(str, enum.Enum):
    CONSISTENCY = "consistency"
    PERFORMANCE = "performance"
    RECOMMENDATION = "recommendation"
    WARNING = "warning"


class Insight(Base):
    __tablename__ = "insights"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    insight_type = Column(Enum(InsightType, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    confidence_score = Column(Integer, default=0)  # 0-100
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="insights")
