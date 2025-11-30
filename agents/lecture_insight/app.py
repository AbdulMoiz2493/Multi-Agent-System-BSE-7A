"""
Lecture Insight Agent - FastAPI Application
Worker agent that processes lecture audio and returns educational resources.
"""

import logging
import uuid
import time
import os
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    logging.info(f"✅ Loaded environment from: {env_path}")
else:
    logging.warning(f"⚠️ No .env file found at: {env_path}")

from shared.models import TaskEnvelope, CompletionReport
from agents.lecture_insight.models import LectureInsightInput, LectureInsightOutput
from agents.lecture_insight import ltm
from agents.lecture_insight.workflow import execute_workflow, state_to_output

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup, cleanup on shutdown."""
    _logger.info("🎓 Lecture Insight Agent starting up...")
    await ltm.init_db()
    # TODO: Initialize LangGraph workflow
    yield
    _logger.info("🎓 Lecture Insight Agent shutting down...")


app = FastAPI(
    title="Lecture Insight Agent",
    description="Processes lecture audio and returns curated educational resources",
    version="1.0.0",
    lifespan=lifespan
)


@app.get('/health')
async def health():
    """Health check endpoint - standard format for supervisor."""
    return {"status": "healthy"}


@app.get('/api/v1/health')
async def health_detailed():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "agent": "lecture-insight",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get('/api/v1/agent-info')
async def agent_info():
    """Agent capabilities and information."""
    return {
        "agent_id": "lecture-insight-v1",
        "agent_name": "Lecture Insight Agent",
        "description": "Processes lecture audio and returns curated learning materials",
        "capabilities": [
            "audio-transcription",
            "content-summarization",
            "keyword-extraction",
            "educational-resource-search"
        ],
        "supported_formats": ["wav", "mp3", "m4a"],
        "version": "1.0.0",
        "endpoint": "/api/v1/process-lecture",
        "method": "POST",
        "timeout_seconds": 30
    }


@app.post('/process', response_model=CompletionReport)
async def process_task(req: Request):
    """
    Supervisor communication endpoint.
    Receives TaskEnvelope from supervisor, processes lecture audio, 
    returns CompletionReport with results.
    
    Supports two formats:
    1. Structured format with audio_input object (for direct audio processing)
    2. Simple format with request text (for general queries about lectures)
    """
    start_time = time.time()
    
    # Parse incoming request
    try:
        body = await req.json()
        task_envelope = TaskEnvelope(**body)
    except Exception as e:
        _logger.error(f"Invalid request body: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid request body: {e}")
    
    _logger.info(f"📥 Received task: {task_envelope.message_id}")
    
    params = task_envelope.task.parameters or {}
    
    # Check for structured agent format (agent_name, intent, payload)
    if "agent_name" in params and "payload" in params:
        params = params.get("payload", {})
    
    # Check for 'data' wrapper
    if "data" in params and isinstance(params.get("data"), dict):
        params = params.get("data")
    
    # Try to extract audio_input from various locations
    audio_input = params.get("audio_input")
    
    # If no audio_input, check if this is a URL-based request
    if not audio_input:
        audio_url = params.get("audio_url") or params.get("url")
        audio_format = params.get("format", "mp3")
        if audio_url:
            audio_input = {
                "type": "url",
                "data": audio_url,
                "format": audio_format
            }
    
    # If still no audio_input, this might be a general query
    if not audio_input:
        user_request = params.get("request") or params.get("query") or ""
        
        # Return helpful message about what this agent does
        return CompletionReport(
            message_id=str(uuid.uuid4()),
            sender="LectureInsightAgent",
            recipient=task_envelope.sender,
            related_message_id=task_envelope.message_id,
            status="SUCCESS",
            results={
                "output": f"""## Lecture Insight Agent

I can help you analyze lecture recordings and generate study materials! 

**What I can do:**
- 🎤 Transcribe lecture audio (MP3, WAV, M4A)
- 📝 Generate comprehensive lecture summaries
- 🔑 Extract key concepts and keywords
- 📚 Find related educational resources (articles & videos)
- 🎯 Identify learning gaps and prerequisites

**To use me, please provide:**
1. A URL to your lecture audio file, OR
2. Base64-encoded audio data

**Example request:**
"Analyze this lecture: https://example.com/lecture.mp3"

Your query: "{user_request}"

