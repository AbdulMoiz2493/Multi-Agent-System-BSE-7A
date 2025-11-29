from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.core.database import get_db
from app.models.user import User
from app.models.reminder import Reminder, ReminderStatus
from app.api.deps import get_current_user
from pydantic import BaseModel, ConfigDict, field_validator

router = APIRouter()


class ReminderLogCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    user_id: int
    scheduled_time: datetime
    message: str
    status: ReminderStatus
    
    @field_validator('status', mode='before')
    @classmethod
    def validate_status(cls, v):
        """Accept both uppercase and lowercase, convert to uppercase"""
        if isinstance(v, str):
            # Convert to uppercase to match enum values
            v_upper = v.upper()
            try:
                return ReminderStatus(v_upper)
            except ValueError:
                # If uppercase doesn't work, try the original value
                try:
                    return ReminderStatus(v)
                except ValueError:
                    raise ValueError(f"Invalid status. Must be one of: {[e.value for e in ReminderStatus]}")
        return v


class ReminderLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    scheduled_time: datetime
    message: str
    status: ReminderStatus
    created_at: datetime


@router.post("/log", response_model=ReminderLogResponse, status_code=status.HTTP_201_CREATED)
def log_reminder(
    reminder_data: ReminderLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Log a reminder delivery (for Person C's reminder engine)"""
    # Verify the reminder is for the current user
    if reminder_data.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to log reminders for this user"
        )
    
    # Pydantic validator already converted status to uppercase enum
    reminder = Reminder(
        user_id=reminder_data.user_id,
        scheduled_time=reminder_data.scheduled_time,
        message=reminder_data.message,
        status=reminder_data.status
    )
    
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    
    return reminder


@router.get("/status")
def get_reminder_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get reminder status for frontend"""
    # Get recent reminders (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    reminders = db.query(Reminder).filter(
        Reminder.user_id == current_user.id,
        Reminder.created_at >= thirty_days_ago
    ).order_by(Reminder.created_at.desc()).limit(50).all()
    
    # Count by status
    status_counts = {}
    for status in ReminderStatus:
        status_counts[status.value] = len([r for r in reminders if r.status == status])
    
    return {
        "user_id": current_user.id,
        "total_reminders_30d": len(reminders),
        "status_counts": status_counts,
        "recent_reminders": [
            {
                "id": r.id,
                "scheduled_time": r.scheduled_time.isoformat(),
                "message": r.message,
                "status": r.status.value,
                "created_at": r.created_at.isoformat()
            }
            for r in reminders[:10]
        ]
    }

