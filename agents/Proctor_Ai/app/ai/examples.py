"""
Example usage scripts for AI Agent functionality
Demonstrates how to use the AI services and API endpoints
"""

from datetime import datetime, timedelta
from app.ai.insights_service import InsightsService
from app.ai.reminder_service import ReminderService


def example_generate_insights(user_id: int, db):
    """Example: Generate AI insights for a user"""
    print("=" * 60)
    print("GENERATING AI INSIGHTS")
    print("=" * 60)
    
    # Generate insights
    insights = InsightsService.generate_insights(user_id, db)
    
    print(f"\nGenerated {len(insights)} insights:\n")
    for i, insight in enumerate(insights, 1):
        print(f"{i}. [{insight['type'].value.upper()}] {insight['title']}")
        print(f"   {insight['message']}")
        print(f"   Confidence: {insight['confidence_score']}%\n")
    
    return insights


def example_analyze_study_patterns(user_id: int, db, days: int = 30):
    """Example: Analyze user study patterns"""
    print("=" * 60)
    print(f"ANALYZING STUDY PATTERNS (Last {days} days)")
    print("=" * 60)
    
    patterns = InsightsService.analyze_study_patterns(user_id, db, days)
    
    print(f"\n📊 Study Statistics:")
    print(f"   Total Sessions: {patterns['total_sessions']}")
    print(f"   Total Hours: {patterns['total_hours']:.2f}")
    print(f"   Average Session: {patterns['average_session_duration']:.0f} minutes")
    print(f"   Consistency Score: {patterns['consistency_score']:.1f}%")
    print(f"   Study Days: {patterns['unique_study_days']}/{days}")
    
    if patterns['most_active_subject']:
        print(f"\n📚 Subject Activity:")
        print(f"   Most Active: {patterns['most_active_subject']}")
        if patterns['least_active_subject']:
            print(f"   Least Active: {patterns['least_active_subject']}")
    
    if patterns['peak_study_times']:
        print(f"\n⏰ Peak Study Times:")
        for time in patterns['peak_study_times']:
            print(f"   - {time}")
    
    if patterns['study_gaps']:
        print(f"\n⚠️  Study Gaps Detected:")
        for gap in patterns['study_gaps'][:3]:
            print(f"   - {gap['days']} days ({gap['start_date']} to {gap['end_date']})")
    
    return patterns


def example_create_reminder_schedule(user_id: int, db, days: int = 7):
    """Example: Create AI-powered reminder schedule"""
    print("=" * 60)
    print(f"CREATING REMINDER SCHEDULE ({days} days)")
    print("=" * 60)
    
    schedule = ReminderService.create_reminder_schedule(
        user_id, 
        db, 
        days_ahead=days,
        preferred_times=["19:00", "21:00"]
    )
    
    print(f"\n📅 Reminder Schedule ({len(schedule)} reminders):\n")
    
    current_day = None
    for item in schedule:
        if item['day'] != current_day:
            current_day = item['day']
            print(f"\n{current_day}:")
        
        subject = f" - {item['subject']}" if item['subject'] else ""
        print(f"  {item['time']}{subject}")
        print(f"    💬 {item['message']}")
    
    return schedule


def example_check_study_recommendation(user_id: int, db):
    """Example: Check if user should study now"""
    print("=" * 60)
    print("SHOULD STUDY NOW CHECK")
    print("=" * 60)
    
    should_send = ReminderService.should_send_reminder(user_id, db)
    pattern = ReminderService.analyze_study_frequency(user_id, db)
    
    print(f"\n🤔 Recommendation: {'YES, STUDY NOW!' if should_send else 'Take a break'}")
    
    if pattern['last_session_date']:
        print(f"\n📅 Last Study Session:")
        print(f"   Date: {pattern['last_session_date'].strftime('%Y-%m-%d %H:%M')}")
        print(f"   Days Ago: {pattern['days_since_last_session']}")
    
    if pattern['has_pattern']:
        print(f"\n📈 Study Pattern Detected:")
        print(f"   Average Interval: {pattern['average_interval_hours']:.1f} hours")
        print(f"   Preferred Times: {', '.join([f'{h}:00' for h in pattern['preferred_hours']])}")
    
    return should_send


