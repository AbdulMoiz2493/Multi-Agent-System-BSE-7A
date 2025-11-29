# Study Session Tracker API

FastAPI backend service for tracking study sessions with AI-powered reminders, personalized insights, and analytics.

## Features

- **Authentication**: JWT-based user authentication
- **Study Sessions**: CRUD operations for study sessions
- **Analytics**: User progress tracking and consistency metrics
- **🤖 Agentic AI (NEW!)**: Powered by Google Gemini Flash for intelligent analysis
- **AI-Powered Insights**: Personalized study recommendations and pattern analysis
- **Smart Reminders**: AI-driven reminder scheduling and motivational messages
- **Chatbot Integration**: API endpoints for chatbot study logging and status
- **Supervisor Agent**: External supervisor integration with LLM reasoning
- **Swagger UI**: Interactive API documentation and testing

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Authentication**: JWT (python-jose, passlib)
- **AI/ML**: LangChain + Google Gemini 1.5 Flash
- **API Docs**: Swagger UI (built-in)

## 🚀 Quick Start

See **[QUICKSTART.md](QUICKSTART.md)** for a 5-minute setup guide.

For detailed AI Agent documentation, see **[AI_AGENT_README.md](AI_AGENT_README.md)**.

### 🆕 Gemini AI Agent Setup

The system now uses **Google Gemini Flash** for intelligent student analysis. See **[GEMINI_AGENT_SETUP.md](GEMINI_AGENT_SETUP.md)** for:
- Complete setup instructions
- How to get your Gemini API key
- Architecture overview
- Testing guide

**Quick Setup:**
1. Get API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Add `GEMINI_API_KEY=your_key` to `.env`
3. Run `pip install -r requirements.txt`
4. Test with `python test_gemini_agent.py`

## Setup Instructions

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- pip

### Installation

1. **Clone the repository** (if applicable)

2. **Create a virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**:
```bash
cp .env.example .env
```

Edit `.env` and update the following:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: A random secret key for JWT tokens

Example `.env`:
```
DATABASE_URL=postgresql://user:password@localhost:5432/study_tracker_db
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

5. **Create the PostgreSQL database**:
```bash
createdb study_tracker_db
```

6. **Run database migrations**:
```bash
alembic upgrade head
```

7. **Seed the database** (optional, for testing):
```bash
python scripts/seed_data.py
```

8. **Start the server**:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

### Swagger UI

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing with Swagger UI

Swagger UI provides an interactive interface to test all API endpoints:

1. **Start the server**: `uvicorn app.main:app --reload`

2. **Open Swagger UI**: Navigate to `http://localhost:8000/docs`

3. **Register a new user**:
   - Click on `POST /api/auth/register`
   - Click "Try it out"
   - Enter user details:
     ```json
     {
       "email": "test@example.com",
       "full_name": "Test User",
       "password": "password123"
     }
     ```
   - Click "Execute"

4. **Login to get JWT token**:
   - Click on `POST /api/auth/login`
   - Click "Try it out"
   - Enter credentials:
     ```json
     {
       "email": "test@example.com",
       "password": "password123"
     }
     ```
   - Click "Execute"
   - Copy the `access_token` from the response

5. **Authorize Swagger UI**:
   - Click the "Authorize" button at the top right
   - Paste the access token in the "Value" field
   - Click "Authorize"
   - Click "Close"

