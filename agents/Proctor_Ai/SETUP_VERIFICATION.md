# AI Agent Setup & Verification Guide

## 🎯 Step-by-Step Setup

### Step 1: Verify Prerequisites
```powershell
# Check Python version (should be 3.9+)
python --version

# Check PostgreSQL is running
# Make sure your database is accessible
```

### Step 2: Install Dependencies
```powershell
cd "d:\Uni\7th Semester\SPM\project\SPM-Project-Backend"
pip install -r requirements.txt
```

Expected output: All packages installed successfully including `python-dateutil`

### Step 3: Run Database Migration
```powershell
# This will create the new AI tables (insights, chatbot_logs)
alembic upgrade head
```

Expected output: Migration runs successfully, new tables created

### Step 4: Verify Database Tables
Connect to your PostgreSQL database and verify:
- `insights` table exists
- `chatbot_logs` table exists
- Both have proper relationships to `users` table

### Step 5: Start the Server
```powershell
uvicorn app.main:app --reload
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 6: Verify API Documentation
Open browser and go to: http://localhost:8000/docs

You should see new sections:
- **AI & Insights** (8 endpoints)
- **Chatbot Integration** (5 endpoints)
- **Supervisor Agent** (3 endpoints)

## ✅ Verification Checklist

### 1. Server Starts ✓
```powershell
uvicorn app.main:app --reload
```
- [ ] No import errors
- [ ] Server starts successfully
- [ ] Can access http://localhost:8000

### 2. API Documentation Loads ✓
Visit http://localhost:8000/docs
- [ ] Swagger UI loads
- [ ] See "AI & Insights" section
- [ ] See "Chatbot Integration" section
- [ ] See "Supervisor Agent" section

### 3. Create Test User ✓
Using Swagger UI:
1. Expand `POST /api/auth/register`
2. Click "Try it out"
3. Enter:
```json
{
  "email": "ai_test@example.com",
  "password": "testpass123",
  "full_name": "AI Test User"
}
```
4. Click "Execute"
- [ ] Returns 201 status
- [ ] Returns user data with ID

### 4. Login and Get Token ✓
1. Expand `POST /api/auth/login`
2. Click "Try it out"
3. Enter credentials from step 3
4. Click "Execute"
- [ ] Returns 200 status
- [ ] Returns `access_token`

5. Click "Authorize" button at top
6. Paste the token
7. Click "Authorize"
- [ ] Shows "Authorized" status

### 5. Test AI Insights ✓
1. Expand `POST /api/ai/generate-insights`
2. Click "Try it out"
3. Use default values
4. Click "Execute"
- [ ] Returns 200 status (or empty array if no sessions)
- [ ] No errors

### 6. Test Study Patterns ✓
1. Expand `GET /api/ai/study-patterns`
2. Click "Try it out"
3. Click "Execute"
- [ ] Returns 200 status
- [ ] Returns pattern data (even if zeros)

### 7. Test Chatbot Status ✓
1. Expand `GET /api/chatbot/status`
2. Click "Try it out"
3. Click "Execute"
- [ ] Returns 200 status
- [ ] Returns user status data

### 8. Test Supervisor Analyze ✓
1. Expand `POST /api/supervisor/analyze`
2. Click "Try it out"
3. Use this payload:
```json
{
  "student_id": "STU_2709",
  "profile": {
    "name": "Test Student",
    "program": "BS Computer Science",
    "semester": 7,
    "subjects": ["Math", "Physics"]
  },
  "study_schedule": {
    "preferred_times": ["19:00", "21:00"],
    "daily_goal_hours": 2
  },
  "activity_log": [
    {
      "date": "2025-09-25",
      "subject": "Math",
      "hours": 2,
      "status": "completed"
    }
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
4. Click "Execute"
- [ ] Returns 200 or 404 (404 is OK if student not found)
- [ ] No 500 errors

## 🧪 Full Integration Test

### Create Some Study Data First:

1. **Create a study session** using `POST /api/sessions`:
```json
{
  "course_name": "Operating Systems",
  "duration_minutes": 60,
  "session_date": "2025-11-17T14:00:00",
  "notes": "Studied CPU scheduling"
}
```

2. **Create another session**:
```json
{
  "course_name": "Data Structures",
  "duration_minutes": 45,
  "session_date": "2025-11-16T15:00:00",
  "notes": "Reviewed binary trees"
}
```

3. **Create one more**:
```json
{
  "course_name": "Operating Systems",
  "duration_minutes": 50,
  "session_date": "2025-11-15T16:00:00",
  "notes": "Memory management"
}
```

### Now Test AI Features:

1. **Generate Insights**: `POST /api/ai/generate-insights`
   - Should return 3-5 insights based on your study data

2. **Get Study Patterns**: `GET /api/ai/study-patterns?days=30`
   - Should show: 3 sessions, 155 minutes total, subjects breakdown

3. **Get Neglected Subjects**: `GET /api/ai/neglected-subjects?days=7`
   - Should identify Data Structures if you created recent OS sessions

4. **Create Reminder Schedule**: `POST /api/ai/reminder-schedule`
```json
{
  "days_ahead": 7,
  "preferred_times": ["19:00", "21:00"]
}
```
   - Should return 14 reminders (7 days × 2 times)

5. **Log via Chatbot**: `POST /api/chatbot/log-study`
```json
{
  "course_name": "Algorithms",
  "duration_minutes": 30,
  "notes": "Sorting algorithms"
}
```
   - Should create session and log chatbot action

6. **Check Chatbot Status**: `GET /api/chatbot/status`
   - Should show 4 sessions now, consistency score

## 🐛 Troubleshooting

### Problem: "Module not found" errors
**Solution:**
```powershell
pip install -r requirements.txt --force-reinstall
```

### Problem: Database connection error
**Solution:**
Check `.env` file has correct `DATABASE_URL`:
```
DATABASE_URL=postgresql://username:password@localhost/dbname
```

### Problem: Migration fails
**Solution:**
```powershell
# Reset migrations
alembic downgrade base
alembic upgrade head
```

### Problem: Import errors for new models
**Solution:**
```powershell
# Restart the server
# Press CTRL+C to stop
uvicorn app.main:app --reload
```

### Problem: 404 on new endpoints
**Solution:**
- Verify `app/api/api.py` includes new routers
- Restart the server
- Clear browser cache

### Problem: 401 Unauthorized errors
**Solution:**
- Get a fresh token via login
- Click "Authorize" in Swagger UI
- Paste the token
- Try again

## 📊 Expected Results

After setup, you should have:
- ✅ 19 new API endpoints working
- ✅ 2 new database tables created
- ✅ AI insights generating correctly
- ✅ Reminder schedules creating
- ✅ Chatbot integration working
- ✅ Supervisor integration accepting requests

## 🎓 Usage Tips

### For Testing:
1. Create multiple study sessions with different dates
2. Use different course names
3. Vary the duration
4. This will generate better AI insights

### For Integration:
1. Frontend: Use `/api/ai/*` and `/api/chatbot/*` endpoints
2. Chatbot: Use `/api/chatbot/*` endpoints exclusively
3. Supervisor: Use `/api/supervisor/analyze` endpoint

### For Development:
1. Check `app/ai/examples.py` for service usage
2. Review `AI_AGENT_README.md` for details
3. Use `test_ai_api.py` for automated testing

## 🚀 You're Ready!

If all checklist items are ✓, your AI agent is fully operational!

Next steps:
1. Share the API documentation with frontend team
2. Test chatbot integration
3. Verify supervisor agent connection
4. Deploy to production (if ready)

## 📞 Support Resources

- **API Docs**: http://localhost:8000/docs
- **Detailed Guide**: See `AI_AGENT_README.md`
- **Quick Start**: See `QUICKSTART.md`
- **Examples**: See `app/ai/examples.py`
- **Tests**: Run `python test_ai_api.py YOUR_TOKEN`

---

**Status**: Ready for production! 🎉
