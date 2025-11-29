import logging
import uuid
import os
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
from datetime import datetime
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
root_env = Path(__file__).parent.parent.parent / '.env'

if env_path.exists():
    load_dotenv(env_path, override=True)
    _logger.info(f"✅ Loaded .env from {env_path}")
elif root_env.exists():
    load_dotenv(root_env, override=True)
    _logger.info(f"✅ Loaded .env from {root_env}")
else:
    _logger.warning(f"⚠️  No .env file found at {env_path} or {root_env}")

# Log API key status (first 20 chars only for security)
api_key = os.getenv('GEMINI_API_KEY', '')
if api_key:
    _logger.info(f"✅ GEMINI_API_KEY loaded: {api_key[:20]}...")
else:
    _logger.warning("⚠️  GEMINI_API_KEY not found in environment")

from shared.models import TaskEnvelope, CompletionReport
from agents.assignment_coach import ltm, coach_agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    await ltm.init_db()
    yield

app = FastAPI(lifespan=lifespan)

@app.get('/health')
async def health():
    return {"status": "healthy", "version": "1.0.0", "timestamp": datetime.utcnow().isoformat()}

@app.post('/process', response_model=CompletionReport)
async def process_task(req: Request):
    try:
        body = await req.json()
        task_envelope = TaskEnvelope(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request body: {e}")

    # Extract the assignment coach specific payload
    payload = task_envelope.task.parameters.get("request")
    if not payload:
        return CompletionReport(
            message_id=str(uuid.uuid4()),
            sender="AssignmentCoachAgent",
            recipient=task_envelope.sender,
            related_message_id=task_envelope.message_id,
            status="FAILURE",
            results={"error": "Missing 'request' in task parameters"}
        )

    # Check LTM first for similar assignments
    cached_output = await ltm.lookup(payload)
    if cached_output:
        return CompletionReport(
            message_id=str(uuid.uuid4()),
            sender="AssignmentCoachAgent",
            recipient=task_envelope.sender,
            related_message_id=task_envelope.message_id,
            status="SUCCESS",
            results={"output": cached_output, "cached": True}
        )

    # Process with LangGraph agent
    result = await coach_agent.process_assignment_request(payload)

    if "error" in result:
        return CompletionReport(
            message_id=str(uuid.uuid4()),
            sender="AssignmentCoachAgent",
            recipient=task_envelope.sender,
            related_message_id=task_envelope.message_id,
            status="FAILURE",
            results={"error": result["error"]}
        )

    # Save to LTM and return success
    await ltm.save(payload, result["output"])
    return CompletionReport(
        message_id=str(uuid.uuid4()),
        sender="AssignmentCoachAgent",
        recipient=task_envelope.sender,
        related_message_id=task_envelope.message_id,
        status="SUCCESS",
        results=result
    )
