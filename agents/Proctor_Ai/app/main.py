from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from app.core.config import settings
from app.api.api import api_router
from app.core.database import engine, Base, get_db, SessionLocal
from app.core.security import get_password_hash
import uuid

# Import all models so they're registered with Base
from app.models.user import User
from app.models.study_session import StudySession
from app.models.course import Course
from app.models.reminder import Reminder
from app.models.insight import Insight
from app.models.chatbot_log import ChatbotLog

# Create all tables automatically on startup
Base.metadata.create_all(bind=engine)


def create_default_user():
    """Create a default test user if it doesn't exist."""
    db = SessionLocal()
    try:
        # Check if test user exists
        existing_user = db.query(User).filter(User.email == "test@example.com").first()
        if not existing_user:
            # Create default test user
            default_user = User(
                email="test@example.com",
                hashed_password=get_password_hash("testpassword123"),
                full_name="Test User"
            )
            db.add(default_user)
            db.commit()
            print("Created default test user: test@example.com")
        else:
            print("Default test user already exists")
    except Exception as e:
        print(f"Error creating default user: {e}")
        db.rollback()
    finally:
        db.close()


# Create default user on startup
create_default_user()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Study Session Tracker API - Backend for tracking study sessions with AI-powered reminders",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://*.app.github.dev",  # GitHub Codespaces
        "*"  # Allow all origins (for development)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Study Session Tracker API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "agent": "daily_revision_proctor_agent", "version": "1.0.0"}


@app.post("/process")
async def process_task(request: Request):
    """
    Process endpoint for supervisor integration.
    Accepts TaskEnvelope format and forwards to /api/supervisor/analyze.
    """
    from sqlalchemy.orm import Session
    from app.api.routes.supervisor import supervisor_analyze_student
    from app.schemas.ai import SupervisorAgentRequest
    
    try:
        body = await request.json()
        
        # Extract task parameters from TaskEnvelope format
        task_params = body.get("task", {}).get("parameters", {})
        
        # If it's a direct supervisor request format, use it directly
        if "student_id" in task_params and "study_schedule" in task_params:
            supervisor_request = SupervisorAgentRequest(**task_params)
        else:
            # Build supervisor request from extracted params
            from datetime import datetime
            activity_log = task_params.get("activity_log", [])
            if not activity_log:
                today = datetime.now().strftime("%Y-%m-%d")
                activity_log = [{
                    "date": today,
                    "subject": task_params.get("subject", "General Study"),
                    "hours": task_params.get("hours", 1.0),
                    "status": "completed"
                }]
            
            supervisor_request = SupervisorAgentRequest(
                student_id=task_params.get("student_id", task_params.get("user_id", "1")),
                profile=task_params.get("profile", {"name": "Student", "grade": "N/A"}),
                study_schedule=task_params.get("study_schedule", {
                    "preferred_times": ["09:00", "14:00", "19:00"],
                    "daily_goal_hours": 3.0
                }),
                activity_log=activity_log,
                user_feedback=task_params.get("user_feedback", {
                    "reminder_effectiveness": 4,
                    "motivation_level": "medium"
                }),
                context=task_params.get("context", {
                    "request_type": "analysis",
                    "supervisor_id": "supervisor_main",
                    "priority": "normal"
                })
            )
        
        # Get database session
        db = next(get_db())
        try:
            # Call the supervisor analyze endpoint
            result = supervisor_analyze_student(supervisor_request, db)
            
            # Return in CompletionReport format
            return {
                "message_id": str(uuid.uuid4()),
                "sender": "daily_revision_proctor_agent",
                "recipient": body.get("sender", "supervisor"),
                "related_message_id": body.get("message_id", ""),
                "status": "SUCCESS",
                "results": result.model_dump() if hasattr(result, 'model_dump') else result
            }
        finally:
            db.close()
            
    except Exception as e:
        return {
            "message_id": str(uuid.uuid4()),
            "sender": "daily_revision_proctor_agent",
            "recipient": body.get("sender", "supervisor") if 'body' in dir() else "supervisor",
            "related_message_id": body.get("message_id", "") if 'body' in dir() else "",
            "status": "FAILURE",
            "results": {"error": str(e)}
        }

