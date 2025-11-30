"""
LangGraph Workflow Definition - Orchestrates the lecture processing pipeline

Architecture:
- Singleton compiled workflow (created once, reused forever)
- Conditional error handling (graceful degradation)
- Type-safe state management with TypedDict
- Optimized execution with proper state initialization
"""

import logging
import time
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from agents.lecture_insight.models import LectureState
from agents.lecture_insight.nodes import (
    transcribe_audio,
    summarize_content,
    analyze_gaps,
    search_resources,
    aggregate_results
)

_logger = logging.getLogger(__name__)

# Singleton: Workflow compiled once at module load
_COMPILED_WORKFLOW = None


def _should_continue_after_transcription(state: LectureState) -> Literal["summarize", "end"]:
    """
    Conditional edge: Only continue if transcription succeeded.
    Implements graceful degradation on critical failures.
    """
    if state.get("error") or not state.get("transcript"):
        _logger.error("⚠️ Transcription failed, terminating workflow early")
        return "end"
    return "summarize"


def _should_continue_after_summarization(state: LectureState) -> Literal["analyze_gaps", "end"]:
    """
    Conditional edge: Only continue if summarization succeeded.
    Without keywords, search phase would fail anyway.
    """
    if state.get("error") or not state.get("keywords"):
        _logger.error("⚠️ Summarization failed, terminating workflow early")
        return "end"
    return "analyze_gaps"


def _get_compiled_workflow():
    """
    Get or create the singleton compiled workflow.
    
    This is the "Steve Jobs" way: Build once, perfectly. Reuse forever.
    Workflow compilation is expensive - we do it once at module initialization.
    
    Architecture:
    - Type-safe state with LectureState TypedDict
    - Conditional edges for graceful error handling
    - Linear pipeline with early termination on critical failures
    
    Flow:
    START → transcribe → [error check] → summarize → [error check] 
    → analyze_gaps → search → aggregate → END
    
    Returns:
        Compiled StateGraph ready for execution
    """
    global _COMPILED_WORKFLOW
    
    if _COMPILED_WORKFLOW is not None:
        return _COMPILED_WORKFLOW
    
    _logger.info("🏗️ Building LangGraph workflow (one-time compilation)...")
    
    # Create graph with type-safe state
    workflow = StateGraph(LectureState)
    
    # Add processing nodes
    workflow.add_node("transcribe", transcribe_audio)
    workflow.add_node("summarize", summarize_content)
    workflow.add_node("analyze_gaps", analyze_gaps)
    workflow.add_node("search", search_resources)
    workflow.add_node("aggregate", aggregate_results)
    
    # Define flow with conditional error handling
    workflow.set_entry_point("transcribe")
    
    # Conditional: Only summarize if transcription succeeded
    workflow.add_conditional_edges(
        "transcribe",
        _should_continue_after_transcription,
        {"summarize": "summarize", "end": END}
    )
    
    # Conditional: Only continue if summarization succeeded
    workflow.add_conditional_edges(
        "summarize",
        _should_continue_after_summarization,
        {"analyze_gaps": "analyze_gaps", "end": END}
    )
    
    # Linear flow for remaining stages (non-critical failures)
    workflow.add_edge("analyze_gaps", "search")
    workflow.add_edge("search", "aggregate")
    workflow.add_edge("aggregate", END)
    
    _COMPILED_WORKFLOW = workflow.compile()
    _logger.info("✅ Workflow compiled successfully (cached for reuse)")
    
    return _COMPILED_WORKFLOW


def get_workflow():
    """
    Public API: Get the compiled workflow for external use.
    
    Use this when you need direct access to the workflow object
    (e.g., for visualization, debugging, or custom execution).
    
    Returns:
        Compiled StateGraph
        
    Example:
        >>> workflow = get_workflow()
        >>> state = {"audio_input": {...}, ...}
        >>> result = await workflow.ainvoke(state)
    """
    return _get_compiled_workflow()


