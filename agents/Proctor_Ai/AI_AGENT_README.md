# AI Agent Module Documentation

## Overview
This module implements the AI/Integration Developer (Member 3) component of the Study Session Tracker. It provides intelligent reminder scheduling, personalized insights, analytics integration, chatbot support, and supervisor agent integration.

## Architecture

### Core Components

1. **AI Services** (`app/ai/`)
   - `insights_service.py`: Generates personalized study insights
   - `reminder_service.py`: AI-powered reminder decision logic

2. **Database Models** (`app/models/`)
   - `insight.py`: Stores generated insights
   - `chatbot_log.py`: Tracks chatbot interactions

3. **API Routes** (`app/api/routes/`)
   - `ai.py`: AI analytics and insights endpoints
   - `chatbot.py`: Chatbot integration endpoints
   - `supervisor.py`: Supervisor agent integration endpoints

4. **Schemas** (`app/schemas/`)
   - `ai.py`: Pydantic models for request/response validation

## Features

### 1. AI Reminder Logic

**Service**: `ReminderService` in `app/ai/reminder_service.py`

**Capabilities**:
- Analyzes user study patterns (frequency, timing, missed sessions)
- Determines optimal reminder times based on historical data
- Generates contextual motivational messages
- Identifies neglected subjects
- Creates personalized reminder schedules

**Key Methods**:
- `analyze_study_frequency()`: Analyzes study patterns
- `determine_reminder_times()`: Calculates optimal reminder times
- `generate_reminder_message()`: Creates contextual messages
- `should_send_reminder()`: Decides if reminder is needed
- `get_neglected_subjects()`: Identifies subjects needing attention
- `create_reminder_schedule()`: Generates weekly reminder schedule

### 2. Personalized Insights

**Service**: `InsightsService` in `app/ai/insights_service.py`

**Capabilities**:
- Analyzes study consistency and trends
- Generates rule-based insights and feedback
- Calculates performance metrics
- Identifies study gaps and patterns
- Provides actionable recommendations

**Insight Types**:
- **Consistency**: Study habit consistency analysis
- **Performance**: Performance trends and metrics
- **Recommendation**: Actionable study suggestions
- **Warning**: Alerts for concerning patterns

**Key Methods**:
- `analyze_study_patterns()`: Comprehensive pattern analysis
- `generate_insights()`: Creates personalized insights
- `save_insights()`: Persists insights to database

### 3. Analytics Integration

**Endpoints**: `/api/ai/*`

**Features**:
- User progress metrics computation
- Consistency trend calculation
- Study pattern visualization data
- Optimal study time recommendations
- Neglected subject identification

### 4. Chatbot Integration

**Endpoints**: `/api/chatbot/*`

**Capabilities**:

#### Log Study Activity
```http
POST /api/chatbot/log-study
```
Allows chatbot to log study sessions on behalf of users.

#### Request User Status
```http
GET /api/chatbot/status
```
Returns comprehensive user study status including:
- Total sessions and hours
- Consistency score
- Current streak
- Top subject
- Days since last session

#### Trigger Reminders
```http
POST /api/chatbot/trigger-reminder
```
Enables chatbot-triggered study reminders with AI-generated messages.

#### Request Insights
```http
GET /api/chatbot/insights
```
Retrieves AI-generated insights for chatbot display.

#### Activity Summary
```http
GET /api/chatbot/activity-summary
```
Quick summary of recent study activity for conversations.

### 5. Supervisor Agent Integration

**Endpoints**: `/api/supervisor/*`

**Input Format**:
```json
{
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
```

**Output Format**:
```json
{
  "student_id": "STU_2709",
  "analysis_summary": {
    "total_study_hours": 12,
    "average_completion_rate": "76%",
    "most_active_subject": "Operating Systems",
    "least_active_subject": "Software Management"
  },
  "recommendations": [
    "Add one more revision session for Software Management.",
    "Continue current schedule for Operating Systems."
  ],
  "reminder_schedule": [
    {"day": "Monday", "time": "7:00 PM"},
    {"day": "Wednesday", "time": "8:00 PM"}
  ],
  "performance_alerts": [
    {"type": "warning", "message": "Missed 2 consecutive study sessions."}
  ],
  "report_summary": {
    "week": "Sept 20–Sept 27",
    "consistency_score": 85,
    "engagement_level": "High"
  }
}
```

