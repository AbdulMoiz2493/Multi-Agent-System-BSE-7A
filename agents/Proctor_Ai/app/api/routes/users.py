from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.core.database import get_db
from app.models.user import User
from app.models.study_session import StudySession
from app.schemas.user import UserResponse, UserUpdate
from app.api.deps import get_current_user
from app.crud import user as crud_user

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user


@router.put("/me", response_model=UserResponse)
def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    # Check if email is being changed and if it's already taken
    if user_update.email and user_update.email != current_user.email:
        existing_user = crud_user.get_user_by_email(db, user_update.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    return crud_user.update_user(db, current_user, user_update)


@router.get("/{user_id}/reminder-data")
def get_user_reminder_data(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user data for reminder engine (for Person C)"""
    # Users can only access their own reminder data
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user's data"
        )
    
    # Get recent study sessions (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_sessions = db.query(StudySession).filter(
        StudySession.user_id == user_id,
        StudySession.session_date >= thirty_days_ago
    ).order_by(StudySession.session_date.desc()).all()
    
    # Calculate statistics
    total_sessions = len(recent_sessions)
    total_minutes = sum(session.duration_minutes for session in recent_sessions)
    courses = list(set(session.course_name for session in recent_sessions))
    
    # Calculate average sessions per week
    if total_sessions > 0:
        days_span = (datetime.now(timezone.utc) - recent_sessions[-1].session_date).days or 1
        avg_sessions_per_week = (total_sessions / days_span) * 7
    else:
        avg_sessions_per_week = 0
    
    return {
        "user_id": user_id,
        "total_sessions_30d": total_sessions,
        "total_minutes_30d": total_minutes,
        "avg_sessions_per_week": round(avg_sessions_per_week, 2),
        "courses": courses,
        "recent_sessions": [
            {
                "course_name": session.course_name,
                "duration_minutes": session.duration_minutes,
                "session_date": session.session_date.isoformat()
            }
            for session in recent_sessions[:10]  # Last 10 sessions
        ]
    }

