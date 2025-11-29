from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from app.core.database import get_db
from app.models.user import User
from app.models.study_session import StudySession
from app.schemas.session import (
    StudySessionCreate,
    StudySessionUpdate,
    StudySessionResponse,
    StudySessionListResponse
)
from app.api.deps import get_current_user
from app.crud import session as crud_session

router = APIRouter()


@router.post("", response_model=StudySessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    session_data: StudySessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new study session"""
    return crud_session.create_session(db, current_user.id, session_data)


@router.get("", response_model=StudySessionListResponse)
def list_sessions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    course_name: Optional[str] = Query(None, description="Filter by course name"),
    start_date: Optional[datetime] = Query(None, description="Filter sessions from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter sessions until this date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's study sessions with pagination and filtering"""
    skip = (page - 1) * page_size
    sessions, total = crud_session.get_user_sessions(
        db,
        current_user.id,
        skip=skip,
        limit=page_size,
        course_name=course_name,
        start_date=start_date,
        end_date=end_date
    )
    
    return {
        "items": sessions,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{session_id}", response_model=StudySessionResponse)
def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a study session by ID"""
    session = crud_session.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found"
        )
    return session


@router.put("/{session_id}", response_model=StudySessionResponse)
def update_session(
    session_id: int,
    session_update: StudySessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a study session"""
    session = crud_session.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found"
        )
    
    return crud_session.update_session(db, session, session_update)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a study session"""
    session = crud_session.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found"
        )
    
    crud_session.delete_session(db, session)
    return None

