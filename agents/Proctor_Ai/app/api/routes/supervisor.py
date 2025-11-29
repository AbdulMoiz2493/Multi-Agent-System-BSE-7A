"""
Supervisor Agent Integration API Routes
Provides interface for external supervisor agent to analyze student study patterns
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from app.core.database import get_db
from app.models.user import User
from app.models.study_session import StudySession
from app.api.deps import get_current_user
from app.schemas.ai import (
    SupervisorAgentRequest,
    SupervisorAgentResponse,
    SupervisorAnalysisSummary,
    SupervisorReminderScheduleItem,
    SupervisorPerformanceAlert,
    SupervisorReportSummary
)
from app.ai.insights_service import InsightsService
from app.ai.reminder_service import ReminderService
from app.ai.gemini_agent import GeminiRevisionAgent

router = APIRouter()

# Initialize the Gemini Agent (singleton)
try:
    gemini_agent = GeminiRevisionAgent()
except ValueError as e:
    # If GEMINI_API_KEY is not set, agent will be None and we'll use fallback logic
    gemini_agent = None
    print(f"Warning: Gemini Agent not initialized: {e}")


def map_student_id_to_user_id(student_id: str, db: Session) -> int:
    """
    Map external student ID to internal user ID
    In production, this would use a proper mapping table
    For now, we'll extract the numeric part or use current user
    """
    # This is a simplified version - in production you'd have a proper mapping
    try:
        # Extract numeric part from student ID (e.g., "STU_2709" -> 2709)
        numeric_id = int(student_id.split("_")[-1])
        # Check if user exists
        user = db.query(User).filter(User.id == numeric_id).first()
        if user:
            return user.id
    except:
        pass
    
    # Fallback: return None if mapping fails
    return None


@router.post("/analyze", response_model=SupervisorAgentResponse)
def supervisor_analyze_student(
    request: SupervisorAgentRequest,
    db: Session = Depends(get_db)
):
    """
    Main endpoint for supervisor agent to analyze student study patterns
    Uses Gemini AI Agent for intelligent analysis and recommendations
    """
    # Use Gemini Agent if available
    if gemini_agent:
        try:
            return gemini_agent.analyze_student(request, db)
        except Exception as e:
            print(f"Gemini Agent error: {e}. Falling back to rule-based analysis.")
            # Fall through to fallback logic
    
    # Fallback: Rule-based analysis (original implementation)
    user_id = map_student_id_to_user_id(request.student_id, db)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student {request.student_id} not found in the system"
        )
    
    # Analyze study patterns
    patterns = InsightsService.analyze_study_patterns(user_id, db, days=30)
    
    # Get insights
    insights = InsightsService.generate_insights(user_id, db)
    
    # Generate recommendations based on activity log and patterns
    recommendations = _generate_recommendations(request, patterns, insights)
    
    # Create reminder schedule
    reminder_schedule = _create_reminder_schedule(
        user_id, 
        db, 
        request.study_schedule.preferred_times
    )
    
    # Generate performance alerts
    alerts = _generate_performance_alerts(request, patterns)
    
    # Calculate week summary
    week_summary = _calculate_week_summary(request, patterns)
    
    # Build analysis summary
    analysis_summary = SupervisorAnalysisSummary(
        total_study_hours=patterns["total_hours"],
        average_completion_rate=_calculate_completion_rate(request),
        most_active_subject=patterns["most_active_subject"] or "N/A",
        least_active_subject=patterns["least_active_subject"]
    )
    
    return SupervisorAgentResponse(
        student_id=request.student_id,
        analysis_summary=analysis_summary,
        recommendations=recommendations,
        reminder_schedule=reminder_schedule,
        performance_alerts=alerts,
        report_summary=week_summary
    )


@router.get("/student-trends/{student_id}")
def get_student_trends(
    student_id: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get summarized study trends for a student (lightweight for supervisor)"""
    user_id = map_student_id_to_user_id(student_id, db)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student {student_id} not found"
        )
    
    patterns = InsightsService.analyze_study_patterns(user_id, db, days)
    
    return {
        "student_id": student_id,
        "period_days": days,
        "total_study_hours": patterns["total_hours"],
        "total_sessions": patterns["total_sessions"],
        "consistency_score": patterns["consistency_score"],
        "most_active_subject": patterns["most_active_subject"],
        "average_session_duration": patterns["average_session_duration"],
        "unique_study_days": patterns["unique_study_days"]
    }


@router.get("/engagement-metrics/{student_id}")
def get_engagement_metrics(
    student_id: str,
    db: Session = Depends(get_db)
):
    """Get anonymized engagement metrics for supervisor dashboard"""
    user_id = map_student_id_to_user_id(student_id, db)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student {student_id} not found"
        )
    
    # Get 30-day patterns
    patterns = InsightsService.analyze_study_patterns(user_id, db, 30)
    
    # Calculate engagement level
    engagement_level = "High" if patterns["consistency_score"] > 70 else \
                      "Medium" if patterns["consistency_score"] > 40 else "Low"
    
    # Check for at-risk indicators
    at_risk = patterns["consistency_score"] < 30 or \
              (patterns["study_gaps"] and len(patterns["study_gaps"]) > 2)
    
    return {
        "student_id": student_id,
        "engagement_level": engagement_level,
        "consistency_score": patterns["consistency_score"],
        "total_sessions_30d": patterns["total_sessions"],
        "total_hours_30d": patterns["total_hours"],
        "at_risk": at_risk,
        "last_activity_days_ago": _get_days_since_last_activity(user_id, db)
    }


