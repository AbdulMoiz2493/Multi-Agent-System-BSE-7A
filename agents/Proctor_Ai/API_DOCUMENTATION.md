# Study Session Tracker - API Documentation

## Base URL
```
http://localhost:8080/api
```

## Table of Contents
1. [Study Sessions](#study-sessions)
2. [AI & Insights](#ai--insights)
3. [Chatbot Integration](#chatbot-integration)
4. [Supervisor Agent](#supervisor-agent)
5. [Analytics](#analytics)
6. [Reminders](#reminders)
7. [User Profile](#user-profile)

---

## Study Sessions

### Create Study Session
**POST** `/api/sessions`

**Request:**
```json
{
  "course_name": "Mathematics",
  "duration_minutes": 60,
  "session_date": "2024-11-24T14:00:00Z",
  "notes": "Completed calculus problems"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "user_id": 1,
  "course_name": "Mathematics",
  "duration_minutes": 60,
  "session_date": "2024-11-24T14:00:00Z",
  "notes": "Completed calculus problems",
  "created_at": "2024-11-24T14:05:00Z"
}
```

---

### List Study Sessions
**GET** `/api/sessions`

**Query Parameters:**
- `page` (integer, default: 1) - Page number
- `page_size` (integer, default: 10, max: 100) - Items per page
- `course_name` (string, optional) - Filter by course name
- `start_date` (datetime, optional) - Filter from this date
- `end_date` (datetime, optional) - Filter until this date

**Example Request:**
```
GET /api/sessions?page=1&page_size=10&course_name=Mathematics
```

**Response:** `200 OK`
```json
{
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "course_name": "Mathematics",
      "duration_minutes": 60,
      "session_date": "2024-11-24T14:00:00Z",
      "notes": "Completed calculus problems",
      "created_at": "2024-11-24T14:05:00Z"
    },
    {
      "id": 2,
      "user_id": 1,
      "course_name": "Physics",
      "duration_minutes": 45,
      "session_date": "2024-11-23T16:00:00Z",
      "notes": "Mechanics chapter review",
      "created_at": "2024-11-23T16:10:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 10
}
```

---

### Get Single Study Session
**GET** `/api/sessions/{session_id}`

**Example Request:**
```
GET /api/sessions/1
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "user_id": 1,
  "course_name": "Mathematics",
  "duration_minutes": 60,
  "session_date": "2024-11-24T14:00:00Z",
  "notes": "Completed calculus problems",
  "created_at": "2024-11-24T14:05:00Z"
}
```

**Response:** `404 Not Found`
```json
{
  "detail": "Study session not found"
}
```

---

### Update Study Session
**PUT** `/api/sessions/{session_id}`

**Request:**
```json
{
  "course_name": "Advanced Mathematics",
  "duration_minutes": 75,
  "notes": "Updated notes - completed integration problems"
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "user_id": 1,
  "course_name": "Advanced Mathematics",
  "duration_minutes": 75,
  "session_date": "2024-11-24T14:00:00Z",
  "notes": "Updated notes - completed integration problems",
  "created_at": "2024-11-24T14:05:00Z"
}
```

---

### Delete Study Session
**DELETE** `/api/sessions/{session_id}`

**Example Request:**
```
DELETE /api/sessions/1
```

**Response:** `204 No Content`

---

## AI & Insights

### Generate AI Insights
**POST** `/api/ai/generate-insights`

**Request:**
```json
{
  "force_regenerate": false
}
```

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "user_id": 1,
    "insight_type": "recommendation",
    "title": "Study Pattern Detected",
    "message": "You study best during evening hours. Consider scheduling more sessions between 7-9 PM.",
    "confidence_score": 85.5,
    "created_at": "2024-11-24T10:00:00Z"
  },
  {
    "id": 2,
    "user_id": 1,
    "insight_type": "warning",
    "title": "Consistency Alert",
    "message": "You haven't studied in 3 days. Try to maintain regular study habits.",
    "confidence_score": 92.0,
    "created_at": "2024-11-24T10:00:00Z"
  }
]
```

---

### Get Previous Insights
**GET** `/api/ai/insights`

**Query Parameters:**
- `limit` (integer, default: 10, max: 50) - Maximum number of insights

**Example Request:**
```
GET /api/ai/insights?limit=5
```

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "user_id": 1,
    "insight_type": "recommendation",
    "title": "Study Pattern Detected",
    "message": "You study best during evening hours.",
    "confidence_score": 85.5,
    "created_at": "2024-11-24T10:00:00Z"
  }
]
```

---

### Analyze Study Patterns
**GET** `/api/ai/study-patterns`

**Query Parameters:**
- `days` (integer, default: 30, max: 365) - Number of days to analyze

**Example Request:**
```
GET /api/ai/study-patterns?days=30
```

**Response:** `200 OK`
```json
{
  "total_sessions": 25,
  "total_hours": 37.5,
  "average_session_duration": 90,
  "consistency_score": 78.5,
  "most_active_subject": "Mathematics",
  "least_active_subject": "History",
  "subject_distribution": {
    "Mathematics": 45,
    "Physics": 30,
    "Chemistry": 25
  },
  "peak_study_times": ["19:00-21:00", "14:00-16:00"],
  "study_gaps": [
    {
      "start": "2024-11-10",
      "end": "2024-11-13",
      "days": 3
    }
  ],
  "unique_study_days": 20
}
```

---

### Create Reminder Schedule
**POST** `/api/ai/reminder-schedule`

**Request:**
```json
{
  "days_ahead": 7,
  "preferred_times": ["19:00", "21:00"]
}
```

**Response:** `200 OK`
```json
{
  "user_id": 1,
  "schedule": [
    {
      "day": "Monday",
      "time": "19:00",
      "datetime": "2024-11-25T19:00:00Z",
      "message": "Time to study Mathematics!",
      "subject": "Mathematics"
    },
    {
      "day": "Tuesday",
      "time": "21:00",
      "datetime": "2024-11-26T21:00:00Z",
      "message": "Don't forget to review Physics!",
      "subject": "Physics"
    }
  ],
  "total_reminders": 7
}
```

---

### Get Optimal Study Times
**GET** `/api/ai/optimal-study-times`

**Response:** `200 OK`
```json
{
  "user_id": 1,
  "has_established_pattern": true,
  "preferred_hours": [19, 21],
  "preferred_days": ["Monday", "Wednesday", "Friday"],
  "recommended_times": ["19:00", "21:00"],
  "confidence": "high"
}
```

---

### Get Neglected Subjects
**GET** `/api/ai/neglected-subjects`

**Query Parameters:**
- `days` (integer, default: 7, max: 30) - Days to look back

**Example Request:**
```
GET /api/ai/neglected-subjects?days=7
```

**Response:** `200 OK`
```json
{
  "user_id": 1,
  "period_days": 7,
  "neglected_subjects": ["History", "Literature"],
  "count": 2,
  "recommendation": "Consider studying History, Literature soon"
}
```

---

### Should Study Now
**GET** `/api/ai/should-study-now`

**Response:** `200 OK`
```json
{
  "should_study": true,
  "message": "Yes! You haven't studied in 3 days. Time to get back on track!",
  "days_since_last_session": 3,
  "last_session_date": "2024-11-21T14:00:00Z"
}
```

---

### Get Study Recommendations
**GET** `/api/ai/study-recommendations`

**Response:** `200 OK`
```json
{
  "user_id": 1,
  "total_recommendations": 5,
  "recommendations": [
    {
      "type": "recommendation",
      "priority": "high",
      "title": "Consistency Improvement",
      "message": "Try to study at the same time each day to build a habit."
    },
    {
      "type": "subject_balance",
      "priority": "medium",
      "title": "Neglected Subjects",
      "message": "Consider studying: History, Literature"
    },
    {
      "type": "timing",
      "priority": "low",
      "title": "Optimal Study Times",
      "message": "You study best at: 19:00-21:00, 14:00-16:00"
    }
  ],
  "generated_at": "2024-11-24T10:00:00Z"
}
```

---

## Chatbot Integration

### Log Study via Chatbot
**POST** `/api/chatbot/log-study`

**Request:**
```json
{
  "course_name": "Mathematics",
  "duration_minutes": 60,
  "session_date": "2024-11-24T14:00:00Z",
  "notes": "Studied via chatbot"
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "Study session logged successfully for Mathematics",
  "session_id": 1,
  "duration_minutes": 60,
  "session_date": "2024-11-24T14:00:00Z"
}
```

---

### Get Chatbot Status
**GET** `/api/chatbot/status`

**Response:** `200 OK`
```json
{
  "user_id": 1,
  "total_sessions": 25,
  "total_hours": 37.5,
  "consistency_score": 78.5,
  "last_session_date": "2024-11-23T14:00:00Z",
  "days_since_last_session": 1,
  "current_streak": 5,
  "top_subject": "Mathematics"
}
```

---

### Trigger Reminder via Chatbot
**POST** `/api/chatbot/trigger-reminder`

**Request:**
```json
{
  "subject": "Mathematics",
  "custom_message": "Don't forget to study calculus today!"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Don't forget to study calculus today!",
  "scheduled_time": "2024-11-24T19:00:00Z",
  "subject": "Mathematics"
}
```

---

### Get Chatbot Insights
**GET** `/api/chatbot/insights`

**Response:** `200 OK`
```json
{
  "insights": [
    {
      "id": 1,
      "user_id": 1,
      "insight_type": "recommendation",
      "title": "Study Pattern",
      "message": "You study best in the evening.",
      "confidence_score": 85.5,
      "created_at": "2024-11-24T10:00:00Z"
    }
  ],
  "summary": "I've analyzed your study patterns and found 3 insights. 2 of them are highly relevant to your current situation."
}
```

---

### Get Activity Summary
**GET** `/api/chatbot/activity-summary`

**Query Parameters:**
- `days` (integer, default: 7) - Number of days to analyze

**Example Request:**
```
GET /api/chatbot/activity-summary?days=7
```

**Response:** `200 OK`
```json
{
  "period_days": 7,
  "total_sessions": 10,
  "total_hours": 15.5,
  "subjects_studied": ["Mathematics", "Physics"],
  "average_daily_hours": 2.2,
  "summary_text": "In the last 7 days, you've completed 10 study sessions totaling 15.5 hours across 2 subjects."
}
```

---

## Supervisor Agent

### Analyze Student
**POST** `/api/supervisor/analyze`

**Request:**
```json
{
  "student_id": "STU_2709",
  "activity_log": [
    {
      "date": "2024-11-24",
      "subject": "Mathematics",
      "status": "completed",
      "duration_minutes": 60
    },
    {
      "date": "2024-11-23",
      "subject": "Physics",
      "status": "partial",
      "duration_minutes": 30
    }
  ],
  "study_schedule": {
    "preferred_times": ["19:00", "21:00"]
  }
}
```

**Response:** `200 OK`
```json
{
  "student_id": "STU_2709",
  "analysis_summary": {
    "total_study_hours": 37.5,
    "average_completion_rate": "85%",
    "most_active_subject": "Mathematics",
    "least_active_subject": "History"
  },
  "recommendations": [
    "Add one more revision session for History.",
    "Continue current schedule for Mathematics.",
    "Try to establish a more consistent daily study routine."
  ],
  "reminder_schedule": [
    {
      "day": "Monday",
      "time": "19:00"
    },
    {
      "day": "Tuesday",
      "time": "21:00"
    }
  ],
  "performance_alerts": [
    {
      "type": "success",
      "message": "Student is performing well with consistent study habits."
    }
  ],
  "report_summary": {
    "week": "Nov 18–Nov 24",
    "consistency_score": 78,
    "engagement_level": "High"
  }
}
```

---

### Get Student Trends
**GET** `/api/supervisor/student-trends/{student_id}`

**Query Parameters:**
- `days` (integer, default: 30) - Number of days to analyze

**Example Request:**
```
GET /api/supervisor/student-trends/STU_2709?days=30
```

**Response:** `200 OK`
```json
{
  "student_id": "STU_2709",
  "period_days": 30,
  "total_study_hours": 37.5,
  "total_sessions": 25,
  "consistency_score": 78.5,
  "most_active_subject": "Mathematics",
  "average_session_duration": 90,
  "unique_study_days": 20
}
```

---

### Get Engagement Metrics
**GET** `/api/supervisor/engagement-metrics/{student_id}`

**Example Request:**
```
GET /api/supervisor/engagement-metrics/STU_2709
```

**Response:** `200 OK`
```json
{
  "student_id": "STU_2709",
  "engagement_level": "High",
  "consistency_score": 78.5,
  "total_sessions_30d": 25,
  "total_hours_30d": 37.5,
  "at_risk": false,
  "last_activity_days_ago": 1
}
```

---

## Analytics

### Get User Progress
**GET** `/api/analytics/user-progress`

**Query Parameters:**
- `days` (integer, default: 30, max: 365) - Days to analyze

**Example Request:**
```
GET /api/analytics/user-progress?days=30
```

**Response:** `200 OK`
```json
{
  "period_days": 30,
  "total_sessions": 25,
  "total_minutes": 2250,
  "total_hours": 37.5,
  "sessions_per_week": 5.8,
  "avg_session_duration_minutes": 90,
  "courses": [
    {
      "course_name": "Mathematics",
      "session_count": 12,
      "total_minutes": 1080
    },
    {
      "course_name": "Physics",
      "session_count": 8,
      "total_minutes": 720
    }
  ]
}
```

---

### Get Consistency Trends
**GET** `/api/analytics/consistency`

**Query Parameters:**
- `days` (integer, default: 30, max: 365) - Days to analyze

**Example Request:**
```
GET /api/analytics/consistency?days=30
```

**Response:** `200 OK`
```json
{
  "period_days": 30,
  "days_with_sessions": 20,
  "consistency_percentage": 66.67,
  "daily_data": [
    {
      "date": "2024-11-24",
      "sessions": 2,
      "total_minutes": 120
    },
    {
      "date": "2024-11-23",
      "sessions": 1,
      "total_minutes": 60
    }
  ],
  "weekly_trends": [
    {
      "week_start": "2024-11-18",
      "sessions": 5,
      "total_minutes": 450,
      "days_active": 4
    }
  ]
}
```

---

### Get Insights Data
**GET** `/api/analytics/insights-data`

**Response:** `200 OK`
```json
{
  "user_id": 1,
  "period_days": 60,
  "total_sessions": 50,
  "total_minutes": 4500,
  "courses": ["Mathematics", "Physics", "Chemistry"],
  "sessions": [
    {
      "id": 1,
      "course_name": "Mathematics",
      "duration_minutes": 60,
      "session_date": "2024-11-24T14:00:00Z",
      "notes": "Calculus problems"
    }
  ],
  "day_of_week_distribution": {
    "Monday": 10,
    "Tuesday": 8,
    "Wednesday": 12,
    "Thursday": 9,
    "Friday": 11
  },
  "avg_session_duration": 90
}
```

---

## Reminders

### Log Reminder
**POST** `/api/reminders/log`

**Request:**
```json
{
  "user_id": 1,
  "scheduled_time": "2024-11-24T19:00:00Z",
  "message": "Time to study Mathematics!",
  "status": "SENT"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "user_id": 1,
  "scheduled_time": "2024-11-24T19:00:00Z",
  "message": "Time to study Mathematics!",
  "status": "SENT",
  "created_at": "2024-11-24T19:00:05Z"
}
```

**Valid Status Values:**
- `SENT` - Reminder was sent successfully
- `DELIVERED` - Reminder was delivered to user
- `CLICKED` - User clicked/opened the reminder
- `DISMISSED` - User dismissed the reminder
- `FAILED` - Reminder failed to send

---

### Get Reminder Status
**GET** `/api/reminders/status`

**Response:** `200 OK`
```json
{
  "user_id": 1,
  "total_reminders_30d": 45,
  "status_counts": {
    "SENT": 40,
    "DELIVERED": 38,
    "CLICKED": 25,
    "DISMISSED": 10,
    "FAILED": 2
  },
  "recent_reminders": [
    {
      "id": 1,
      "scheduled_time": "2024-11-24T19:00:00Z",
      "message": "Time to study Mathematics!",
      "status": "SENT",
      "created_at": "2024-11-24T19:00:05Z"
    }
  ]
}
```

---

## User Profile

### Get User Profile
**GET** `/api/users/me`

**Response:** `200 OK`
```json
{
  "id": 1,
  "email": "student@example.com",
  "full_name": "John Doe",
  "created_at": "2024-11-24T10:00:00Z"
}
```

---

### Update User Profile
**PUT** `/api/users/me`

**Request:**
```json
{
  "email": "newemail@example.com",
  "full_name": "John Smith"
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "email": "newemail@example.com",
  "full_name": "John Smith",
  "created_at": "2024-11-24T10:00:00Z"
}
```

---

### Get User Reminder Data
**GET** `/api/users/{user_id}/reminder-data`

**Example Request:**
```
GET /api/users/1/reminder-data
```

**Response:** `200 OK`
```json
{
  "user_id": 1,
  "total_sessions_30d": 15,
  "total_minutes_30d": 900,
  "avg_sessions_per_week": 3.5,
  "courses": ["Mathematics", "Physics", "Chemistry"],
  "recent_sessions": [
    {
      "course_name": "Mathematics",
      "duration_minutes": 60,
      "session_date": "2024-11-23T14:00:00Z"
    }
  ]
}
```

---

## Common Response Codes

### Success Codes
- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `204 No Content` - Request successful, no content to return

### Error Codes
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Access denied
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

### Error Response Format
```json
{
  "detail": "Error message description"
}
```

---

## Frontend Integration Example

```javascript
// API Configuration
const API_BASE_URL = 'http://localhost:8080/api';

// Create Study Session
const createSession = async (sessionData) => {
  const response = await fetch(`${API_BASE_URL}/sessions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${yourToken}`
    },
    body: JSON.stringify({
      course_name: sessionData.courseName,
      duration_minutes: sessionData.duration,
      session_date: new Date().toISOString(),
      notes: sessionData.notes
    })
  });
  
  return await response.json();
};

// Get Study Insights
const getInsights = async () => {
  const response = await fetch(`${API_BASE_URL}/ai/insights?limit=10`, {
    headers: {
      'Authorization': `Bearer ${yourToken}`
    }
  });
  
  return await response.json();
};

// Get Analytics
const getAnalytics = async (days = 30) => {
  const response = await fetch(`${API_BASE_URL}/analytics/user-progress?days=${days}`, {
    headers: {
      'Authorization': `Bearer ${yourToken}`
    }
  });
  
  return await response.json();
};
```

---

## Testing with curl

```bash
# Create Study Session
curl -X POST "http://localhost:8080/api/sessions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "course_name": "Mathematics",
    "duration_minutes": 60,
    "notes": "Studied calculus"
  }'

# Get Insights
curl -X GET "http://localhost:8080/api/ai/insights?limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get Analytics
curl -X GET "http://localhost:8080/api/analytics/user-progress?days=30" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Interactive Documentation

Visit `http://localhost:8080/docs` for Swagger UI with interactive API testing.