6. **Test protected endpoints**:
   - Now you can test all protected endpoints (sessions, analytics, etc.)
   - Swagger UI will automatically include the token in requests

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/me` - Get current user info

### Study Sessions
- `POST /api/sessions` - Create study session
- `GET /api/sessions` - List sessions (with pagination and filtering)
- `GET /api/sessions/{id}` - Get session details
- `PUT /api/sessions/{id}` - Update session
- `DELETE /api/sessions/{id}` - Delete session

### Users
- `GET /api/users/me` - Get current user profile
- `PUT /api/users/me` - Update user profile
- `GET /api/users/{id}/reminder-data` - Get user data for reminders

### Analytics
- `GET /api/analytics/user-progress` - User progress metrics
- `GET /api/analytics/consistency` - Consistency trends
- `GET /api/analytics/insights-data` - Raw data for AI insights

### Reminders (for Person C)
- `POST /api/reminders/log` - Log reminder delivery
- `GET /api/reminders/status` - Get reminder status

### AI & Insights (NEW - Member 3)
- `POST /api/ai/generate-insights` - Generate AI-powered insights
- `GET /api/ai/insights` - Get previously generated insights
- `GET /api/ai/study-patterns` - Detailed study pattern analysis
- `POST /api/ai/reminder-schedule` - Create AI-powered reminder schedule
- `GET /api/ai/optimal-study-times` - Get recommended study times
- `GET /api/ai/neglected-subjects` - Identify neglected subjects
- `GET /api/ai/should-study-now` - AI decision on studying now
- `GET /api/ai/study-recommendations` - Comprehensive recommendations

### Chatbot Integration (NEW - Member 3)
- `POST /api/chatbot/log-study` - Log study session via chatbot
- `GET /api/chatbot/status` - Get user study status
- `POST /api/chatbot/trigger-reminder` - Trigger study reminder
- `GET /api/chatbot/insights` - Get AI insights for chatbot
- `GET /api/chatbot/activity-summary` - Quick activity summary

### Supervisor Agent (NEW - Member 3)
- `POST /api/supervisor/analyze` - Comprehensive student analysis
- `GET /api/supervisor/student-trends/{student_id}` - Student study trends
- `GET /api/supervisor/engagement-metrics/{student_id}` - Engagement metrics

## Database Migrations

### Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations:
```bash
alembic upgrade head
```

### Rollback migration:
```bash
alembic downgrade -1
```

## Project Structure

```
fastapi-backend/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── core/                # Core configuration
│   │   ├── config.py        # Settings
│   │   ├── database.py      # Database connection
│   │   └── security.py      # JWT functions
│   ├── models/              # SQLAlchemy models
│   │   ├── user.py
│   │   ├── study_session.py
│   │   ├── reminder.py
│   │   ├── insight.py       # NEW: AI insights model
│   │   └── chatbot_log.py   # NEW: Chatbot logs model
│   ├── schemas/             # Pydantic schemas
│   │   ├── user.py
│   │   ├── session.py
│   │   └── ai.py            # NEW: AI-related schemas
│   ├── api/                 # API routes
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── sessions.py
│   │       ├── analytics.py
│   │       ├── reminders.py
│   │       ├── ai.py        # NEW: AI & Insights endpoints
│   │       ├── chatbot.py   # NEW: Chatbot integration
│   │       └── supervisor.py # NEW: Supervisor agent
│   ├── crud/                # CRUD operations
│   └── ai/                  # NEW: AI Services (Member 3)
│       ├── insights_service.py   # Insights generation
│       ├── reminder_service.py   # Reminder logic
│       └── examples.py          # Usage examples
├── alembic/                 # Database migrations
│   └── versions/
│       └── add_ai_models.py # NEW: AI models migration
├── scripts/                 # Utility scripts
├── requirements.txt         # Python dependencies
├── AI_AGENT_README.md       # NEW: AI Agent documentation
├── QUICKSTART.md            # NEW: Quick start guide
├── test_ai_api.py          # NEW: Python test script
└── test_ai_endpoints.sh    # NEW: Shell test script
```

## Development

### Running in development mode:
```bash
uvicorn app.main:app --reload
```

The `--reload` flag enables auto-reload on code changes.

### Testing AI Endpoints

#### Using Python:
```bash
python test_ai_api.py YOUR_JWT_TOKEN
```

#### Using Shell:
```bash
bash test_ai_endpoints.sh
```

#### Using Swagger UI:
1. Go to http://localhost:8000/docs
2. Authorize with your JWT token
3. Test any endpoint interactively

## AI Agent Features (Member 3)

### 1. AI Reminder Logic
- Analyzes study patterns and frequency
- Determines optimal reminder times
- Generates contextual motivational messages
- Identifies neglected subjects

### 2. Personalized Insights
- Analyzes study consistency and trends
- Generates rule-based insights
- Provides actionable recommendations
- Calculates performance metrics

### 3. Chatbot Integration
- Log study activity via chatbot
- Request user status information
- Trigger reminders through chatbot
- Access AI-generated insights

### 4. Supervisor Agent Integration
- Accepts external supervisor requests
- Provides comprehensive student analysis
- Returns recommendations and alerts
- Generates engagement metrics

See **[AI_AGENT_README.md](AI_AGENT_README.md)** for detailed documentation.

## Notes

- The `app/ai/` directory contains AI/ML services for insights and reminders (Member 3)
- All endpoints require JWT authentication except `/api/auth/register`, `/api/auth/login`, and `/api/supervisor/*`
- Use Swagger UI for interactive testing - no need for Postman or other tools
- Seed data script creates 3 test users with study sessions for testing
- AI insights are generated on-demand based on user study patterns
- Chatbot endpoints allow external chatbot integration
- Supervisor endpoints enable external monitoring and analytics

## Team Member Responsibilities

- **Member 1 (Frontend)**: Consumes all API endpoints for UI/dashboard
- **Member 2 (Backend Core)**: Implemented database, auth, sessions, base analytics
- **Member 3 (AI/Integration)**: Implemented AI insights, reminders, chatbot, supervisor integration

## License

[Your License Here]

