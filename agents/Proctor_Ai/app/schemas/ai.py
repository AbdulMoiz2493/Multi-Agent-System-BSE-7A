"""
AI-related Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# Insight Schemas
class InsightTypeEnum(str, Enum):
    CONSISTENCY = "consistency"
    PERFORMANCE = "performance"
    RECOMMENDATION = "recommendation"
    WARNING = "warning"


class InsightResponse(BaseModel):
    id: int
    user_id: int
    insight_type: InsightTypeEnum
    title: str
    message: str
    confidence_score: int
    created_at: datetime

    class Config:
        from_attributes = True


class InsightGenerateRequest(BaseModel):
    days_back: int = Field(default=30, ge=1, le=365, description="Number of days to analyze")


# Chatbot Schemas
class ChatbotActionTypeEnum(str, Enum):
    LOG_STUDY = "log_study"
    GET_STATUS = "get_status"
    TRIGGER_REMINDER = "trigger_reminder"
    GET_INSIGHTS = "get_insights"


class ChatbotLogStudyRequest(BaseModel):
    course_name: str = Field(..., description="Name of the course/subject", examples=["Mathematics"])
    duration_minutes: int = Field(..., ge=1, description="Duration in minutes", examples=[10])
    session_date: Optional[datetime] = Field(default=None, description="Session date, defaults to now")
    notes: Optional[str] = Field(default=None, description="Optional notes about the session", examples=["Studied calculus concepts"])


class ChatbotStatusResponse(BaseModel):
    user_id: int
    total_sessions: int
    total_hours: float
    consistency_score: float
    last_session_date: Optional[datetime]
    days_since_last_session: Optional[int]
    current_streak: int
    top_subject: Optional[str]


class ChatbotTriggerReminderRequest(BaseModel):
    subject: Optional[str] = Field(default=None, description="Specific subject to remind about")
    custom_message: Optional[str] = Field(default=None, description="Custom reminder message")


class ChatbotInsightsResponse(BaseModel):
    insights: List[InsightResponse]
    summary: str


# Supervisor Agent Schemas
class SupervisorStudySchedule(BaseModel):
    preferred_times: List[str] = Field(..., examples=[["09:00", "14:00", "19:00"]])
    daily_goal_hours: float = Field(..., examples=[3.5])


class SupervisorActivityLog(BaseModel):
    date: str = Field(..., examples=["2025-11-17"], description="Date in YYYY-MM-DD format")
    subject: str = Field(..., examples=["Mathematics"])
    hours: float = Field(..., examples=[2.5])
    status: str = Field(..., examples=["completed"])
    
    @field_validator('date')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate that date is in YYYY-MM-DD format"""
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')


class SupervisorUserFeedback(BaseModel):
    reminder_effectiveness: int = Field(..., ge=1, le=5, examples=[4])
    motivation_level: str = Field(..., examples=["high"])


class SupervisorContext(BaseModel):
    request_type: str = Field(..., examples=["weekly_analysis"])
    supervisor_id: str = Field(..., examples=["supervisor_001"])
    priority: str = Field(..., examples=["normal"])


class SupervisorAgentRequest(BaseModel):
    student_id: str = Field(..., examples=["1"])
    profile: Dict[str, Any] = Field(..., examples=[{"name": "John Doe", "grade": "10"}])
    study_schedule: SupervisorStudySchedule
    activity_log: List[SupervisorActivityLog]
    user_feedback: SupervisorUserFeedback
    context: SupervisorContext
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "student_id": "1",
                    "profile": {"name": "John Doe", "grade": "10"},
                    "study_schedule": {
                        "preferred_times": ["09:00", "14:00", "19:00"],
                        "daily_goal_hours": 3.5
                    },
                    "activity_log": [
                        {
                            "date": "2025-11-15",
                            "subject": "Mathematics",
                            "hours": 2.5,
                            "status": "completed"
                        },
                        {
                            "date": "2025-11-16",
                            "subject": "Physics",
                            "hours": 1.5,
                            "status": "completed"
                        }
                    ],
                    "user_feedback": {
                        "reminder_effectiveness": 4,
                        "motivation_level": "high"
                    },
                    "context": {
                        "request_type": "weekly_analysis",
                        "supervisor_id": "supervisor_001",
                        "priority": "normal"
                    }
                }
            ]
        }
    }


class SupervisorAnalysisSummary(BaseModel):
    total_study_hours: float
    average_completion_rate: str
    most_active_subject: str
    least_active_subject: Optional[str]


class SupervisorReminderScheduleItem(BaseModel):
    day: str
    time: str


class SupervisorPerformanceAlert(BaseModel):
    type: str
    message: str


class SupervisorReportSummary(BaseModel):
    week: str
    consistency_score: int
    engagement_level: str


class SupervisorAgentResponse(BaseModel):
    student_id: str
    analysis_summary: SupervisorAnalysisSummary
    recommendations: List[str]
    reminder_schedule: List[SupervisorReminderScheduleItem]
    performance_alerts: List[SupervisorPerformanceAlert]
    report_summary: SupervisorReportSummary


# Reminder Schemas
class ReminderScheduleRequest(BaseModel):
    days_ahead: int = Field(default=7, ge=1, le=30, description="Number of days to schedule")
    preferred_times: Optional[List[str]] = Field(default=None, description="Preferred times in HH:MM format")


class ReminderScheduleItem(BaseModel):
    day: str
    time: str
    datetime: datetime
    message: str
    subject: Optional[str]


class ReminderScheduleResponse(BaseModel):
    user_id: int
    schedule: List[ReminderScheduleItem]
    total_reminders: int


# Analytics Schemas
class StudyPatternAnalysis(BaseModel):
    total_sessions: int
    total_hours: float
    average_session_duration: float
    consistency_score: float
    most_active_subject: Optional[str]
    least_active_subject: Optional[str]
    subject_distribution: Dict[str, Any]
    peak_study_times: List[str]
    study_gaps: List[Dict[str, Any]]
    unique_study_days: int
