"""
AI Insights Service
Generates personalized study insights and recommendations based on user activity patterns
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models.study_session import StudySession
from app.models.user import User
from app.models.insight import Insight, InsightType


class InsightsService:
    """Service for generating AI-powered study insights"""
    
    @staticmethod
    def analyze_study_patterns(user_id: int, db: Session, days: int = 30) -> Dict[str, Any]:
        """Analyze user's study patterns over the specified period"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        sessions = db.query(StudySession).filter(
            and_(
                StudySession.user_id == user_id,
                StudySession.session_date >= start_date
            )
        ).order_by(StudySession.session_date).all()
        
        if not sessions:
            return {
                "total_sessions": 0,
                "total_hours": 0,
                "average_session_duration": 0,
                "consistency_score": 0,
                "most_active_subject": None,
                "least_active_subject": None,
                "peak_study_times": [],
                "study_gaps": [],
                "unique_study_days": 0
            }
        
        # Calculate basic metrics
        total_sessions = len(sessions)
        total_minutes = sum(s.duration_minutes for s in sessions)
        total_hours = round(total_minutes / 60, 2)
        avg_duration = round(total_minutes / total_sessions, 2)
        
        # Subject analysis
        subject_stats = {}
        for session in sessions:
            if session.course_name not in subject_stats:
                subject_stats[session.course_name] = {"count": 0, "minutes": 0}
            subject_stats[session.course_name]["count"] += 1
            subject_stats[session.course_name]["minutes"] += session.duration_minutes
        
        most_active = max(subject_stats.items(), key=lambda x: x[1]["minutes"])[0] if subject_stats else None
        least_active = min(subject_stats.items(), key=lambda x: x[1]["minutes"])[0] if len(subject_stats) > 1 else None
        
        # Time pattern analysis
        hour_distribution = {}
        for session in sessions:
            hour = session.session_date.hour
            hour_distribution[hour] = hour_distribution.get(hour, 0) + 1
        
        peak_hours = sorted(hour_distribution.items(), key=lambda x: x[1], reverse=True)[:3]
        peak_study_times = [f"{hour:02d}:00" for hour, _ in peak_hours]
        
        # Consistency analysis
        unique_dates = set(s.session_date.date() for s in sessions)
        consistency_score = round((len(unique_dates) / days) * 100, 2)
        
        # Find study gaps (days without sessions)
        study_gaps = []
        if len(sessions) > 1:
            for i in range(len(sessions) - 1):
                gap = (sessions[i + 1].session_date.date() - sessions[i].session_date.date()).days
                if gap > 3:  # Gap of more than 3 days
                    study_gaps.append({
                        "start_date": sessions[i].session_date.date().isoformat(),
                        "end_date": sessions[i + 1].session_date.date().isoformat(),
                        "days": gap
                    })
        
        return {
            "total_sessions": total_sessions,
            "total_hours": total_hours,
            "average_session_duration": avg_duration,
            "consistency_score": consistency_score,
            "most_active_subject": most_active,
            "least_active_subject": least_active,
            "subject_distribution": subject_stats,
            "peak_study_times": peak_study_times,
            "study_gaps": study_gaps[:5],  # Top 5 gaps
            "unique_study_days": len(unique_dates)
        }
    
    @staticmethod
    def generate_insights(user_id: int, db: Session) -> List[Dict[str, Any]]:
        """Generate personalized insights based on study patterns"""
        patterns = InsightsService.analyze_study_patterns(user_id, db)
        insights = []
        
        # Consistency insights
        if patterns["consistency_score"] >= 70:
            insights.append({
                "type": InsightType.CONSISTENCY,
                "title": "Excellent Consistency!",
                "message": f"You've been studying consistently {patterns['consistency_score']}% of the time. Keep up the great work!",
                "confidence_score": 90
            })
        elif patterns["consistency_score"] >= 40:
            insights.append({
                "type": InsightType.CONSISTENCY,
                "title": "Good Progress",
                "message": f"Your consistency score is {patterns['consistency_score']}%. Try to study a bit more regularly to improve.",
                "confidence_score": 75
            })
        else:
            insights.append({
                "type": InsightType.WARNING,
                "title": "Low Consistency",
                "message": f"Your consistency score is {patterns['consistency_score']}%. Consider setting a regular study schedule.",
                "confidence_score": 80
            })
        
        # Subject balance insights
        if patterns["most_active_subject"] and patterns["least_active_subject"]:
            insights.append({
                "type": InsightType.RECOMMENDATION,
                "title": "Subject Balance",
                "message": f"You're focusing heavily on {patterns['most_active_subject']}. Consider dedicating more time to {patterns['least_active_subject']}.",
                "confidence_score": 70
            })
        
        # Study gaps warning
        if patterns["study_gaps"]:
            longest_gap = max(patterns["study_gaps"], key=lambda x: x["days"])
            if longest_gap["days"] > 5:
                insights.append({
                    "type": InsightType.WARNING,
                    "title": "Study Gap Detected",
                    "message": f"You had a {longest_gap['days']}-day gap in studying. Try to maintain regular study sessions.",
                    "confidence_score": 85
                })
        
        # Session duration insights
        if patterns["average_session_duration"] < 30:
            insights.append({
                "type": InsightType.RECOMMENDATION,
                "title": "Short Study Sessions",
                "message": f"Your average session is {patterns['average_session_duration']} minutes. Consider longer, focused sessions for better retention.",
                "confidence_score": 65
            })
        elif patterns["average_session_duration"] > 120:
            insights.append({
                "type": InsightType.RECOMMENDATION,
                "title": "Long Study Sessions",
                "message": f"Your sessions average {patterns['average_session_duration']} minutes. Consider taking breaks to maintain focus.",
                "confidence_score": 70
            })
        
        # Peak time insight
        if patterns["peak_study_times"]:
            insights.append({
                "type": InsightType.PERFORMANCE,
                "title": "Optimal Study Times",
                "message": f"You study most effectively at {', '.join(patterns['peak_study_times'])}. Schedule important subjects during these times.",
                "confidence_score": 80
            })
        
        return insights
    
    @staticmethod
    def save_insights(user_id: int, db: Session) -> List[Insight]:
        """Generate and save insights to database"""
        insights_data = InsightsService.generate_insights(user_id, db)
        saved_insights = []
        
        for insight_data in insights_data:
            insight = Insight(
                user_id=user_id,
                insight_type=insight_data["type"],
                title=insight_data["title"],
                message=insight_data["message"],
                confidence_score=insight_data["confidence_score"]
            )
            db.add(insight)
            saved_insights.append(insight)
        
        db.commit()
        return saved_insights