def example_get_neglected_subjects(user_id: int, db, days: int = 7):
    """Example: Identify neglected subjects"""
    print("=" * 60)
    print(f"NEGLECTED SUBJECTS (Last {days} days)")
    print("=" * 60)
    
    neglected = ReminderService.get_neglected_subjects(user_id, db, days)
    
    if neglected:
        print(f"\n⚠️  {len(neglected)} subject(s) need attention:\n")
        for i, subject in enumerate(neglected, 1):
            print(f"   {i}. {subject}")
        print(f"\n💡 Recommendation: Schedule study sessions for these subjects soon!")
    else:
        print("\n✅ All subjects are up to date!")
    
    return neglected


def example_supervisor_analysis(student_id: str, user_id: int, db):
    """Example: Supervisor agent analysis"""
    print("=" * 60)
    print(f"SUPERVISOR ANALYSIS - Student {student_id}")
    print("=" * 60)
    
    # Analyze patterns
    patterns = InsightsService.analyze_study_patterns(user_id, db, 30)
    insights = InsightsService.generate_insights(user_id, db)
    
    # Create analysis summary
    print(f"\n📊 Analysis Summary:")
    print(f"   Total Study Hours: {patterns['total_hours']:.1f}")
    print(f"   Total Sessions: {patterns['total_sessions']}")
    print(f"   Consistency Score: {patterns['consistency_score']:.0f}/100")
    
    if patterns['most_active_subject']:
        print(f"   Most Active Subject: {patterns['most_active_subject']}")
        if patterns['least_active_subject']:
            print(f"   Least Active Subject: {patterns['least_active_subject']}")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    high_priority = [i for i in insights if i['confidence_score'] >= 75]
    for i, insight in enumerate(high_priority[:3], 1):
        print(f"   {i}. {insight['message']}")
    
    # Performance alerts
    print(f"\n⚠️  Performance Alerts:")
    if patterns['consistency_score'] < 50:
        print(f"   - Low consistency detected ({patterns['consistency_score']:.0f}%)")
    if patterns['study_gaps']:
        longest_gap = max(patterns['study_gaps'], key=lambda x: x['days'])
        print(f"   - Study gap of {longest_gap['days']} days detected")
    
    if not (patterns['consistency_score'] < 50 or patterns['study_gaps']):
        print(f"   ✅ No alerts - student is performing well")
    
    # Engagement level
    engagement = "High" if patterns['consistency_score'] > 70 else \
                "Medium" if patterns['consistency_score'] > 40 else "Low"
    
    print(f"\n🎯 Engagement Level: {engagement}")
    
    return {
        "patterns": patterns,
        "insights": insights,
        "engagement": engagement
    }


# Example API request payloads
EXAMPLE_CHATBOT_LOG_STUDY = {
    "course_name": "Operating Systems",
    "duration_minutes": 60,
    "notes": "Studied process scheduling and CPU algorithms"
}

EXAMPLE_CHATBOT_TRIGGER_REMINDER = {
    "subject": "Data Structures",
    "custom_message": None
}

EXAMPLE_SUPERVISOR_REQUEST = {
    "student_id": "STU_2709",
    "profile": {
        "name": "Sumair Ali",
        "program": "BS Computer Science",
        "semester": 7,
        "subjects": ["Operating Systems", "Software Management", "AI Fundamentals"]
    },
    "study_schedule": {
        "preferred_times": ["7:00 PM", "9:00 PM"],
        "daily_goal_hours": 2
    },
    "activity_log": [
        {"date": "2025-09-25", "subject": "Operating Systems", "hours": 2, "status": "completed"},
        {"date": "2025-09-26", "subject": "AI Fundamentals", "hours": 1, "status": "partial"},
        {"date": "2025-09-27", "subject": "Operating Systems", "hours": 2, "status": "completed"}
    ],
    "user_feedback": {
        "reminder_effectiveness": 4,
        "motivation_level": "medium"
    },
    "context": {
        "request_type": "analyze_revision_pattern",
        "supervisor_id": "SUP_001",
        "priority": "medium"
    }
}


if __name__ == "__main__":
    print("AI Agent Example Scripts")
    print("========================\n")
    print("Import these functions in your code to test AI functionality:")
    print("- example_generate_insights(user_id, db)")
    print("- example_analyze_study_patterns(user_id, db, days=30)")
    print("- example_create_reminder_schedule(user_id, db, days=7)")
    print("- example_check_study_recommendation(user_id, db)")
    print("- example_get_neglected_subjects(user_id, db, days=7)")
    print("- example_supervisor_analysis(student_id, user_id, db)")