async def execute_workflow(input_data: Dict[str, Any]) -> LectureState:
    """
    Execute the lecture processing workflow end-to-end.
    
    This is the primary entry point for workflow execution.
    Handles state initialization, validation, error recovery, and timing.
    
    Args:
        input_data: Dict with required keys:
            - audio_input: AudioInput dict (type, data, format)
            - user_id: User identifier
            - preferences: ProcessingPreferences dict (optional)
        
    Returns:
        LectureState with all processing results:
            - transcript: Transcribed text
            - summary: Content summary
            - keywords: Extracted keywords
            - learning_gaps: Identified prerequisites
            - articles: List of Article dicts
            - videos: List of Video dicts
            - audio_duration: Duration in seconds
            - error: Error message if any failures occurred
    
    Example:
        >>> result = await execute_workflow({
        ...     "audio_input": {"type": "url", "data": "...", "format": "mp3"},
        ...     "user_id": "user-456",
        ...     "preferences": {"resource_limit": 10}
        ... })
        >>> print(result["summary"])
    """
    start_time = time.time()
    user_id = input_data.get('user_id', 'anonymous')
    
    # Validate required inputs (fail fast)
    if not input_data.get('audio_input'):
        _logger.error("❌ Missing required field: audio_input")
        return {
            "error": "Missing required field: audio_input",
            "transcript": "",
            "summary": "",
            "keywords": [],
            "learning_gaps": [],
            "articles": [],
            "videos": [],
            "audio_duration": 0
        }
    
    _logger.info(f"🚀 Starting workflow execution for user {user_id}")
    
    try:
        # Initialize state with defaults (TypedDict compliant)
        state: LectureState = {
            **input_data,  # type: ignore
            "start_time": start_time,
            "transcript": "",
            "summary": "",
            "keywords": [],
            "learning_gaps": [],
            "articles": [],
            "videos": [],
            "audio_duration": 0,
            "error": ""
        }
        
        # Get compiled workflow (singleton, cached after first call)
        workflow = _get_compiled_workflow()
        
        # Execute workflow (async state machine execution)
        final_state: LectureState = await workflow.ainvoke(state)
        
        processing_time = time.time() - start_time
        
        if final_state.get("error"):
            _logger.warning(f"⚠️ Workflow completed with errors in {processing_time:.2f}s: {final_state['error']}")
        else:
            _logger.info(f"✅ Workflow completed successfully in {processing_time:.2f}s")
        
        return final_state
        
    except Exception as e:
        processing_time = time.time() - start_time
        _logger.error(f"❌ Workflow execution failed after {processing_time:.2f}s: {e}")
        
        # Return error state (graceful degradation)
        return {
            **input_data,  # type: ignore
            "error": f"Workflow error: {str(e)}",
            "transcript": "",
            "summary": "",
            "keywords": [],
            "learning_gaps": [],
            "articles": [],
            "videos": [],
            "audio_duration": 0
        }


def state_to_output(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert workflow state to LectureInsightOutput format.
    
    Converts structured summary dict to PRD-compliant string format.
    
    Args:
        state: Final workflow state
        
    Returns:
        Output dict matching LectureInsightOutput model
    """
    processing_time = time.time() - state.get("start_time", time.time())
    
    # Convert structured summary dict to string (PRD requires string)
    summary_data = state.get("summary", "")
    if isinstance(summary_data, dict):
        # Format structured summary as readable text
        summary_parts = []
        
        if summary_data.get("title"):
            summary_parts.append(f"Title: {summary_data['title']}")
        
        if summary_data.get("summary"):
            summary_parts.append(f"\n{summary_data['summary']}")
        
        if summary_data.get("key_points"):
            summary_parts.append("\n\nKey Points:")
            for i, point in enumerate(summary_data["key_points"], 1):
                summary_parts.append(f"{i}. {point}")
        
        if summary_data.get("main_concepts"):
            summary_parts.append("\n\nMain Concepts: " + ", ".join(summary_data["main_concepts"]))
        
        summary_text = "\n".join(summary_parts)
    else:
        summary_text = str(summary_data) if summary_data else ""
    
    return {
        "transcript": state.get("transcript", ""),
        "summary": summary_text,
        "keywords": state.get("keywords", []),
        "learning_gaps": state.get("learning_gaps", []),
        "resources": {
            "articles": state.get("articles", []),
            "videos": state.get("videos", [])
        },
        "metadata": {
            "processing_time_seconds": round(processing_time, 2),
            "audio_duration_seconds": state.get("audio_duration", 0),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    }
