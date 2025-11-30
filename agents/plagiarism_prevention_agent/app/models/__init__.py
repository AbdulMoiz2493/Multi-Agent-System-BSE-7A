"""
Pydantic models for the Plagiarism Prevention Agent
"""

from app.models.schemas import (
    SimilarityRequest,
    SimilarityResponse,
    RephraseRequest,
    RephraseResponse,
    RephrasedSentence,
    PlagiarismSource,
    PPAInput,
    PPAProcessing,
    PPARequest,
    PPAOutput,
    PPAResponse
)

__all__ = [
    "SimilarityRequest",
    "SimilarityResponse",
    "RephraseRequest",
    "RephraseResponse",
    "RephrasedSentence",
    "PlagiarismSource",
    "PPAInput",
    "PPAProcessing",
    "PPARequest",
    "PPAOutput",
    "PPAResponse"
]