def _generate_recommendations(
    request: SupervisorAgentRequest, 
    patterns: Dict[str, Any],
    insights: List[Dict[str, Any]]
) -> List[str]:
    """Generate recommendations based on analysis"""
    recommendations = []
    
    # Analyze activity log completion rates
    if request.activity_log:
        partial_sessions = [log for log in request.activity_log if log.status == "partial"]
        if len(partial_sessions) > len(request.activity_log) * 0.3:
            recommendations.append("Focus on completing full study sessions rather than partial ones.")
    
    # Subject balance recommendation
    if patterns["least_active_subject"] and patterns["most_active_subject"]:
        recommendations.append(
            f"Add one more revision session for {patterns['least_active_subject']}."
        )
        recommendations.append(
            f"Continue current schedule for {patterns['most_active_subject']}."
        )
    
    # Consistency recommendation
    if patterns["consistency_score"] < 50:
        recommendations.append("Try to establish a more consistent daily study routine.")
    elif patterns["consistency_score"] > 80:
        recommendations.append("Excellent consistency! Maintain your current schedule.")
    
    # Study duration recommendation
    if patterns["average_session_duration"] < 30:
        recommendations.append("Consider longer study sessions (45-60 minutes) for better retention.")
    
    # Gap-based recommendation
    if patterns["study_gaps"]:
        recommendations.append("Minimize gaps between study sessions to maintain momentum.")
    
    return recommendations[:5]  # Return top 5 recommendations


def _create_reminder_schedule(
    user_id: int, 
    db: Session, 
    preferred_times: List[str]
) -> List[SupervisorReminderScheduleItem]:
    """Create reminder schedule based on preferred times"""
    schedule_items = ReminderService.determine_reminder_times(user_id, db, preferred_times)
    
    result = []
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    # Create weekly schedule
    for i, day in enumerate(days):
        if i < len(preferred_times):
            result.append(SupervisorReminderScheduleItem(
                day=day,
                time=preferred_times[i % len(preferred_times)]
            ))
    
    return result[:7]  # Return one week schedule


def _generate_performance_alerts(
    request: SupervisorAgentRequest,
    patterns: Dict[str, Any]
) -> List[SupervisorPerformanceAlert]:
    """Generate performance alerts based on patterns"""
    alerts = []
    
    # Check for missed sessions
    if request.activity_log:
        # Count consecutive missed/partial sessions
        recent_statuses = [log.status for log in request.activity_log[-5:]]
        missed_count = sum(1 for s in recent_statuses if s in ["partial", "missed"])
        
        if missed_count >= 2:
            alerts.append(SupervisorPerformanceAlert(
                type="warning",
                message=f"Missed {missed_count} consecutive study sessions."
            ))
    
    # Check consistency
    if patterns["consistency_score"] < 30:
        alerts.append(SupervisorPerformanceAlert(
            type="critical",
            message="Very low consistency score. Immediate attention needed."
        ))
    elif patterns["consistency_score"] < 50:
        alerts.append(SupervisorPerformanceAlert(
            type="warning",
            message="Below-average consistency. Consider setting reminders."
        ))
    
    # Check study gaps
    if patterns["study_gaps"]:
        longest_gap = max(patterns["study_gaps"], key=lambda x: x["days"])
        if longest_gap["days"] > 7:
            alerts.append(SupervisorPerformanceAlert(
                type="warning",
                message=f"Long study gap detected: {longest_gap['days']} days without studying."
            ))
    
    # Check if no alerts, add positive feedback
    if not alerts:
        alerts.append(SupervisorPerformanceAlert(
            type="success",
            message="Student is performing well with consistent study habits."
        ))
    
    return alerts


def _calculate_week_summary(
    request: SupervisorAgentRequest,
    patterns: Dict[str, Any]
) -> SupervisorReportSummary:
    """Calculate weekly report summary"""
    # Determine date range from activity log
    if request.activity_log:
        try:
            dates = [datetime.strptime(log.date, "%Y-%m-%d") for log in request.activity_log]
            start_date = min(dates)
            end_date = max(dates)
            week_str = f"{start_date.strftime('%b %d')}–{end_date.strftime('%b %d')}"
        except ValueError:
            # Invalid date format, use default
            week_str = "Current Week"
    else:
        week_str = "Current Week"
    
    # Calculate consistency score (0-100)
    consistency_score = int(patterns["consistency_score"])
    
    # Determine engagement level
    if consistency_score >= 70 and patterns["total_hours"] >= 10:
        engagement_level = "High"
    elif consistency_score >= 40 and patterns["total_hours"] >= 5:
        engagement_level = "Medium"
    else:
        engagement_level = "Low"
    
    return SupervisorReportSummary(
        week=week_str,
        consistency_score=consistency_score,
        engagement_level=engagement_level
    )


def _calculate_completion_rate(request: SupervisorAgentRequest) -> str:
    """Calculate average completion rate from activity log"""
    if not request.activity_log:
        return "N/A"
    
    completed = sum(1 for log in request.activity_log if log.status == "completed")
    total = len(request.activity_log)
    
    if total == 0:
        return "0%"
    
    percentage = (completed / total) * 100
    return f"{percentage:.0f}%"


def _get_days_since_last_activity(user_id: int, db: Session) -> int:
    """Get number of days since last study session"""
    last_session = db.query(StudySession).filter(
        StudySession.user_id == user_id
    ).order_by(StudySession.session_date.desc()).first()
    
    if not last_session:
        return -1  # No activity
    
    return (datetime.now(timezone.utc) - last_session.session_date).days
