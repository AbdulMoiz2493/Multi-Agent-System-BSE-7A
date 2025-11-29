from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Optional
from app.core.database import get_db
from app.models.user import User
from app.models.study_session import StudySession
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/user-progress")
def get_user_progress(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user progress metrics"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total sessions and minutes
    sessions_query = db.query(StudySession).filter(
        and_(
            StudySession.user_id == current_user.id,
            StudySession.session_date >= start_date
        )
    )
    
    total_sessions = sessions_query.count()
    total_minutes = db.query(func.sum(StudySession.duration_minutes)).filter(
        and_(
            StudySession.user_id == current_user.id,
            StudySession.session_date >= start_date
        )
    ).scalar() or 0
    
    # Sessions per week
    weeks = days / 7
    sessions_per_week = round(total_sessions / weeks, 2) if weeks > 0 else 0
    
    # Average session duration
    avg_duration = round(total_minutes / total_sessions, 2) if total_sessions > 0 else 0
    
    # Course breakdown
    course_stats = db.query(
        StudySession.course_name,
        func.count(StudySession.id).label("count"),
        func.sum(StudySession.duration_minutes).label("total_minutes")
    ).filter(
        and_(
            StudySession.user_id == current_user.id,
            StudySession.session_date >= start_date
        )
    ).group_by(StudySession.course_name).all()
    
    courses = [
        {
            "course_name": stat.course_name,
            "session_count": stat.count,
            "total_minutes": stat.total_minutes or 0
        }
        for stat in course_stats
    ]
    
    return {
        "period_days": days,
        "total_sessions": total_sessions,
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 2),
        "sessions_per_week": sessions_per_week,
        "avg_session_duration_minutes": avg_duration,
        "courses": courses
    }


@router.get("/consistency")
def get_consistency_trends(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get consistency trends over time"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get sessions grouped by date
    daily_sessions = db.query(
        func.date(StudySession.session_date).label("date"),
        func.count(StudySession.id).label("count"),
        func.sum(StudySession.duration_minutes).label("total_minutes")
    ).filter(
        and_(
            StudySession.user_id == current_user.id,
            StudySession.session_date >= start_date
        )
    ).group_by(func.date(StudySession.session_date)).order_by("date").all()
    
    # Calculate consistency metrics
    days_with_sessions = len(daily_sessions)
    consistency_percentage = round((days_with_sessions / days) * 100, 2) if days > 0 else 0
    
    # Weekly breakdown
    weekly_data = {}
    for date_str, count, minutes in daily_sessions:
        date = datetime.strptime(str(date_str), "%Y-%m-%d").date()
        week_start = date - timedelta(days=date.weekday())
        week_key = week_start.isoformat()
        
        if week_key not in weekly_data:
            weekly_data[week_key] = {"sessions": 0, "minutes": 0, "days": 0}
        
        weekly_data[week_key]["sessions"] += count
        weekly_data[week_key]["minutes"] += minutes or 0
        weekly_data[week_key]["days"] += 1
    
    weekly_trends = [
        {
            "week_start": week_key,
            "sessions": data["sessions"],
            "total_minutes": data["minutes"],
            "days_active": data["days"]
        }
        for week_key, data in sorted(weekly_data.items())
    ]
    
    return {
        "period_days": days,
        "days_with_sessions": days_with_sessions,
        "consistency_percentage": consistency_percentage,
        "daily_data": [
            {
                "date": str(date_str),
                "sessions": count,
                "total_minutes": minutes or 0
            }
            for date_str, count, minutes in daily_sessions
        ],
        "weekly_trends": weekly_trends
    }


@router.get("/insights-data")
def get_insights_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get raw data for AI insights generation (for Person C)"""
    # Get last 60 days of data
    start_date = datetime.utcnow() - timedelta(days=60)
    
    sessions = db.query(StudySession).filter(
        and_(
            StudySession.user_id == current_user.id,
            StudySession.session_date >= start_date
        )
    ).order_by(StudySession.session_date.desc()).all()
    
    # Prepare data for AI processing
    sessions_data = [
        {
            "id": session.id,
            "course_name": session.course_name,
            "duration_minutes": session.duration_minutes,
            "session_date": session.session_date.isoformat(),
            "notes": session.notes
        }
        for session in sessions
    ]
    
    # Calculate basic stats
    total_sessions = len(sessions)
    total_minutes = sum(s.duration_minutes for s in sessions)
    courses = list(set(s.course_name for s in sessions))
    
    # Session frequency by day of week
    day_of_week_count = {}
    for session in sessions:
        day_name = session.session_date.strftime("%A")
        day_of_week_count[day_name] = day_of_week_count.get(day_name, 0) + 1
    
    return {
        "user_id": current_user.id,
        "period_days": 60,
        "total_sessions": total_sessions,
        "total_minutes": total_minutes,
        "courses": courses,
        "sessions": sessions_data,
        "day_of_week_distribution": day_of_week_count,
        "avg_session_duration": round(total_minutes / total_sessions, 2) if total_sessions > 0 else 0
    }

