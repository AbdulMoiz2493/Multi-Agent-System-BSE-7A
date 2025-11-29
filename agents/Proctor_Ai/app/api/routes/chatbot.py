"""
Chatbot Integration API Routes
Allows chatbot to interact with the study tracking system
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List
import json

from app.core.database import get_db
from app.models.user import User
from app.models.study_session import StudySession
from app.models.chatbot_log import ChatbotLog, ChatbotActionType
from app.models.insight import Insight
from app.api.deps import get_current_user
from app.schemas.ai import (
    ChatbotLogStudyRequest,
    ChatbotStatusResponse,
    ChatbotTriggerReminderRequest,
    ChatbotInsightsResponse,
    InsightResponse
)
from app.ai.insights_service import InsightsService
from app.ai.reminder_service import ReminderService

router = APIRouter()


@router.post("/log-study", status_code=status.HTTP_201_CREATED)
def chatbot_log_study(
    request: ChatbotLogStudyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allow chatbot to log a study session for the user"""
    # Create study session
    session_date = request.session_date if request.session_date else datetime.now(timezone.utc)
    
    study_session = StudySession(
        user_id=current_user.id,
        course_name=request.course_name,
        duration_minutes=request.duration_minutes,
        session_date=session_date,
        notes=request.notes
    )
    db.add(study_session)
    
    # Log chatbot action
    chatbot_log = ChatbotLog(
        user_id=current_user.id,
        action_type=ChatbotActionType.LOG_STUDY.value,
        request_data=json.dumps(request.model_dump(), default=str),
        response_data=json.dumps({"session_id": study_session.id}, default=str)
    )
    db.add(chatbot_log)
    
    db.commit()
    db.refresh(study_session)
    
    return {
        "success": True,
        "message": f"Study session logged successfully for {request.course_name}",
        "session_id": study_session.id,
        "duration_minutes": request.duration_minutes,
        "session_date": study_session.session_date.isoformat()
    }


@router.get("/status", response_model=ChatbotStatusResponse)
def chatbot_get_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's current study status for chatbot"""
    # Get study pattern analysis
    pattern = ReminderService.analyze_study_frequency(current_user.id, db, days=30)
    
    # Get overall stats
    all_sessions = db.query(StudySession).filter(
        StudySession.user_id == current_user.id
    ).all()
    
    total_sessions = len(all_sessions)
    total_minutes = sum(s.duration_minutes for s in all_sessions)
    total_hours = round(total_minutes / 60, 2)
    
    # Calculate consistency score
    if all_sessions:
        last_30_days = datetime.now(timezone.utc) - timedelta(days=30)
        recent_sessions = [s for s in all_sessions if s.session_date >= last_30_days]
        unique_dates = set(s.session_date.date() for s in recent_sessions)
        consistency_score = round((len(unique_dates) / 30) * 100, 2)
    else:
        consistency_score = 0.0
    
    # Calculate current streak
    current_streak = 0
    if all_sessions:
        sorted_sessions = sorted(all_sessions, key=lambda x: x.session_date, reverse=True)
        current_date = datetime.now(timezone.utc).date()
        
        for i, session in enumerate(sorted_sessions):
            session_date = session.session_date.date()
            expected_date = current_date - timedelta(days=i)
            
            if session_date == expected_date or (i == 0 and (current_date - session_date).days <= 1):
                current_streak += 1
            else:
                break
    
    # Find top subject
    if all_sessions:
        subject_counts = {}
        for session in all_sessions:
            subject_counts[session.course_name] = subject_counts.get(session.course_name, 0) + session.duration_minutes
        top_subject = max(subject_counts.items(), key=lambda x: x[1])[0]
    else:
        top_subject = None
    
    # Log chatbot action
    chatbot_log = ChatbotLog(
        user_id=current_user.id,
        action_type=ChatbotActionType.GET_STATUS.value,
        request_data=json.dumps({"action": "get_status"}),
        response_data=json.dumps({
            "total_sessions": total_sessions,
            "consistency_score": consistency_score
        })
    )
    db.add(chatbot_log)
    db.commit()
    
    return ChatbotStatusResponse(
        user_id=current_user.id,
        total_sessions=total_sessions,
        total_hours=total_hours,
        consistency_score=consistency_score,
        last_session_date=pattern.get("last_session_date"),
        days_since_last_session=pattern.get("days_since_last_session"),
        current_streak=current_streak,
        top_subject=top_subject
    )


