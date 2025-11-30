"""
Lecture Insight Agent - Data Models
Defines Pydantic models for input/output as per PRD specification.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


# ============================================================================
# INPUT MODELS
# ============================================================================

class AudioInput(BaseModel):
    """Audio input specification."""
    type: Literal["base64", "url", "stream"]
    data: str  # base64 encoded data or URL
    format: Literal["wav", "mp3", "m4a"]


class ProcessingPreferences(BaseModel):
    """User preferences for processing."""
    resource_limit: int = 10
    language: str = "en"
    include_videos: bool = True
    include_articles: bool = True


class LectureInsightInput(BaseModel):
    """Main input model for lecture processing."""
    audio_input: AudioInput
    user_id: str
    preferences: ProcessingPreferences = Field(default_factory=ProcessingPreferences)


# ============================================================================
# OUTPUT MODELS
# ============================================================================

class Article(BaseModel):
    """Article resource model."""
    title: str
    url: str
    description: str
    source: str = "web_search"
    relevance_score: float


class Video(BaseModel):
    """Video resource model."""
    title: str
    url: str
    thumbnail: str
    channel: str
    duration: str
    source: str = "video_platform"
    relevance_score: float


class Resources(BaseModel):
    """Collection of educational resources."""
    articles: List[Article] = Field(default_factory=list)
    videos: List[Video] = Field(default_factory=list)


class ProcessingMetadata(BaseModel):
    """Metadata about the processing operation."""
    processing_time_seconds: float
    audio_duration_seconds: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LectureInsightOutput(BaseModel):
    """Main output model for lecture processing."""
    transcript: str
    summary: str
    keywords: List[str]
    learning_gaps: List[str] = Field(default_factory=list)
    resources: Resources
    metadata: ProcessingMetadata


# ============================================================================
# LANGGRAPH STATE MODEL
# ============================================================================

from typing import TypedDict

class LectureState(TypedDict, total=False):
    """
    State object that flows through the LangGraph workflow.
    This represents the complete state at any point in the processing pipeline.
    Uses TypedDict for LangGraph compatibility and performance.
    """
    # Input data (required)
    audio_input: dict  # AudioInput as dict
    user_id: str
    preferences: dict  # ProcessingPreferences as dict
    
    # Processing results (populated by nodes)
    transcript: str
    summary: str
    keywords: List[str]
    learning_gaps: List[str]
    articles: List[dict]  # List[Article] as dicts
    videos: List[dict]    # List[Video] as dicts
    
    # Metadata
    start_time: float
    audio_duration: float
    
    # Error tracking
    error: str
