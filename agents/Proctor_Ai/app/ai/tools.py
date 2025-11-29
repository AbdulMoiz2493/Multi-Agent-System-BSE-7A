"""
AI Agent Tools
Provides database access tools for the Gemini Agent to query student data
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from langchain_core.tools import tool

from app.models.user import User
from app.models.study_session import StudySession
from app.core.database import get_db


def map_student_id_to_user_id(student_id: str, db: Session) -> Optional[int]:
    """
    Map external student ID to internal user ID
    Handles formats like "STU_2709" -> user_id 2709
    """
    try:
        # Extract numeric part from student ID
        if "_" in student_id:
            numeric_id = int(student_id.split("_")[-1])
        else:
            numeric_id = int(student_id)
        
        # Check if user exists
        user = db.query(User).filter(User.id == numeric_id).first()
        if user:
            return user.id
    except (ValueError, AttributeError):
        pass
    
    return None


@tool
def get_student_study_sessions(student_id: str, days: int = 30) -> Dict[str, Any]:
    """
    Fetch study session logs for a student from the database.
    
    Args:
        student_id: The student ID (e.g., "STU_2709")
        days: Number of days to look back (default 30)
    
    Returns:
        Dictionary containing study sessions and statistics
    """
    # Get database session
    db = next(get_db())
    
    try:
        user_id = map_student_id_to_user_id(student_id, db)
        
        if not user_id:
            return {
                "success": False,
                "error": f"Student {student_id} not found in database",
                "sessions": []
            }
        
        # Fetch sessions
        start_date = datetime.utcnow() - timedelta(days=days)
        sessions = db.query(StudySession).filter(
            StudySession.user_id == user_id,
            StudySession.session_date >= start_date
        ).order_by(StudySession.session_date.desc()).all()
        
        # Format sessions
        session_data = []
        total_hours = 0
        subject_hours = {}
        
        for session in sessions:
            hours = session.duration_minutes / 60
            total_hours += hours
            
            subject = session.course_name
            subject_hours[subject] = subject_hours.get(subject, 0) + hours
            
            session_data.append({
                "date": session.session_date.strftime("%Y-%m-%d"),
                "subject": session.course_name,
                "hours": round(hours, 2),
                "duration_minutes": session.duration_minutes,
                "notes": session.notes
            })
        
        # Calculate statistics
        most_active_subject = max(subject_hours.items(), key=lambda x: x[1])[0] if subject_hours else None
        least_active_subject = min(subject_hours.items(), key=lambda x: x[1])[0] if len(subject_hours) > 1 else None
        
        return {
            "success": True,
            "student_id": student_id,
            "user_id": user_id,
            "period_days": days,
            "total_sessions": len(sessions),
            "total_hours": round(total_hours, 2),
            "sessions": session_data,
            "subject_distribution": {k: round(v, 2) for k, v in subject_hours.items()},
            "most_active_subject": most_active_subject,
            "least_active_subject": least_active_subject
        }
    
    finally:
        db.close()


@tool
def get_student_profile(student_id: str) -> Dict[str, Any]:
    """
    Fetch student profile information from the database.
    
    Args:
        student_id: The student ID (e.g., "STU_2709")
    
    Returns:
        Dictionary containing student profile data
    """
    db = next(get_db())
    
    try:
        user_id = map_student_id_to_user_id(student_id, db)
        
        if not user_id:
            return {
                "success": False,
                "error": f"Student {student_id} not found in database"
            }
        
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return {
                "success": False,
                "error": f"User data not found for {student_id}"
            }
        
        # Get all subjects the student has studied
        subjects = db.query(StudySession.course_name).filter(
            StudySession.user_id == user_id
        ).distinct().all()
        
        return {
            "success": True,
            "student_id": student_id,
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "student_id_internal": user.student_id,
            "subjects": [s[0] for s in subjects],
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    
    finally:
        db.close()


@tool
def calculate_consistency_score(student_id: str, days: int = 30) -> Dict[str, Any]:
    """
    Calculate the student's study consistency score.
    
    Args:
        student_id: The student ID (e.g., "STU_2709")
        days: Number of days to analyze (default 30)
    
    Returns:
        Dictionary containing consistency metrics
    """
    db = next(get_db())
    
    try:
        user_id = map_student_id_to_user_id(student_id, db)
        
        if not user_id:
            return {
                "success": False,
                "error": f"Student {student_id} not found"
            }
        
        start_date = datetime.utcnow() - timedelta(days=days)
        sessions = db.query(StudySession).filter(
            StudySession.user_id == user_id,
            StudySession.session_date >= start_date
        ).all()
        
        if not sessions:
            return {
                "success": True,
                "consistency_score": 0,
                "unique_study_days": 0,
                "total_days_analyzed": days
            }
        
        # Calculate unique study days
        unique_dates = set(s.session_date.date() for s in sessions)
        consistency_score = round((len(unique_dates) / days) * 100, 2)
        
        # Find gaps
        sorted_dates = sorted(unique_dates)
        gaps = []
        for i in range(len(sorted_dates) - 1):
            gap_days = (sorted_dates[i + 1] - sorted_dates[i]).days - 1
            if gap_days > 2:
                gaps.append({
                    "start": sorted_dates[i].isoformat(),
                    "end": sorted_dates[i + 1].isoformat(),
                    "days": gap_days
                })
        
        return {
            "success": True,
            "student_id": student_id,
            "consistency_score": consistency_score,
            "unique_study_days": len(unique_dates),
            "total_days_analyzed": days,
            "study_gaps": gaps[:5]  # Top 5 gaps
        }
    
    finally:
        db.close()


# List of all tools for the agent
AGENT_TOOLS = [
    get_student_study_sessions,
    get_student_profile,
    calculate_consistency_score
]

