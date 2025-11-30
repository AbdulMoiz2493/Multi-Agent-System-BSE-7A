"""
Plagiarism Prevention Agent (PPA)
Main FastAPI application entry point
"""

# Import config first to set environment variables before other imports
import app.config  # noqa: F401

import logging
import uuid
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routers import similarity, rephrase, process
from app.database import init_db
from app.services.plagiarism_processor import PlagiarismProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Initialize processor (lazy loading)
_processor = None

def get_processor() -> PlagiarismProcessor:
    """Get or create plagiarism processor instance"""
    global _processor
    if _processor is None:
        _processor = PlagiarismProcessor()
    return _processor

app = FastAPI(
    title="Plagiarism Prevention Agent",
    description="AI agent for detecting plagiarism and rephrasing text to improve originality",
    version="1.0.0"
)

# CORS middleware - Allow all origins for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(similarity.router, prefix="/api/v1", tags=["Similarity"])
app.include_router(rephrase.router, prefix="/api/v1", tags=["Rephrasing"])
app.include_router(process.router, prefix="/api/v1", tags=["Processing"])

# Track if models are loaded
_models_loaded = False
_models_loading = False

def _load_models_background():
    """Load ML models in a background thread"""
    global _models_loaded, _models_loading
    _models_loading = True
    logger.info("Pre-loading ML models in background (this may take a few minutes)...")
    try:
        get_processor()
        _models_loaded = True
        logger.info("ML models loaded successfully!")
    except Exception as e:
        logger.error(f"Failed to pre-load ML models: {e}")
    finally:
        _models_loading = False

@app.on_event("startup")
async def startup_event():
    """Initialize database and start model loading in background"""
    init_db()
    # Start loading models in a background thread so server can start immediately
    import threading
    thread = threading.Thread(target=_load_models_background, daemon=True)
    thread.start()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Plagiarism Prevention Agent API",
        "version": "1.0.0",
        "models_loaded": _models_loaded,
        "models_loading": _models_loading,
        "endpoints": {
            "check_similarity": "/api/v1/check-similarity",
            "rephrase_text": "/api/v1/rephrase-text",
            "process_text": "/api/v1/process-text"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "models_loaded": _models_loaded}



@app.post("/process")
async def process_supervisor_request(req: Request):
    """
    Process endpoint for Supervisor Agent communication.
    Accepts TaskEnvelope format and returns CompletionReport format.
    """
    try:
        # Check if models are still loading
        if _models_loading and not _models_loaded:
            logger.info("Models still loading, returning loading status...")
            return {
                "message_id": str(uuid.uuid4()),
                "sender": "plagiarism_prevention_agent",
                "status": "FAILURE",
                "results": {
                    "error": "Models are still loading. Please try again in a few moments.",
                    "output": "The plagiarism detection models are still loading. This typically takes 2-3 minutes after startup. Please try again shortly."
                }
            }
        
        body = await req.json()
        logger.info(f"Received /process request: {list(body.keys())}")
        
        # Extract task parameters from TaskEnvelope
        task = body.get("task", {})
        params = task.get("parameters", {})
        
        # Try to get text from various possible locations
        text_to_check = None
        
        # Check for agent-specific payload format
        if "payload" in params and isinstance(params["payload"], dict):
            payload = params["payload"]
            if "input" in payload and isinstance(payload["input"], dict):
                text_to_check = payload["input"].get("student_text")
            elif "student_text" in payload:
                text_to_check = payload["student_text"]
            elif "text" in payload:
                text_to_check = payload["text"]
        
        # Check data field
        if not text_to_check and "data" in params:
            data = params["data"]
            if isinstance(data, dict):
                text_to_check = data.get("student_text") or data.get("text") or data.get("content")
            elif isinstance(data, str):
                text_to_check = data
        
        # Check direct fields
        if not text_to_check:
            text_to_check = params.get("student_text") or params.get("text") or params.get("content")
        
        # Fall back to the raw request field
        if not text_to_check:
            text_to_check = params.get("request") or params.get("original_request")
            # Try to extract text after colon (e.g., "Check this for plagiarism: <text>")
            if text_to_check and ":" in text_to_check:
                parts = text_to_check.split(":", 1)
                if len(parts) > 1 and len(parts[1].strip()) > 20:
                    text_to_check = parts[1].strip()
        
        if not text_to_check:
            logger.warning("No text found in request")
            return {
                "message_id": str(uuid.uuid4()),
                "sender": "plagiarism_prevention_agent",
                "status": "FAILURE",
                "results": {
                    "error": "No text provided. Please include text to check for plagiarism.",
                    "output": "I need text content to check for plagiarism. Please provide the text you want me to analyze."
                }
            }
        
        logger.info(f"Processing text ({len(text_to_check)} chars): {text_to_check[:100]}...")
        
        # Process the text
        processor = get_processor()
        rephrased_sentences, pledge_percentage, is_plagiarized, feedback = processor.process_text(
            student_text=text_to_check,
            comparison_sources=[],
            preserve_meaning=True,
            improve_originality=True,
            check_online=True
        )
        
        # Build response
        rephrased_text = " ".join([sent.rephrased_sentence for sent in rephrased_sentences])
        
        result_output = {
            "original_text": text_to_check,
            "rephrased_text": rephrased_text,
            "originality_score": pledge_percentage,
            "is_plagiarized": is_plagiarized,
            "feedback": feedback,
            "sentences": [
                {
                    "original": sent.original_sentence,
                    "rephrased": sent.rephrased_sentence,
                    "similarity_score": sent.similarity_score,
                    "is_plagiarized": sent.is_plagiarized,
                    "source_url": sent.source_url
                }
                for sent in rephrased_sentences
            ]
        }
        
        # Format human-readable output
        output_text = f"""## Plagiarism Analysis Results

**Originality Score:** {pledge_percentage:.1f}%
**Plagiarism Detected:** {"Yes" if is_plagiarized else "No"}

### Feedback
{feedback}

### Rephrased Text
{rephrased_text}
"""
        
        logger.info(f"Successfully processed text. Originality: {pledge_percentage}%, Plagiarized: {is_plagiarized}")
        
        return {
            "message_id": str(uuid.uuid4()),
            "sender": "plagiarism_prevention_agent",
            "status": "SUCCESS",
            "results": {
                "output": output_text,
                "data": result_output
            }
        }
        
    except Exception as e:
        logger.exception(f"Error processing request: {e}")
        return {
            "message_id": str(uuid.uuid4()),
            "sender": "plagiarism_prevention_agent",
            "status": "FAILURE",
            "results": {
                "error": str(e),
                "output": f"An error occurred while processing your request: {str(e)}"
            }
        }


