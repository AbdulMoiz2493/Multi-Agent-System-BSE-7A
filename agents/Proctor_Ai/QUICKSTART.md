# AI Agent Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### 1. Install Dependencies
```bash
cd "d:\Uni\7th Semester\SPM\project\SPM-Project-Backend"
pip install -r requirements.txt
```

### 2. Run Database Migration
```bash
# Generate migration (if needed)
alembic revision --autogenerate -m "Add AI models"

# Apply migration
alembic upgrade head
```

### 3. Start the Server
```bash
uvicorn app.main:app --reload
```

### 4. Access API Documentation
Open your browser and go to:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Quick Test

### Step 1: Register/Login
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "full_name": "Test User"
  }'
```

Copy the `access_token` from the response.

### Step 2: Test AI Insights
```bash
# Replace YOUR_TOKEN with actual token
curl -X POST "http://localhost:8000/api/ai/generate-insights" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"days_back": 30}'
```

### Step 3: Test Chatbot Integration
```bash
curl -X POST "http://localhost:8000/api/chatbot/log-study" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "course_name": "Operating Systems",
    "duration_minutes": 60
  }'
```

### Step 4: Test Supervisor Integration
```bash
curl -X POST "http://localhost:8000/api/supervisor/analyze" \
  -H "Content-Type: application/json" \
  -d @supervisor_test_payload.json
```

## 📁 File Structure

```
app/
├── ai/                      # AI Services
│   ├── insights_service.py  # Insights generation
│   ├── reminder_service.py  # Reminder logic
│   └── examples.py          # Usage examples
│
├── api/routes/              # API Endpoints
│   ├── ai.py               # AI & Insights endpoints
│   ├── chatbot.py          # Chatbot integration
│   └── supervisor.py       # Supervisor agent
│
├── models/                  # Database Models
│   ├── insight.py          # Insights model
│   └── chatbot_log.py      # Chatbot logs model
│
└── schemas/                 # Request/Response schemas
    └── ai.py               # AI-related schemas
```

## 🔑 Key Endpoints

### AI & Insights
- `POST /api/ai/generate-insights` - Generate AI insights
- `GET /api/ai/study-patterns` - Get study patterns
- `POST /api/ai/reminder-schedule` - Create reminder schedule
- `GET /api/ai/study-recommendations` - Get recommendations

### Chatbot Integration
- `POST /api/chatbot/log-study` - Log study session
- `GET /api/chatbot/status` - Get user status
- `POST /api/chatbot/trigger-reminder` - Trigger reminder
- `GET /api/chatbot/insights` - Get insights

### Supervisor Agent
- `POST /api/supervisor/analyze` - Analyze student
- `GET /api/supervisor/student-trends/{id}` - Get trends
- `GET /api/supervisor/engagement-metrics/{id}` - Get metrics

## 💡 Usage Examples

### Generate Insights (Python)
```python
from app.ai.insights_service import InsightsService

insights = InsightsService.generate_insights(user_id=1, db=db_session)
for insight in insights:
    print(f"{insight['title']}: {insight['message']}")
```

### Create Reminder Schedule (Python)
```python
from app.ai.reminder_service import ReminderService

schedule = ReminderService.create_reminder_schedule(
    user_id=1,
    db=db_session,
    days_ahead=7,
    preferred_times=["19:00", "21:00"]
)
```

### Chatbot Log Study (API)
```bash
POST /api/chatbot/log-study
{
  "course_name": "Data Structures",
  "duration_minutes": 45,
  "notes": "Studied binary trees"
}
```

## 🧩 Integration Points

### For Frontend Developer (Member 2)
Use these endpoints to display AI features:
- `/api/ai/insights` - Display insights on dashboard
- `/api/ai/study-patterns` - Show pattern visualizations
- `/api/ai/neglected-subjects` - Highlight neglected subjects
- `/api/chatbot/*` - Integrate chatbot functionality

### For Supervisor Agent (External Team)
Use this endpoint for student analysis:
- `/api/supervisor/analyze` - Main analysis endpoint
  - Input: Student profile + activity log
  - Output: Analysis, recommendations, alerts

### For Chatbot (Integration)
Use these endpoints for chatbot features:
- `/api/chatbot/log-study` - Log study sessions
- `/api/chatbot/status` - Get user status
- `/api/chatbot/insights` - Get AI insights
- `/api/chatbot/trigger-reminder` - Send reminders

## 🐛 Troubleshooting

### Database Connection Error
```bash
# Check .env file has DATABASE_URL set
# Example: DATABASE_URL=postgresql://user:pass@localhost/dbname
```

### Migration Issues
```bash
# Reset migrations (careful - deletes data!)
alembic downgrade base
alembic upgrade head
```

### Import Errors
```bash
# Make sure you're in the project directory
cd "d:\Uni\7th Semester\SPM\project\SPM-Project-Backend"

# Reinstall dependencies
pip install -r requirements.txt
```

### Token Authentication Errors
```bash
# Get new token
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpass"}'
```

## 📊 Testing

### Run Python Tests
```bash
python test_ai_api.py YOUR_JWT_TOKEN
```

### Run Shell Tests
```bash
# On Windows (PowerShell)
bash test_ai_endpoints.sh

# Or manually copy-paste commands from the file
```

### Use Swagger UI
1. Go to http://localhost:8000/docs
2. Click "Authorize" and enter your token
3. Try out any endpoint interactively

## 📚 Documentation

- **Full Documentation**: See `AI_AGENT_README.md`
- **API Docs**: http://localhost:8000/docs
- **Examples**: See `app/ai/examples.py`
- **Test Scripts**: See `test_ai_api.py`

## 🎯 Next Steps

1. ✅ Review the API documentation
2. ✅ Test endpoints using Swagger UI
3. ✅ Integrate with frontend
4. ✅ Connect chatbot
5. ✅ Test supervisor integration
6. ✅ Add more test data for better insights

## 📞 Support

For issues:
1. Check server logs in terminal
2. Verify database connection
3. Ensure migrations are up to date
4. Check API documentation at /docs

## 🎉 Success Checklist

- [ ] Server starts without errors
- [ ] Can access /docs endpoint
- [ ] Can register/login
- [ ] Can generate insights
- [ ] Can create reminder schedule
- [ ] Chatbot endpoints work
- [ ] Supervisor endpoint works
- [ ] Frontend can consume APIs

You're all set! 🚀
