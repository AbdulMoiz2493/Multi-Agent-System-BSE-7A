"""
API Testing Examples using curl commands
Test all AI Agent endpoints
"""

# Set your authentication token
TOKEN="your_jwt_token_here"
BASE_URL="http://localhost:8000/api"

# ============================================================================
# AI & INSIGHTS ENDPOINTS
# ============================================================================

# 1. Generate AI Insights
curl -X POST "$BASE_URL/ai/generate-insights" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"days_back": 30}'

# 2. Get Previous Insights
curl -X GET "$BASE_URL/ai/insights?limit=10" \
  -H "Authorization: Bearer $TOKEN"

# 3. Analyze Study Patterns
curl -X GET "$BASE_URL/ai/study-patterns?days=30" \
  -H "Authorization: Bearer $TOKEN"

# 4. Create Reminder Schedule
curl -X POST "$BASE_URL/ai/reminder-schedule" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "days_ahead": 7,
    "preferred_times": ["19:00", "21:00"]
  }'

# 5. Get Optimal Study Times
curl -X GET "$BASE_URL/ai/optimal-study-times" \
  -H "Authorization: Bearer $TOKEN"

# 6. Get Neglected Subjects
curl -X GET "$BASE_URL/ai/neglected-subjects?days=7" \
  -H "Authorization: Bearer $TOKEN"

# 7. Check if Should Study Now
curl -X GET "$BASE_URL/ai/should-study-now" \
  -H "Authorization: Bearer $TOKEN"

# 8. Get Study Recommendations
curl -X GET "$BASE_URL/ai/study-recommendations" \
  -H "Authorization: Bearer $TOKEN"


# ============================================================================
# CHATBOT INTEGRATION ENDPOINTS
# ============================================================================

# 1. Log Study Session (Chatbot)
curl -X POST "$BASE_URL/chatbot/log-study" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "course_name": "Operating Systems",
    "duration_minutes": 60,
    "notes": "Studied CPU scheduling algorithms"
  }'

# 2. Get User Status (Chatbot)
curl -X GET "$BASE_URL/chatbot/status" \
  -H "Authorization: Bearer $TOKEN"

# 3. Trigger Reminder (Chatbot)
curl -X POST "$BASE_URL/chatbot/trigger-reminder" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Data Structures"
  }'

# 4. Get Insights (Chatbot)
curl -X GET "$BASE_URL/chatbot/insights" \
  -H "Authorization: Bearer $TOKEN"

# 5. Get Activity Summary (Chatbot)
curl -X GET "$BASE_URL/chatbot/activity-summary?days=7" \
  -H "Authorization: Bearer $TOKEN"


# ============================================================================
# SUPERVISOR AGENT ENDPOINTS
# ============================================================================

# 1. Analyze Student (Main Supervisor Endpoint)
curl -X POST "$BASE_URL/supervisor/analyze" \
  -H "Content-Type: application/json" \
  -d '{
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
  }'

# 2. Get Student Trends
curl -X GET "$BASE_URL/supervisor/student-trends/STU_2709?days=30" \
  -H "Content-Type: application/json"

# 3. Get Engagement Metrics
curl -X GET "$BASE_URL/supervisor/engagement-metrics/STU_2709" \
  -H "Content-Type: application/json"


# ============================================================================
# EXISTING ANALYTICS ENDPOINTS (Enhanced with AI data)
# ============================================================================

# User Progress
curl -X GET "$BASE_URL/analytics/user-progress?days=30" \
  -H "Authorization: Bearer $TOKEN"

# Consistency Trends
curl -X GET "$BASE_URL/analytics/consistency?days=30" \
  -H "Authorization: Bearer $TOKEN"

# Insights Data
curl -X GET "$BASE_URL/analytics/insights-data" \
  -H "Authorization: Bearer $TOKEN"
