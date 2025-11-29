from fastapi import APIRouter
from app.api.routes import auth, sessions, users, analytics, reminders, ai, chatbot, supervisor

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Study Sessions"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(reminders.router, prefix="/reminders", tags=["Reminders"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI & Insights"])
api_router.include_router(chatbot.router, prefix="/chatbot", tags=["Chatbot Integration"])
api_router.include_router(supervisor.router, prefix="/supervisor", tags=["Supervisor Agent"])

