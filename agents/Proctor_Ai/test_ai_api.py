"""
Python test script for AI Agent endpoints
Run this after starting the server to test all AI functionality
"""
import requests
import json
from datetime import datetime


BASE_URL = "http://localhost:8000/api"
TOKEN = "your_jwt_token_here"  # Replace with actual token


def get_headers(include_auth=True):
    """Get request headers"""
    headers = {"Content-Type": "application/json"}
    if include_auth:
        headers["Authorization"] = f"Bearer {TOKEN}"
    return headers


def test_ai_insights():
    """Test AI insights endpoints"""
    print("\n" + "="*60)
    print("TESTING AI INSIGHTS ENDPOINTS")
    print("="*60)
    
    # Generate insights
    print("\n1. Generating AI Insights...")
    response = requests.post(
        f"{BASE_URL}/ai/generate-insights",
        headers=get_headers(),
        json={"days_back": 30}
    )
    print(f"Status: {response.status_code}")
    if response.ok:
        insights = response.json()
        print(f"Generated {len(insights)} insights")
        for insight in insights[:3]:
            print(f"  - [{insight['insight_type']}] {insight['title']}")
    
    # Get insights
    print("\n2. Getting Previous Insights...")
    response = requests.get(
        f"{BASE_URL}/ai/insights?limit=5",
        headers=get_headers()
    )
    print(f"Status: {response.status_code}")
    if response.ok:
        insights = response.json()
        print(f"Found {len(insights)} insights")
    
    # Study patterns
    print("\n3. Analyzing Study Patterns...")
    response = requests.get(
        f"{BASE_URL}/ai/study-patterns?days=30",
        headers=get_headers()
    )
    print(f"Status: {response.status_code}")
    if response.ok:
        patterns = response.json()
        print(f"  Total Sessions: {patterns['total_sessions']}")
        print(f"  Consistency Score: {patterns['consistency_score']:.1f}%")
        print(f"  Most Active Subject: {patterns.get('most_active_subject', 'N/A')}")


def test_reminder_features():
    """Test reminder-related endpoints"""
    print("\n" + "="*60)
    print("TESTING REMINDER ENDPOINTS")
    print("="*60)
    
    # Create reminder schedule
    print("\n1. Creating Reminder Schedule...")
    response = requests.post(
        f"{BASE_URL}/ai/reminder-schedule",
        headers=get_headers(),
        json={
            "days_ahead": 7,
            "preferred_times": ["19:00", "21:00"]
        }
    )
    print(f"Status: {response.status_code}")
    if response.ok:
        schedule = response.json()
        print(f"Created schedule with {schedule['total_reminders']} reminders")
    
    # Get optimal study times
    print("\n2. Getting Optimal Study Times...")
    response = requests.get(
        f"{BASE_URL}/ai/optimal-study-times",
        headers=get_headers()
    )
    print(f"Status: {response.status_code}")
    if response.ok:
        times = response.json()
        print(f"  Preferred times: {times.get('recommended_times', [])}")
        print(f"  Confidence: {times.get('confidence', 'N/A')}")
    
    # Check if should study now
    print("\n3. Should Study Now Check...")
    response = requests.get(
        f"{BASE_URL}/ai/should-study-now",
        headers=get_headers()
    )
    print(f"Status: {response.status_code}")
    if response.ok:
        result = response.json()
        print(f"  Should Study: {result['should_study']}")
        print(f"  Message: {result['message']}")
    
    # Get neglected subjects
    print("\n4. Getting Neglected Subjects...")
    response = requests.get(
        f"{BASE_URL}/ai/neglected-subjects?days=7",
        headers=get_headers()
    )
    print(f"Status: {response.status_code}")
    if response.ok:
        result = response.json()
        print(f"  Found {result['count']} neglected subjects")
        if result['neglected_subjects']:
            print(f"  Subjects: {', '.join(result['neglected_subjects'])}")


