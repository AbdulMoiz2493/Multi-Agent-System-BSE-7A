"""
Pydantic schemas for API request/response validation
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# ============== Similarity Detection Models ==============

class SimilarityRequest(BaseModel):
    """Request model for similarity check endpoint"""
    text1: str = Field(..., description="First text to compare")
    text2: Optional[str] = Field(None, description="Second text to compare (optional)")


class SimilarityResponse(BaseModel):
    """Response model for similarity check endpoint"""
    similarity_score: float = Field(..., description="Similarity score between 0 and 1")
    is_plagiarized: bool = Field(..., description="Whether the text is considered plagiarized")
    source: Optional[str] = Field(None, description="Source of the plagiarized content if detected")


# ============== Rephrasing Models ==============

class RephrasedSentence(BaseModel):
    """Model for a rephrased sentence with comparison"""
    original_sentence: str = Field(..., description="Original sentence")
    rephrased_sentence: str = Field(..., description="Rephrased version of the sentence")
    similarity_score: float = Field(0.0, description="Similarity score with original")
    is_plagiarized: bool = Field(False, description="Whether this sentence was flagged as plagiarized")
    source_url: Optional[str] = Field(None, description="URL of the source if plagiarism detected")
    source_text: Optional[str] = Field(None, description="Text from the source that matched")


class PlagiarismSource(BaseModel):
    """Model for a plagiarism source match"""
    url: str = Field(..., description="URL of the matching source")
    title: str = Field(..., description="Title of the source")
    matched_text: str = Field(..., description="Text that matched from the source")
    similarity_score: float = Field(..., description="Similarity score with the source")


class RephraseRequest(BaseModel):
    """Request model for text rephrasing endpoint"""
    text: str = Field(..., description="Text to rephrase")
    preserve_meaning: bool = Field(True, description="Whether to preserve the original meaning")


class RephraseResponse(BaseModel):
    """Response model for text rephrasing endpoint"""
    original_text: str = Field(..., description="Original text")
    rephrased_text: str = Field(..., description="Rephrased text")
    sentences: List[RephrasedSentence] = Field(..., description="List of rephrased sentences")


# ============== Main Processing Models (PPA) ==============

class PPAInput(BaseModel):
    """Input model for the main processing endpoint"""
    student_text: str = Field(..., description="Student's text to check and rephrase")
    submission_id: str = Field(..., description="Unique submission identifier")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), 
                          description="Timestamp of the submission")


class PPAProcessing(BaseModel):
    """Processing configuration for the main endpoint"""
    comparison_sources: List[str] = Field(default_factory=list, 
                                          description="Reference texts to compare against")
    preserve_meaning: bool = Field(True, description="Whether to preserve the original meaning")
    improve_originality: bool = Field(True, description="Whether to improve text originality")


class PPARequest(BaseModel):
    """Main request model for the process-text endpoint"""
    student_id: str = Field(..., description="Student identifier")
    input: PPAInput = Field(..., description="Input data containing the student text")
    processing: PPAProcessing = Field(default_factory=PPAProcessing, 
                                      description="Processing configuration")


class PPAOutput(BaseModel):
    """Output model containing processing results"""
    rephrased_text: List[RephrasedSentence] = Field(..., 
                                                     description="List of rephrased sentences")
    pledge_percentage: float = Field(..., 
                                     description="Originality percentage (0-100)")
    is_plagiarized: bool = Field(..., description="Overall plagiarism status")
    plagiarism_detected: bool = Field(..., 
                                      description="Whether any plagiarism was detected")
    feedback: str = Field(..., description="Feedback message for the student")


class PPAResponse(BaseModel):
    """Main response model for the process-text endpoint"""
    student_id: str = Field(..., description="Student identifier")
    submission_id: str = Field(..., description="Submission identifier")
    output: PPAOutput = Field(..., description="Processing output")
    timestamp: str = Field(..., description="Response timestamp")