Please provide a lecture audio URL or upload audio for me to analyze!""",
                "requires_audio": True,
                "supported_formats": ["mp3", "wav", "m4a"]
            }
        )
    
    # Extract and validate input parameters
    try:
        input_data = LectureInsightInput(
            audio_input=audio_input,
            user_id=params.get("user_id") or params.get("student_id") or "default_user",
            preferences=params.get("preferences", {})
        )
    except Exception as e:
        _logger.error(f"Invalid task parameters: {e}")
        return CompletionReport(
            message_id=str(uuid.uuid4()),
            sender="LectureInsightAgent",
            recipient=task_envelope.sender,
            related_message_id=task_envelope.message_id,
            status="FAILURE",
            results={"error": f"Invalid parameters: {str(e)}"}
        )
    
    # Check LTM cache first
    cached_output = await ltm.lookup(
        audio_data=input_data.audio_input.data,
        preferences=input_data.preferences.model_dump()
    )
    if cached_output:
        _logger.info(f"⚡ Returning cached result for user {input_data.user_id}")
        return CompletionReport(
            message_id=str(uuid.uuid4()),
            sender="LectureInsightAgent",
            recipient=task_envelope.sender,
            related_message_id=task_envelope.message_id,
            status="SUCCESS",
            results={"output": cached_output, "cached": True}
        )
    
    # Execute LangGraph workflow
    try:
        # Prepare workflow input state
        workflow_input = {
            "audio_input": input_data.audio_input.model_dump(),
            "user_id": input_data.user_id,
            "preferences": input_data.preferences.model_dump()
        }
        
        # Run workflow
        _logger.info(f"🔄 Executing workflow for user {input_data.user_id}")
        final_state = await execute_workflow(workflow_input)
        
        # Check for errors
        if final_state.get("error"):
            _logger.error(f"Workflow error: {final_state['error']}")
            return CompletionReport(
                message_id=str(uuid.uuid4()),
                sender="LectureInsightAgent",
                recipient=task_envelope.sender,
                related_message_id=task_envelope.message_id,
                status="FAILURE",
                results={"error": final_state["error"]}
            )
        
        # Convert state to output format
        output = state_to_output(final_state)
        
        # Save to LTM cache for future requests
        await ltm.save(
            audio_data=input_data.audio_input.data,
            preferences=input_data.preferences.model_dump(),
            output=output
        )
        
        _logger.info(f"✅ Task completed: {task_envelope.message_id}")
        
        return CompletionReport(
            message_id=str(uuid.uuid4()),
            sender="LectureInsightAgent",
            recipient=task_envelope.sender,
            related_message_id=task_envelope.message_id,
            status="SUCCESS",
            results={"output": output, "cached": False}
        )
        
    except Exception as e:
        _logger.exception(f"❌ Task failed: {e}")
        return CompletionReport(
            message_id=str(uuid.uuid4()),
            sender="LectureInsightAgent",
            recipient=task_envelope.sender,
            related_message_id=task_envelope.message_id,
            status="FAILURE",
            results={"error": str(e)}
        )


@app.post('/api/v1/process-lecture')
async def process_lecture(input_data: LectureInsightInput) -> LectureInsightOutput:
    """
    PRD-compliant endpoint for direct lecture processing.
    Accepts audio input and preferences, returns structured educational resources.
    
    This is the main endpoint documented in the PRD for supervisor integration.
    """
    start_time = time.time()
    
    _logger.info(f"📥 Received lecture processing request from user {input_data.user_id}")
    
    # Check LTM cache first
    cached_output = await ltm.lookup(
        audio_data=input_data.audio_input.data,
        preferences=input_data.preferences.model_dump()
    )
    if cached_output:
        _logger.info(f"⚡ Returning cached result for user {input_data.user_id}")
        # Update processing_time for this request
        cached_output["metadata"]["processing_time_seconds"] = time.time() - start_time
        
        # Convert cached summary if it's a dict (backward compatibility)
        if isinstance(cached_output.get("summary"), dict):
            summary_data = cached_output["summary"]
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
            
            cached_output["summary"] = "\n".join(summary_parts)
        
        return LectureInsightOutput(**cached_output)
    
    # Execute LangGraph workflow
    try:
        # Prepare workflow input state
        workflow_input = {
            "audio_input": input_data.audio_input.model_dump(),
            "user_id": input_data.user_id,
            "preferences": input_data.preferences.model_dump(),
            "start_time": start_time
        }
        
        # Run workflow
        _logger.info(f"🔄 Executing workflow for user {input_data.user_id}")
        final_state = await execute_workflow(workflow_input)
        
        # Check for errors
        if final_state.get("error"):
            error_msg = final_state["error"]
            _logger.error(f"Workflow error: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": True,
                    "message": error_msg,
                    "code": "WORKFLOW_ERROR",
                    "user_id": input_data.user_id
                }
            )
        
        # Convert state to output format
        output = state_to_output(final_state)
        
        # Save to LTM cache for future requests
        await ltm.save(
            audio_data=input_data.audio_input.data,
            preferences=input_data.preferences.model_dump(),
            output=output
        )
        
        processing_time = time.time() - start_time
        _logger.info(
            f"✅ Lecture processed successfully for user {input_data.user_id} "
            f"in {processing_time:.2f}s"
        )
        
        return LectureInsightOutput(**output)
        
    except HTTPException:
        raise
    except Exception as e:
        _logger.exception(f"❌ Lecture processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "message": str(e),
                "code": "PROCESSING_ERROR",
                "user_id": input_data.user_id
            }
        )