def test_chatbot_integration():
    """Test chatbot integration endpoints"""
    print("\n" + "="*60)
    print("TESTING CHATBOT INTEGRATION")
    print("="*60)
    
    # Log study session
    print("\n1. Logging Study Session via Chatbot...")
    response = requests.post(
        f"{BASE_URL}/chatbot/log-study",
        headers=get_headers(),
        json={
            "course_name": "Operating Systems",
            "duration_minutes": 60,
            "notes": "Studied CPU scheduling algorithms"
        }
    )
    print(f"Status: {response.status_code}")
    if response.ok:
        result = response.json()
        print(f"  Success: {result['success']}")
        print(f"  Message: {result['message']}")
    
    # Get status
    print("\n2. Getting User Status...")
    response = requests.get(
        f"{BASE_URL}/chatbot/status",
        headers=get_headers()
    )
    print(f"Status: {response.status_code}")
    if response.ok:
        status = response.json()
        print(f"  Total Sessions: {status['total_sessions']}")
        print(f"  Total Hours: {status['total_hours']:.1f}")
        print(f"  Consistency Score: {status['consistency_score']:.1f}%")
        print(f"  Current Streak: {status['current_streak']} days")
    
    # Trigger reminder
    print("\n3. Triggering Reminder...")
    response = requests.post(
        f"{BASE_URL}/chatbot/trigger-reminder",
        headers=get_headers(),
        json={"subject": "Data Structures"}
    )
    print(f"Status: {response.status_code}")
    if response.ok:
        result = response.json()
        print(f"  Message: {result['message']}")
    
    # Get insights
    print("\n4. Getting Insights for Chatbot...")
    response = requests.get(
        f"{BASE_URL}/chatbot/insights",
        headers=get_headers()
    )
    print(f"Status: {response.status_code}")
    if response.ok:
        result = response.json()
        print(f"  Summary: {result['summary']}")
        print(f"  Insights Count: {len(result['insights'])}")
    
    # Get activity summary
    print("\n5. Getting Activity Summary...")
    response = requests.get(
        f"{BASE_URL}/chatbot/activity-summary?days=7",
        headers=get_headers()
    )
    print(f"Status: {response.status_code}")
    if response.ok:
        summary = response.json()
        print(f"  Summary: {summary['summary_text']}")


def test_supervisor_integration():
    """Test supervisor agent integration"""
    print("\n" + "="*60)
    print("TESTING SUPERVISOR INTEGRATION")
    print("="*60)
    
    # Analyze student
    print("\n1. Analyzing Student...")
    supervisor_request = {
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
            {"date": "2025-09-26", "subject": "AI Fundamentals", "hours": 1, "status": "partial"}
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
    
    response = requests.post(
        f"{BASE_URL}/supervisor/analyze",
        headers={"Content-Type": "application/json"},
        json=supervisor_request
    )
    print(f"Status: {response.status_code}")
    if response.ok:
        result = response.json()
        print(f"\n  Analysis Summary:")
        print(f"    Total Study Hours: {result['analysis_summary']['total_study_hours']}")
        print(f"    Completion Rate: {result['analysis_summary']['average_completion_rate']}")
        print(f"    Consistency Score: {result['report_summary']['consistency_score']}")
        print(f"    Engagement Level: {result['report_summary']['engagement_level']}")
        print(f"\n  Recommendations: {len(result['recommendations'])}")
        for i, rec in enumerate(result['recommendations'][:3], 1):
            print(f"    {i}. {rec}")
    else:
        print(f"  Error: {response.text}")


def test_study_recommendations():
    """Test comprehensive study recommendations"""
    print("\n" + "="*60)
    print("TESTING STUDY RECOMMENDATIONS")
    print("="*60)
    
    response = requests.get(
        f"{BASE_URL}/ai/study-recommendations",
        headers=get_headers()
    )
    print(f"Status: {response.status_code}")
    if response.ok:
        result = response.json()
        print(f"\nTotal Recommendations: {result['total_recommendations']}\n")
        
        for rec in result['recommendations']:
            print(f"[{rec['priority'].upper()}] {rec['title']}")
            print(f"  {rec['message']}\n")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("AI AGENT API TESTING SUITE")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        test_ai_insights()
        test_reminder_features()
        test_chatbot_integration()
        test_supervisor_integration()
        test_study_recommendations()
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server")
        print("Make sure the server is running on", BASE_URL)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        TOKEN = sys.argv[1]
        print(f"Using provided token: {TOKEN[:20]}...")
    else:
        print("\n⚠️  WARNING: Using default token. Provide token as argument:")
        print("   python test_ai_api.py YOUR_JWT_TOKEN")
        print("\nTo get a token:")
        print("   1. Register/Login via /api/auth/register or /api/auth/login")
        print("   2. Copy the access_token from the response")
        print("   3. Run: python test_ai_api.py <token>\n")
    
    run_all_tests()
