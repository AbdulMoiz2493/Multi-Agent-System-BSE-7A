from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime
from typing import Optional
from app.models.study_session import StudySession
from app.schemas.session import StudySessionCreate, StudySessionUpdate


def create_session(db: Session, user_id: int, session_data: StudySessionCreate) -> StudySession:
    """Create a new study session"""
    db_session = StudySession(
        user_id=user_id,
        **session_data.model_dump()
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def get_session(db: Session, session_id: int, user_id: int) -> StudySession | None:
    """Get a study session by ID (ensuring it belongs to the user)"""
    return db.query(StudySession).filter(
        and_(StudySession.id == session_id, StudySession.user_id == user_id)
    ).first()


def get_user_sessions(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    course_name: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> tuple[list[StudySession], int]:
    """Get user's study sessions with filtering and pagination"""
    query = db.query(StudySession).filter(StudySession.user_id == user_id)
    
    if course_name:
        query = query.filter(StudySession.course_name.ilike(f"%{course_name}%"))
    
    if start_date:
        query = query.filter(StudySession.session_date >= start_date)
    
    if end_date:
        query = query.filter(StudySession.session_date <= end_date)
    
    total = query.count()
    sessions = query.order_by(StudySession.session_date.desc()).offset(skip).limit(limit).all()
    
    return sessions, total


def update_session(
    db: Session,
    session: StudySession,
    session_update: StudySessionUpdate
) -> StudySession:
    """Update a study session"""
    update_data = session_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(session, field, value)
    
    db.commit()
    db.refresh(session)
    return session


def delete_session(db: Session, session: StudySession) -> None:
    """Delete a study session"""
    db.delete(session)
    db.commit()

