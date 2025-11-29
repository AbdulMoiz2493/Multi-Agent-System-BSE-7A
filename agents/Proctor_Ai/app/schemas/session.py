from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class StudySessionBase(BaseModel):
    course_name: str
    duration_minutes: int
    session_date: datetime
    notes: Optional[str] = None


class StudySessionCreate(StudySessionBase):
    pass


class StudySessionUpdate(BaseModel):
    course_name: Optional[str] = None
    duration_minutes: Optional[int] = None
    session_date: Optional[datetime] = None
    notes: Optional[str] = None


class StudySessionResponse(StudySessionBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class StudySessionListResponse(BaseModel):
    items: list[StudySessionResponse]
    total: int
    page: int
    page_size: int

