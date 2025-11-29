"""
AI-powered Analytics and Insights API Routes
Provides AI-generated insights and advanced analytics
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.models.insight import Insight
from app.api.deps import get_current_user
from app.schemas.ai import (
    InsightResponse,
    InsightGenerateRequest,
    StudyPatternAnalysis,
    ReminderScheduleRequest,
    ReminderScheduleResponse,
    ReminderScheduleItem
)
from app.ai.insights_service import InsightsService
from app.ai.reminder_service import ReminderService

router = APIRouter()


@router.post("/generate-insights", response_model=List[InsightResponse])
def generate_insights(
    request: InsightGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate AI-powered insights based on user's study patterns
    Analyzes recent activity and provides personalized recommendations
    """
    # Save insights to database
    insights = InsightsService.save_insights(current_user.id, db)
    
    return [
        InsightResponse(
            id=insight.id,
            user_id=insight.user_id,
            insight_type=insight.insight_type,
            title=insight.title,
            message=insight.message,
            confidence_score=insight.confidence_score,
            created_at=insight.created_at
        )
        for insight in insights
    ]


@router.get("/insights", response_model=List[InsightResponse])
def get_insights(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of insights to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get previously generated insights for the user"""
    insights = db.query(Insight).filter(
        Insight.user_id == current_user.id
    ).order_by(Insight.created_at.desc()).limit(limit).all()
    
    return [
        InsightResponse(
            id=insight.id,
            user_id=insight.user_id,
            insight_type=insight.insight_type,
            title=insight.title,
            message=insight.message,
            confidence_score=insight.confidence_score,
            created_at=insight.created_at
        )
        for insight in insights
    ]


@router.get("/study-patterns", response_model=StudyPatternAnalysis)
def analyze_study_patterns(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed study pattern analysis
    Includes consistency scores, subject distribution, peak study times, etc.
    """
    patterns = InsightsService.analyze_study_patterns(current_user.id, db, days)
    
    if not patterns.get("total_sessions"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access study pattern analysis because there is not enough data. No study sessions found for the selected period."
        )

    return StudyPatternAnalysis(
        total_sessions=patterns["total_sessions"],
        total_hours=patterns["total_hours"],
        average_session_duration=patterns["average_session_duration"],
        consistency_score=patterns["consistency_score"],
        most_active_subject=patterns["most_active_subject"],
        least_active_subject=patterns["least_active_subject"],
        subject_distribution=patterns.get("subject_distribution", {}),
        peak_study_times=patterns.get("peak_study_times", []),
        study_gaps=patterns.get("study_gaps", []),
        unique_study_days=patterns.get("unique_study_days", 0)
    )


@router.post("/reminder-schedule", response_model=ReminderScheduleResponse)
def create_reminder_schedule(
    request: ReminderScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate an AI-powered reminder schedule based on user's study patterns
    Takes into account preferred times and historical patterns
    """
    schedule = ReminderService.create_reminder_schedule(
        current_user.id,
        db,
        days_ahead=request.days_ahead,
        preferred_times=request.preferred_times
    )
    
    schedule_items = [
        ReminderScheduleItem(
            day=item["day"],
            time=item["time"],
            datetime=item["datetime"],
            message=item["message"],
            subject=item["subject"]
        )
        for item in schedule
    ]
    
    return ReminderScheduleResponse(
        user_id=current_user.id,
        schedule=schedule_items,
        total_reminders=len(schedule_items)
    )


@router.get("/optimal-study-times")
def get_optimal_study_times(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI-recommended optimal study times based on user's historical patterns
    """
    pattern = ReminderService.analyze_study_frequency(current_user.id, db)
    
    return {
        "user_id": current_user.id,
        "has_established_pattern": pattern["has_pattern"],
        "preferred_hours": pattern["preferred_hours"],
        "preferred_days": pattern["preferred_days"],
        "recommended_times": [
            f"{hour:02d}:00" for hour in pattern["preferred_hours"]
        ] if pattern["preferred_hours"] else ["19:00", "21:00"],
        "confidence": "high" if pattern["has_pattern"] else "low"
    }


@router.get("/neglected-subjects")
def get_neglected_subjects(
    days: int = Query(7, ge=1, le=30, description="Days to look back"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Identify subjects that haven't been studied recently
    Helps users maintain balanced study across all subjects
    """
    neglected = ReminderService.get_neglected_subjects(current_user.id, db, days)
    
    return {
        "user_id": current_user.id,
        "period_days": days,
        "neglected_subjects": neglected,
        "count": len(neglected),
        "recommendation": f"Consider studying {', '.join(neglected[:2])} soon" if neglected else "All subjects are up to date!"
    }


@router.get("/should-study-now")
def should_study_now(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI decision on whether user should study now based on their patterns
    """
    should_send = ReminderService.should_send_reminder(current_user.id, db)
    pattern = ReminderService.analyze_study_frequency(current_user.id, db)
    
    message = ""
    if should_send:
        if pattern["days_since_last_session"] and pattern["days_since_last_session"] > 2:
            message = f"Yes! You haven't studied in {pattern['days_since_last_session']} days. Time to get back on track!"
        else:
            message = "Yes! Based on your usual study pattern, now is a good time to study."
    else:
        message = "You're doing great! You've been studying consistently. Take a break if needed."
    
    return {
        "should_study": should_send,
        "message": message,
        "days_since_last_session": pattern["days_since_last_session"],
        "last_session_date": pattern["last_session_date"].isoformat() if pattern["last_session_date"] else None
    }


@router.get("/study-recommendations")
def get_study_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive AI-powered study recommendations
    """
    patterns = InsightsService.analyze_study_patterns(current_user.id, db)
    insights = InsightsService.generate_insights(current_user.id, db)
    neglected = ReminderService.get_neglected_subjects(current_user.id, db)
    
    recommendations = []
    
    # Add insights as recommendations
    for insight in insights:
        if insight["type"].value in ["recommendation", "warning"]:
            recommendations.append({
                "type": insight["type"].value,
                "priority": "high" if insight["confidence_score"] >= 80 else "medium",
                "title": insight["title"],
                "message": insight["message"]
            })
    
    # Add neglected subjects recommendation
    if neglected:
        recommendations.append({
            "type": "subject_balance",
            "priority": "medium",
            "title": "Neglected Subjects",
            "message": f"Consider studying: {', '.join(neglected)}"
        })
    
    # Add study time recommendations
    if patterns["peak_study_times"]:
        recommendations.append({
            "type": "timing",
            "priority": "low",
            "title": "Optimal Study Times",
            "message": f"You study best at: {', '.join(patterns['peak_study_times'])}"
        })
    
    return {
        "user_id": current_user.id,
        "total_recommendations": len(recommendations),
        "recommendations": recommendations,
        "generated_at": datetime.utcnow().isoformat()
    }
