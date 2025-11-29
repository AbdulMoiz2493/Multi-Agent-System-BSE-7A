"""
AI Reminder Service
Determines optimal reminder times and generates motivational messages
"""
from datetime import datetime, timedelta, time, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models.study_session import StudySession
from app.models.reminder import Reminder, ReminderStatus
from app.models.user import User
import random


class ReminderService:
    """Service for AI-powered reminder scheduling and message generation"""
    
    # Motivational messages pool
    MOTIVATIONAL_MESSAGES = [
        "Time to study! Every session brings you closer to your goals. 📚",
        "Don't break the streak! Your consistency matters. 💪",
        "Ready to learn something new today? Let's get started! 🚀",
        "Your future self will thank you for studying now! ⏰",
        "Small daily improvements lead to big results. Study time! 📖",
        "Stay focused, stay consistent. Time for your study session! 🎯",
        "Knowledge is power. Let's add to yours today! 💡",
        "You've got this! Time to hit the books. 📝",
        "Remember your goals! Time to make progress. 🌟",
        "Consistency is key to success. Ready to study? 🔑"
    ]
    
    WARNING_MESSAGES = [
        "You haven't studied in a while. Don't lose your momentum! ⚠️",
        "It's been {days} days since your last session. Time to get back on track! 🎯",
        "Your study streak is at risk! Let's resume your learning journey. 📚",
        "Missing study sessions? Let's change that today! 💪",
        "Your goals are waiting! Time to catch up on your studies. 🚀"
    ]
    
    SUBJECT_REMINDERS = [
        "Time to focus on {subject}! You've got this! 📖",
        "Don't forget about {subject}. Let's make some progress! 🎓",
        "{subject} needs your attention. Ready to dive in? 💡",
        "Let's tackle {subject} today! Every bit counts. 📝"
    ]
    
    @staticmethod
    def analyze_study_frequency(user_id: int, db: Session, days: int = 14) -> Dict[str, Any]:
        """Analyze user's study frequency and timing patterns"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        sessions = db.query(StudySession).filter(
            and_(
                StudySession.user_id == user_id,
                StudySession.session_date >= start_date
            )
        ).order_by(StudySession.session_date).all()
        
        if not sessions:
            return {
                "has_pattern": False,
                "average_interval_hours": 0,
                "preferred_hours": [],
                "preferred_days": [],
                "last_session_date": None,
                "days_since_last_session": None
            }
        
        # Calculate average interval between sessions
        intervals = []
        for i in range(len(sessions) - 1):
            interval = (sessions[i + 1].session_date - sessions[i].session_date).total_seconds() / 3600
            intervals.append(interval)
        
        avg_interval = sum(intervals) / len(intervals) if intervals else 0
        
        # Preferred study hours
        hour_counts = {}
        for session in sessions:
            hour = session.session_date.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        preferred_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        preferred_hours = [hour for hour, _ in preferred_hours]
        
        # Preferred days of week
        day_counts = {}
        for session in sessions:
            day = session.session_date.strftime("%A")
            day_counts[day] = day_counts.get(day, 0) + 1
        
        preferred_days = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        preferred_days = [day for day, _ in preferred_days]
        
        # Last session info
        last_session = sessions[-1]
        days_since_last = (datetime.now(timezone.utc) - last_session.session_date).days
        
        return {
            "has_pattern": len(sessions) >= 3,
            "average_interval_hours": round(avg_interval, 2),
            "preferred_hours": preferred_hours,
            "preferred_days": preferred_days,
            "last_session_date": last_session.session_date,
            "days_since_last_session": days_since_last,
            "total_sessions": len(sessions)
        }
    
    @staticmethod
    def determine_reminder_times(user_id: int, db: Session, 
                                   preferred_times: Optional[List[str]] = None) -> List[datetime]:
        """Determine optimal reminder times based on user patterns"""
        pattern = ReminderService.analyze_study_frequency(user_id, db)
        reminder_times = []
        
        # If user provided preferred times, use those
        if preferred_times:
            for time_str in preferred_times:
                try:
                    hour, minute = map(int, time_str.split(":"))
                    next_reminder = datetime.utcnow().replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if next_reminder < datetime.utcnow():
                        next_reminder += timedelta(days=1)
                    reminder_times.append(next_reminder)
                except:
                    pass
        
        # Use AI-determined times based on patterns
        elif pattern["has_pattern"] and pattern["preferred_hours"]:
            for hour in pattern["preferred_hours"][:2]:  # Top 2 preferred hours
                next_reminder = datetime.utcnow().replace(hour=hour, minute=0, second=0, microsecond=0)
                if next_reminder < datetime.utcnow():
                    next_reminder += timedelta(days=1)
                reminder_times.append(next_reminder)
        
        # Default times if no pattern exists
        else:
            default_hours = [19, 21]  # 7 PM and 9 PM
            for hour in default_hours:
                next_reminder = datetime.utcnow().replace(hour=hour, minute=0, second=0, microsecond=0)
                if next_reminder < datetime.utcnow():
                    next_reminder += timedelta(days=1)
                reminder_times.append(next_reminder)
        
        return reminder_times
    
    @staticmethod
    def generate_reminder_message(user_id: int, db: Session, 
                                   subject: Optional[str] = None) -> str:
        """Generate contextual reminder message"""
        pattern = ReminderService.analyze_study_frequency(user_id, db)
        
        # Warning if user hasn't studied recently
        if pattern["days_since_last_session"] and pattern["days_since_last_session"] > 3:
            message = random.choice(ReminderService.WARNING_MESSAGES)
            return message.format(days=pattern["days_since_last_session"])
        
        # Subject-specific reminder
        if subject:
            message = random.choice(ReminderService.SUBJECT_REMINDERS)
            return message.format(subject=subject)
        
        # General motivational message
        return random.choice(ReminderService.MOTIVATIONAL_MESSAGES)
    
    @staticmethod
    def should_send_reminder(user_id: int, db: Session) -> bool:
        """Determine if a reminder should be sent based on user activity"""
        pattern = ReminderService.analyze_study_frequency(user_id, db)
        
        # Send reminder if user hasn't studied in the last 24 hours
        if pattern["days_since_last_session"] is None:
            return True
        
        if pattern["days_since_last_session"] >= 1:
            return True
        
        # Check if it's been longer than average interval
        if pattern["average_interval_hours"] > 0:
            hours_since_last = (datetime.utcnow() - pattern["last_session_date"]).total_seconds() / 3600
            if hours_since_last >= pattern["average_interval_hours"]:
                return True
        
        return False
    
    @staticmethod
    def get_neglected_subjects(user_id: int, db: Session, days: int = 7) -> List[str]:
        """Identify subjects that haven't been studied recently"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all subjects user has ever studied
        all_subjects = db.query(StudySession.course_name).filter(
            StudySession.user_id == user_id
        ).distinct().all()
        all_subjects = [s[0] for s in all_subjects]
        
        # Get subjects studied in the last week
        recent_subjects = db.query(StudySession.course_name).filter(
            and_(
                StudySession.user_id == user_id,
                StudySession.session_date >= start_date
            )
        ).distinct().all()
        recent_subjects = [s[0] for s in recent_subjects]
        
        # Find neglected subjects
        neglected = [s for s in all_subjects if s not in recent_subjects]
        return neglected
    
    @staticmethod
    def create_reminder_schedule(user_id: int, db: Session, 
                                  days_ahead: int = 7,
                                  preferred_times: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Create a reminder schedule for the next N days"""
        schedule = []
        reminder_times = ReminderService.determine_reminder_times(user_id, db, preferred_times)
        neglected_subjects = ReminderService.get_neglected_subjects(user_id, db)
        
        # Create reminders for the next week
        for day_offset in range(days_ahead):
            for reminder_time in reminder_times:
                scheduled_time = reminder_time + timedelta(days=day_offset)
                
                # Choose subject to remind about
                subject = None
                if neglected_subjects and day_offset % 2 == 0:  # Alternate with neglected subjects
                    subject = random.choice(neglected_subjects)
                
                message = ReminderService.generate_reminder_message(user_id, db, subject)
                
                schedule.append({
                    "day": scheduled_time.strftime("%A"),
                    "time": scheduled_time.strftime("%I:%M %p"),
                    "datetime": scheduled_time,
                    "message": message,
                    "subject": subject
                })
        
        return schedule