**Key Endpoints**:

#### Analyze Student
```http
POST /api/supervisor/analyze
```
Main endpoint for comprehensive student analysis.

#### Student Trends
```http
GET /api/supervisor/student-trends/{student_id}
```
Lightweight summarized trends for supervisor dashboard.

#### Engagement Metrics
```http
GET /api/supervisor/engagement-metrics/{student_id}
```
Anonymized engagement metrics including at-risk indicators.

## API Endpoints Reference

### AI & Insights (`/api/ai/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/generate-insights` | POST | Generate new AI insights |
| `/insights` | GET | Get previously generated insights |
| `/study-patterns` | GET | Detailed study pattern analysis |
| `/reminder-schedule` | POST | Create AI-powered reminder schedule |
| `/optimal-study-times` | GET | Get recommended study times |
| `/neglected-subjects` | GET | Identify neglected subjects |
| `/should-study-now` | GET | AI decision on studying now |
| `/study-recommendations` | GET | Comprehensive recommendations |

### Chatbot Integration (`/api/chatbot/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/log-study` | POST | Log study session via chatbot |
| `/status` | GET | Get user study status |
| `/trigger-reminder` | POST | Trigger study reminder |
| `/insights` | GET | Get insights for chatbot |
| `/activity-summary` | GET | Quick activity summary |

### Supervisor Agent (`/api/supervisor/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze` | POST | Comprehensive student analysis |
| `/student-trends/{student_id}` | GET | Student study trends |
| `/engagement-metrics/{student_id}` | GET | Engagement metrics |

## Database Schema

### Insights Table
```sql
CREATE TABLE insights (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    insight_type ENUM('consistency', 'performance', 'recommendation', 'warning'),
    title VARCHAR,
    message TEXT,
    confidence_score INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Chatbot Logs Table
```sql
CREATE TABLE chatbot_logs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action_type ENUM('log_study', 'get_status', 'trigger_reminder', 'get_insights'),
    request_data TEXT,
    response_data TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Database Migration
```bash
alembic upgrade head
```

### 3. Start the Server
```bash
uvicorn app.main:app --reload
```

## Usage Examples

### Generate Insights
```python
from app.ai.insights_service import InsightsService

# Generate insights for user
insights = InsightsService.generate_insights(user_id=1, db=db_session)

# Save to database
saved_insights = InsightsService.save_insights(user_id=1, db=db_session)
```

### Create Reminder Schedule
```python
from app.ai.reminder_service import ReminderService

# Create 7-day reminder schedule
schedule = ReminderService.create_reminder_schedule(
    user_id=1,
    db=db_session,
    days_ahead=7,
    preferred_times=["19:00", "21:00"]
)
```

### Analyze Study Patterns
```python
from app.ai.insights_service import InsightsService

# Get comprehensive pattern analysis
patterns = InsightsService.analyze_study_patterns(
    user_id=1, 
    db=db_session,
    days=30
)
```

## Testing

### Test Chatbot Integration
```bash
curl -X POST "http://localhost:8000/api/chatbot/log-study" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "course_name": "Operating Systems",
    "duration_minutes": 60,
    "notes": "Studied process scheduling"
  }'
```

### Test Supervisor Integration
```bash
curl -X POST "http://localhost:8000/api/supervisor/analyze" \
  -H "Content-Type: application/json" \
  -d @supervisor_request.json
```

## Configuration

No additional configuration needed. The AI agent uses existing database and authentication setup.

## Performance Considerations

- Insights are generated on-demand to ensure freshness
- Caching can be implemented for frequently accessed patterns
- Database queries are optimized with indexes
- Analysis is limited to configurable time periods

## Future Enhancements

1. **Machine Learning Integration**: Replace rule-based insights with ML models
2. **Predictive Analytics**: Predict future study patterns and outcomes
3. **Natural Language Processing**: Analyze study notes for deeper insights
4. **Advanced Personalization**: Multi-factor personalization algorithms
5. **Real-time Notifications**: Push notifications for reminders
6. **A/B Testing**: Test different reminder strategies

## Support

For issues or questions:
1. Check API documentation at `/docs`
2. Review logs in terminal
3. Verify database migrations are up to date
4. Ensure authentication tokens are valid

## License

Part of the Study Session Tracker project.