@router.post("/trigger-reminder")
def chatbot_trigger_reminder(
    request: ChatbotTriggerReminderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allow chatbot to trigger a study reminder"""
    # Generate reminder message
    if request.custom_message:
        message = request.custom_message
    else:
        message = ReminderService.generate_reminder_message(
            current_user.id, 
            db, 
            subject=request.subject
        )
    
    # Get optimal reminder time
    reminder_times = ReminderService.determine_reminder_times(current_user.id, db)
    next_reminder_time = reminder_times[0] if reminder_times else datetime.utcnow() + timedelta(hours=1)
    
    # Log chatbot action
    chatbot_log = ChatbotLog(
        user_id=current_user.id,
        action_type=ChatbotActionType.TRIGGER_REMINDER.value,
        request_data=json.dumps(request.model_dump(), default=str),
        response_data=json.dumps({
            "message": message,
            "scheduled_time": next_reminder_time.isoformat()
        }, default=str)
    )
    db.add(chatbot_log)
    db.commit()
    
    return {
        "success": True,
        "message": message,
        "scheduled_time": next_reminder_time.isoformat(),
        "subject": request.subject
    }


@router.get("/insights", response_model=ChatbotInsightsResponse)
def chatbot_get_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI-generated insights for chatbot to display"""
    # Generate fresh insights
    insights_data = InsightsService.generate_insights(current_user.id, db)
    
    # Get recent saved insights
    recent_insights = db.query(Insight).filter(
        Insight.user_id == current_user.id
    ).order_by(Insight.created_at.desc()).limit(5).all()
    
    # Combine fresh and recent insights
    all_insights = []
    
    # Add fresh insights as InsightResponse objects
    for insight in insights_data:
        all_insights.append(InsightResponse(
            id=0,  # Temporary ID for fresh insights
            user_id=current_user.id,
            insight_type=insight["type"],
            title=insight["title"],
            message=insight["message"],
            confidence_score=insight["confidence_score"],
            created_at=datetime.utcnow()
        ))
    
    # Generate summary
    if insights_data:
        summary = f"I've analyzed your study patterns and found {len(insights_data)} insights. "
        high_confidence = [i for i in insights_data if i["confidence_score"] >= 80]
        if high_confidence:
            summary += f"{len(high_confidence)} of them are highly relevant to your current situation."
    else:
        summary = "Keep studying consistently, and I'll be able to provide personalized insights soon!"
    
    # Log chatbot action
    chatbot_log = ChatbotLog(
        user_id=current_user.id,
        action_type=ChatbotActionType.GET_INSIGHTS.value,
        request_data=json.dumps({"action": "get_insights"}),
        response_data=json.dumps({"insights_count": len(insights_data)})
    )
    db.add(chatbot_log)
    db.commit()
    
    return ChatbotInsightsResponse(
        insights=all_insights,
        summary=summary
    )


@router.get("/activity-summary")
def chatbot_get_activity_summary(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a quick activity summary for chatbot conversations"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    sessions = db.query(StudySession).filter(
        StudySession.user_id == current_user.id,
        StudySession.session_date >= start_date
    ).all()
    
    total_minutes = sum(s.duration_minutes for s in sessions)
    subjects = list(set(s.course_name for s in sessions))
    
    return {
        "period_days": days,
        "total_sessions": len(sessions),
        "total_hours": round(total_minutes / 60, 2),
        "subjects_studied": subjects,
        "average_daily_hours": round((total_minutes / 60) / days, 2) if days > 0 else 0,
        "summary_text": f"In the last {days} days, you've completed {len(sessions)} study sessions totaling {round(total_minutes / 60, 1)} hours across {len(subjects)} subjects."
    }
