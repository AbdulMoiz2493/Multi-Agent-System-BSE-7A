"""
Nodes package for Lecture Insight Agent workflow
"""

from agents.lecture_insight.nodes.transcription import transcribe_audio
from agents.lecture_insight.nodes.summarization import summarize_content
from agents.lecture_insight.nodes.gap_analysis import analyze_gaps
from agents.lecture_insight.nodes.search import search_resources
from agents.lecture_insight.nodes.aggregation import aggregate_results

__all__ = [
    "transcribe_audio",
    "summarize_content",
    "analyze_gaps",
    "search_resources",
    "aggregate_results"
]
