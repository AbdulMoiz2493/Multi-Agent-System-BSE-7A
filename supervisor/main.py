# supervisor/main.py
import logging
import asyncio
import yaml
from fastapi import FastAPI, Depends, HTTPException, Body, Query, UploadFile, File
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel

from shared.models import RequestPayload, RequestResponse, User
from supervisor import registry, memory_manager, auth, routing
from supervisor.worker_client import forward_to_agent
from supervisor.gemini_chat_orchestrator import get_orchestrator

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

with open("config/settings.yaml", "r") as f:
    config = yaml.safe_load(f)

HEALTH_CHECK_INTERVAL = config['supervisor'].get('health_check_interval', 15)
MAX_CLARIFICATION_ATTEMPTS = 3  # Maximum times to ask for clarification before giving up

# Request model that includes conversation context
class EnhancedRequestPayload(BaseModel):
    request: str
    agentId: Optional[str] = None
    autoRoute: bool = True
    conversationId: Optional[str] = None  # For tracking conversation threads
    includeHistory: bool = True  # Whether to use conversation history for context
    # Exam readiness specific fields (passed through from frontend form)
    subject: Optional[str] = None
    assessment_type: Optional[str] = None
    difficulty: Optional[str] = None
    question_count: Optional[int] = None
    type_counts: Optional[Dict[str, int]] = None
    use_rag: Optional[bool] = None
    pdf_input_paths: Optional[List[str]] = None
    rag_top_k: Optional[int] = None
    rag_max_chars: Optional[int] = None
    export_pdf: Optional[bool] = None
    pdf_output_filename: Optional[str] = None

async def periodic_health_checks():
    """Periodically run health checks for all registered agents."""
    while True:
        _logger.info("Running periodic agent health checks...")
        await registry.health_check_agents()
        await asyncio.sleep(HEALTH_CHECK_INTERVAL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    _logger.info("Supervisor starting up...")
    registry.load_registry()
    # Initial health check
    await registry.health_check_agents()
    
    # Start periodic health checks as a background task
    health_check_task = asyncio.create_task(periodic_health_checks())
    
    yield
    
    # On shutdown
    _logger.info("Supervisor shutting down.")
    health_check_task.cancel()
    try:
        await health_check_task
    except asyncio.CancelledError:
        _logger.info("Health check task cancelled successfully.")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post('/api/auth/login')
async def login(req: LoginRequest = Body(...)):
    return auth.login(req.model_dump())

@app.get('/health')
async def health():
    return {"status": "ok"}

@app.post('/api/auth/logout')
async def logout(user: User = Depends(auth.require_auth)):
    return {"message": "Logged out successfully"}

@app.get('/api/auth/me', response_model=User)
async def get_current_user(user: User = Depends(auth.require_auth)):
    return user

@app.get('/api/supervisor/registry')
async def get_registry(user: User = Depends(auth.require_auth)):
    return {"agents": registry.list_agents()}

@app.post('/api/supervisor/request-unified')
async def submit_request_unified(
    payload: EnhancedRequestPayload,
    user: User = Depends(auth.require_auth),
    use_orchestrator: bool = Query(True, description="Use unified Gemini orchestrator")
):
    """
    NEW: Unified Gemini-based chat handler endpoint.
    Uses a single Gemini call to handle intent identification, parameter extraction,
    and agent routing in one conversational flow.
    
    This is the recommended endpoint for new integrations.
    
    Returns either:
    - status="CLARIFICATION_NEEDED" with clarifying_questions (ask user for more info)
    - status="READY_TO_ROUTE" with agent_id and agent_payload (ready to forward to agent)
    """
    user_id = user.id
    user_query = payload.request
    
    try:
        # Get or create orchestrator instance per user
        # In production, you might want to manage orchestrator per conversation_id
        orchestrator = get_orchestrator()
        
        # Store user message in memory
        memory_manager.store_conversation_message(
            user_id=user_id,
            role="user",
            content=user_query
        )
        
        # Process through unified orchestrator
        _logger.info(f"Processing unified request for user {user_id}: {user_query[:100]}...")
        orchestrator_response = await orchestrator.process_message(user_query)
        
        # Convert to dict for JSON response
        response_dict = {
            "status": orchestrator_response.status,
            "agent_id": orchestrator_response.agent_id,
            "confidence": orchestrator_response.confidence,
            "reasoning": orchestrator_response.reasoning,
            "extracted_params": orchestrator_response.extracted_params,
            "clarifying_questions": orchestrator_response.clarifying_questions,
        }
        
        # If ready to route, check agent health and forward
        if orchestrator_response.status == "READY_TO_ROUTE":
            agent_id = orchestrator_response.agent_id
            agent_payload = orchestrator_response.agent_payload
            
            # Verify agent exists and is healthy
            agent = registry.get_agent(agent_id)
            if not agent:
                return {
                    "status": "CLARIFICATION_NEEDED",
                    "agent_id": None,
                    "confidence": 0.0,
                    "reasoning": f"Agent {agent_id} not found in registry",
                    "extracted_params": orchestrator_response.extracted_params,
                    "clarifying_questions": ["Let me rephrase that request. Could you provide more details?"]
                }
            
            if agent.status != "healthy":
                return {
                    "status": "CLARIFICATION_NEEDED",
                    "agent_id": None,
                    "confidence": 0.0,
                    "reasoning": f"Agent {agent_id} is currently {agent.status}",
                    "extracted_params": orchestrator_response.extracted_params,
                    "clarifying_questions": ["The required specialist is currently offline. Please try again in a moment."]
                }
            
            # Forward to agent
            try:
                _logger.info(f"Forwarding to {agent_id} with payload: {agent_payload}")
                
                # Create RequestPayload for forwarding
                forward_payload = RequestPayload(
                    agentId=agent_id,
                    request=user_query,
                    autoRoute=False
                )
                
                # Forward and get response
                agent_response = await forward_to_agent(
                    agent_id, 
                    forward_payload, 
                    agent_specific=agent_payload
                )
                
                # Store in memory and return
                memory_manager.store_conversation_message(
                    user_id=user_id,
                    role="assistant",
                    content=getattr(agent_response, 'response', str(agent_response)),
                    agent_id=agent_id
                )
                
                # Build response with both orchestrator and agent info
                response_content = getattr(agent_response, 'response', str(agent_response))
                response_dict = {
                    "status": "AGENT_RESPONSE",
                    "agent_id": agent_id,
                    "agent_name": agent.name,
                    "response": response_content,
                    "confidence": orchestrator_response.confidence,
                    "reasoning": orchestrator_response.reasoning,
                    "extracted_params": orchestrator_response.extracted_params,
                    "metadata": {
                        "identified_agent": agent_id,
                        "agent_name": agent.name,
                        "confidence": orchestrator_response.confidence,
                        "reasoning": orchestrator_response.reasoning,
                        "extracted_params": orchestrator_response.extracted_params,
                    }
                }
                
                if hasattr(agent_response, 'error') and agent_response.error:
                    response_dict["error"] = agent_response.error.dict() if hasattr(agent_response.error, 'dict') else str(agent_response.error)
                
                return response_dict
                
            except Exception as e:
                _logger.error(f"Error forwarding to agent {agent_id}: {e}")
                return {
                    "status": "ERROR",
                    "agent_id": agent_id,
                    "confidence": 0.0,
                    "reasoning": f"Failed to forward to agent: {str(e)}",
                    "extracted_params": orchestrator_response.extracted_params,
                    "error": str(e)
                }
        
        else:  # CLARIFICATION_NEEDED
            # Just return the clarification response
            response_dict["status"] = "clarification_needed"
            memory_manager.store_conversation_message(
                user_id=user_id,
                role="assistant",
                content=f"Clarification: {response_dict['reasoning']}"
            )
            return response_dict
        
    except Exception as e:
        _logger.error(f"Error in unified request handler: {e}", exc_info=True)
        return {
            "status": "ERROR",
            "agent_id": None,
            "confidence": 0.0,
            "reasoning": f"Error processing request: {str(e)}",
            "extracted_params": {},
            "error": str(e)
        }

@app.post('/api/supervisor/request')
async def submit_request(
    payload: EnhancedRequestPayload, 
    user: User = Depends(auth.require_auth)
):
    """
    Submit a request to the supervisor for routing to appropriate agent.
    Maintains conversation context and handles iterative clarification.
    
    Returns either:
    - RequestResponse: If agent successfully processes the request
    - Clarification request: If user query is ambiguous
    """
    
    user_id = user.id
    user_query = payload.request
    
    # Get conversation history if enabled
    conversation_history = None
    if payload.includeHistory:
        conversation_history = memory_manager.get_conversation_history(user_id, limit=10)
        _logger.info(f"Retrieved {len(conversation_history)} previous messages for context")
    
    # Store user message
    memory_manager.store_conversation_message(
        user_id=user_id,
        role="user",
        content=user_query
    )
    
    # CHECK FOR EXPLICIT EXAM READINESS PARAMETERS
    # If the frontend form sends structured parameters, bypass Gemini extraction
    # and directly route to exam_readiness_agent
    if payload.subject and payload.assessment_type and payload.question_count and payload.type_counts:
        _logger.info(f"Explicit exam parameters detected - bypassing intent identification")
        
        # Build explicit payload for exam_readiness_agent
        explicit_agent_payload = {
            "subject": payload.subject,
            "assessment_type": payload.assessment_type,
            "difficulty": payload.difficulty or "medium",
            "question_count": payload.question_count,
            "type_counts": payload.type_counts,
            "allow_latex": True,
            "created_by": "frontend_form",
            "use_rag": payload.use_rag or False,
            "export_pdf": payload.export_pdf or False,
        }
        
        # Add optional RAG parameters
        if payload.use_rag:
            if payload.pdf_input_paths:
                explicit_agent_payload["pdf_input_paths"] = payload.pdf_input_paths
            if payload.rag_top_k:
                explicit_agent_payload["rag_top_k"] = payload.rag_top_k
            if payload.rag_max_chars:
                explicit_agent_payload["rag_max_chars"] = payload.rag_max_chars
        
        if payload.export_pdf and payload.pdf_output_filename:
            explicit_agent_payload["pdf_output_filename"] = payload.pdf_output_filename
        
        # Check agent health
        agent = registry.get_agent("exam_readiness_agent")
        if not agent:
            return {"status": "ERROR", "error": "exam_readiness_agent not found in registry"}
        
        if agent.status != "healthy":
            return {"status": "ERROR", "error": f"exam_readiness_agent is {agent.status}"}
        
        # Forward to exam_readiness_agent directly
        try:
            forward_payload = RequestPayload(
                agentId="exam_readiness_agent",
                request=user_query,
                autoRoute=False
            )
            
            agent_response = await forward_to_agent(
                "exam_readiness_agent",
                forward_payload,
                agent_specific=explicit_agent_payload
            )
            
            # Format response - handle both dict and Pydantic model metadata
            response_data = agent_response.response if hasattr(agent_response, 'response') else agent_response
            
            # Safely extract metadata values
            metadata_obj = getattr(agent_response, 'metadata', None)
            if metadata_obj is not None:
                if hasattr(metadata_obj, 'executionTime'):
                    execution_time = metadata_obj.executionTime
                elif isinstance(metadata_obj, dict):
                    execution_time = metadata_obj.get('executionTime', 0)
                else:
                    execution_time = 0
                    
                if hasattr(metadata_obj, 'cached'):
                    cached = metadata_obj.cached
                elif isinstance(metadata_obj, dict):
                    cached = metadata_obj.get('cached', False)
                else:
                    cached = False
            else:
                execution_time = 0
                cached = False
            
            return {
                "response": response_data,
                "agentId": "exam_readiness_agent",
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {
                    "executionTime": execution_time,
                    "agentTrace": ["exam_readiness_agent"],
                    "participatingAgents": ["exam_readiness_agent"],
                    "cached": cached
                },
                "intent_info": {
                    "agent_id": "exam_readiness_agent",
                    "confidence": 1.0,
                    "reasoning": "Direct form submission with explicit parameters"
                }
            }
        except Exception as e:
            _logger.error(f"Error forwarding to exam_readiness_agent: {e}", exc_info=True)
            return {"status": "ERROR", "error": str(e)}
    
    # Check if we've been asking for clarification too many times
    recent_clarifications = 0
    for msg in (conversation_history or [])[-MAX_CLARIFICATION_ATTEMPTS:]:
        if not isinstance(msg, dict):
            continue
        intent_info_obj = msg.get("intent_info") or {}
        try:
            if intent_info_obj.get("is_ambiguous", False):
                recent_clarifications += 1
        except Exception:
            # Be defensive in case intent_info_obj is not a dict-like object
            continue
    
    if recent_clarifications >= MAX_CLARIFICATION_ATTEMPTS:
        _logger.warning(f"User {user_id} has received {recent_clarifications} clarification requests. Proceeding with best guess.")
        # Force routing to gemini-wrapper for general handling
        agent_id = "gemini-wrapper"
        routing_result = {
            "agent_ids": [agent_id],
            "intent_info": {
                "agent_id": agent_id,
                "confidence": 0.5,
                "reasoning": "Query remains unclear after multiple clarification attempts. Using general assistant.",
                "is_ambiguous": False
            },
            "needs_clarification": False
        }
    else:
        # Prepare payload for routing. If autoRoute is enabled, ensure there is
        # no explicit agentId in the payload so intent identification runs.
        routing_input = payload.dict()
        if getattr(payload, 'autoRoute', False):
            # Remove any agentId so routing.decide_agent treats this as an auto-route
            routing_input.pop('agentId', None)
            _logger.info(f"Auto-route enabled for user {user_id}; removing explicit agentId for routing")
        else:
            # Normalize empty-string agentId to None so it isn't treated as an explicit override
            if routing_input.get('agentId') == "":
                routing_input['agentId'] = None

        _logger.debug(f"Routing input for user {user_id}: {routing_input}")
        # Get routing decision with intent identification
        routing_result = await routing.decide_agent(
            routing_input,
            registry.list_agents(),
            conversation_history
        )
    
    intent_info = routing_result.get("intent_info", {})
    
    # Check if clarification is needed
    if routing_result.get("needs_clarification", False):
        _logger.info("Query is ambiguous, requesting clarification from user")
        
        clarification_response = {
            "status": "clarification_needed",
            "message": "I need a bit more information to help you better.",
            "response": "I need a bit more information to help you better.",
            "clarifying_questions": routing_result.get("clarifying_questions", []),
            "intent_info": intent_info,
            "suggestions": [
                "Please be more specific about what you need",
                "Try mentioning the subject or topic you're working on",
                "Let me know what type of help you're looking for"
            ],
            "clarification_count": recent_clarifications + 1,
            "max_clarifications": MAX_CLARIFICATION_ATTEMPTS
        }
        
        # Store assistant clarification request
        memory_manager.store_conversation_message(
            user_id=user_id,
            role="assistant",
            content=f"Clarification requested: {clarification_response['message']}",
            intent_info=intent_info
        )
        
        return clarification_response
    
    agent_ids = routing_result.get("agent_ids", [])
    
    if not agent_ids:
        error_message = "I couldn't identify the right specialist for your request. Could you try rephrasing or providing more details?"
        
        memory_manager.store_conversation_message(
            user_id=user_id,
            role="assistant",
            content=error_message,
            intent_info=intent_info
        )
        
        raise HTTPException(status_code=404, detail=error_message)
    
    # Handle multiple potential agents
    if len(agent_ids) > 1:
        _logger.info(f"Multiple agents can handle this request: {agent_ids}")
        
        # Check if all agents are healthy
        healthy_agents = [
            agent_id for agent_id in agent_ids 
            if registry.get_agent(agent_id) and registry.get_agent(agent_id).status == "healthy"
        ]
        
        if not healthy_agents:
            error_message = "All suitable agents are currently offline. Please try again later."
            memory_manager.store_conversation_message(
                user_id=user_id,
                role="assistant",
                content=error_message
            )
            # Return a RequestResponse-shaped dict so the frontend can render
            # the assistant-style message in the chat rather than receiving
            # an HTTP error. Keep metadata consistent with other responses.
            response_dict = {
                "response": error_message,
                "agentId": None,
                "timestamp": datetime.utcnow(),
                "error": {"code": "AGENT_OFFLINE", "message": error_message},
                "metadata": {
                    "identified_agent": None,
                    "agent_name": None,
                    "confidence": intent_info.get("confidence", 0.0),
                    "reasoning": intent_info.get("reasoning", ""),
                    "extracted_params": intent_info.get("extracted_params", {}),
                    "conversation_length": len(conversation_history) if conversation_history else 0
                }
            }
            return response_dict
        
        # Use the first healthy agent (primary choice)
        agent_id = healthy_agents[0]
        _logger.info(f"Selected primary agent: {agent_id} from {len(healthy_agents)} healthy options")
    else:
        agent_id = agent_ids[0]
    
    # Check if agent is healthy
    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found in registry")
    
    if agent.status != "healthy":
        _logger.warning(f"Primary agent {agent_id} is {agent.status}, looking for alternatives")
        
        alternative_agents = intent_info.get("alternative_agents", [])
        healthy_alternative = None
        
        for alt_agent_id in alternative_agents:
            alt_agent = registry.get_agent(alt_agent_id)
            if alt_agent and alt_agent.status == "healthy":
                healthy_alternative = alt_agent_id
                break
        
        if healthy_alternative:
            _logger.info(f"Using alternative healthy agent: {healthy_alternative}")
            agent_id = healthy_alternative
        else:
            error_message = f"Agent {agent_id} is currently {agent.status}. No healthy alternatives available."
            memory_manager.store_conversation_message(
                user_id=user_id,
                role="assistant",
                content=error_message
            )
            # Return a RequestResponse-shaped dict with an explicit error
            # message so the UI shows it inline as an assistant reply.
            response_dict = {
                "response": error_message,
                "agentId": agent_id,
                "timestamp": datetime.utcnow(),
                "error": {"code": "AGENT_OFFLINE", "message": error_message},
                "metadata": {
                    "identified_agent": agent_id,
                    "agent_name": agent.name if agent else agent_id,
                    "confidence": intent_info.get("confidence", 0.0),
                    "reasoning": intent_info.get("reasoning", ""),
                    "extracted_params": intent_info.get("extracted_params", {}),
                    "conversation_length": len(conversation_history) if conversation_history else 0
                }
            }
            return response_dict
    
    # Build agent-specific payload
    agent_payload = routing.build_agent_payload(agent_id, payload.request, intent_info)
    
    # Update the payload with agent-specific format
    payload_dict = payload.dict()
    # Ensure agentId is present for downstream RequestPayload validation
    payload_dict["agentId"] = agent_id
    # Merge agent-specific payload fields into the top-level payload so agents
    # that expect e.g. a 'data' key (research_scout) will find it at task.parameters
    if isinstance(agent_payload, dict):
        # Avoid overwriting explicit top-level keys unintentionally
        for k, v in agent_payload.items():
            if k not in payload_dict or payload_dict.get(k) in (None, ""):
                payload_dict[k] = v
    
    try:
        # Forward to selected agent
        _logger.info(f"Forwarding request to {agent_id} with confidence {intent_info.get('confidence', 0):.2f}")
        
        # Convert back to RequestPayload for forwarding and include agent-specific
        # fields separately so they are not lost by Pydantic model serialization.
        forward_payload = RequestPayload(**{k: v for k, v in payload_dict.items() if k in RequestPayload.__fields__})
        rr = await forward_to_agent(agent_id, forward_payload, agent_specific=agent_payload)
        
        # If the agent indicates it needs clarification, translate that
        # into a supervisor-level clarification request to the user.
        try:
            rr_error = getattr(rr, 'error', None)
            if rr_error and getattr(rr_error, 'code', None) == 'CLARIFICATION_NEEDED':
                # Extract clarifying questions from error.details if present
                clar_qs = []
                example = None
                required_format = None
                try:
                    import json as _json
                    details = getattr(rr_error, 'details', None)
                    if details:
                        parsed = _json.loads(details)
                        clar_qs = parsed.get('clarifying_questions', [])
                        example = parsed.get('example')
                        required_format = parsed.get('required_format')
                except Exception:
                    clar_qs = []

                # Build a specific response that tells the user what to include
                base_msg = getattr(rr_error, 'message', "I need more information to proceed.")
                if example:
                    response_text = f"{base_msg} For example: {example}"
                elif required_format:
                    response_text = f"{base_msg} Please send a request in this format: {required_format}"
                else:
                    response_text = base_msg

                clarification_response = {
                    "status": "clarification_needed",
                    "message": base_msg,
                    "response": response_text,
                    "clarifying_questions": clar_qs,
                    "example_request": example,
                    "required_format": required_format,
                    "intent_info": intent_info,
                    "suggestions": [
                        "Please be more specific about what you need",
                        "Try mentioning the subject or topic you're working on",
                        "Let me know what type of help you're looking for"
                    ],
                    "clarification_count": recent_clarifications + 1,
                    "max_clarifications": MAX_CLARIFICATION_ATTEMPTS
                }

                # Store assistant clarification request
                memory_manager.store_conversation_message(
                    user_id=user_id,
                    role="assistant",
                    content=f"Clarification requested: {clarification_response['message']}",
                    intent_info=intent_info
                )

                return clarification_response
        except Exception:
            # Be defensive: if anything goes wrong while inspecting rr, continue
            pass
        # If agent returned an error, normalize a human-readable response
        # so the frontend does not show empty content.
        response_content = None
        try:
            has_error = bool(getattr(rr, 'error', None))
        except Exception:
            has_error = False

        if has_error:
            err = rr.error
            # Prefer a friendly message, then error.message, then error.code
            friendly = getattr(err, 'message', None) or getattr(err, 'code', None) or "The agent failed to process the request."
            response_content = friendly
        else:
            # Prefer explicit response string, else fallback to str(rr)
            response_content = getattr(rr, 'response', None) or str(rr)

        # Store in memory if successful
        if not has_error:
            memory_manager.store(agent_id, forward_payload, rr)

        # Ensure we never store a None content into conversation history
        memory_manager.store_conversation_message(
            user_id=user_id,
            role="assistant",
            content=response_content or "",
            agent_id=agent_id,
            intent_info=intent_info
        )

        # Add metadata to response and ensure a `response` field exists
        response_dict = rr.dict() if hasattr(rr, 'dict') else {"response": str(rr)}
        if not response_dict.get("response"):
            response_dict["response"] = response_content or ""

        # Merge agent-provided metadata (executionTime, agentTrace, participatingAgents, cached)
        # with supervisor-level metadata (identified_agent, confidence, reasoning, extracted_params).
        incoming_meta = {}
        try:
            incoming_meta = response_dict.get("metadata") or {}
        except Exception:
            incoming_meta = {}

        merged_meta = {
            "executionTime": incoming_meta.get("executionTime") if incoming_meta.get("executionTime") is not None else None,
            "agentTrace": incoming_meta.get("agentTrace") if incoming_meta.get("agentTrace") is not None else [],
            "participatingAgents": incoming_meta.get("participatingAgents") if incoming_meta.get("participatingAgents") is not None else [],
            "cached": incoming_meta.get("cached") if incoming_meta.get("cached") is not None else False,

            # Supervisor-added context
            "identified_agent": agent_id,
            "agent_name": agent.name if agent else agent_id,
            "confidence": intent_info.get("confidence", 0.0),
            "reasoning": intent_info.get("reasoning", ""),
            "extracted_params": intent_info.get("extracted_params", {}),
            "conversation_length": len(conversation_history) if conversation_history else 0
        }

        response_dict["metadata"] = merged_meta

        return response_dict
        
    except Exception as e:
        _logger.error(f"Error forwarding to agent {agent_id}: {e}")
        error_message = f"Failed to process request with {agent_id}: {str(e)}"
        
        memory_manager.store_conversation_message(
            user_id=user_id,
            role="assistant",
            content=error_message
        )
        
        raise HTTPException(status_code=500, detail=error_message)

@app.get('/api/agent/{agent_id}/health')
async def get_agent_health(agent_id: str, user: User = Depends(auth.require_auth)):
    # Perform a live health check instead of returning possibly stale registry status
    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        # Ask registry to perform live check and persist status
        status = await registry.check_agent_live_status(agent_id)
        return {"status": status}
    except Exception as e:
        _logger.error(f"Error checking health for {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/supervisor/debug/last-agent-response')
async def get_last_agent_response(agent_id: Optional[str] = None, user: User = Depends(auth.require_auth)):
    """Return the last raw response captured from agents for debugging.

    If `agent_id` is omitted, returns all stored entries (careful: may be large).
    Protected by auth to prevent accidental exposure.
    """
    try:
        from supervisor import worker_client
        store = getattr(worker_client, 'LAST_RAW_AGENT_RESPONSES', None)
    except Exception as e:
        _logger.error(f"Unable to access worker_client debug store: {e}")
        raise HTTPException(status_code=500, detail="Debug store unavailable")

    if store is None:
        raise HTTPException(status_code=404, detail="No debug data available")

    if agent_id:
        v = store.get(agent_id)
        if not v:
            raise HTTPException(status_code=404, detail="No recorded response for that agent")
        return v

    # Return full store (caller must be careful)
    return {"count": len(store), "entries": store}

@app.post('/api/supervisor/identify-intent')
async def identify_intent_endpoint(
    payload: dict,
    user: User = Depends(auth.require_auth)
):
    """
    Standalone endpoint to identify intent without executing.
    Useful for testing and debugging.
    """
    from supervisor.intent_identifier import get_intent_identifier
    
    user_query = payload.get("query", "")
    conversation_history = payload.get("conversation_history", None)
    
    if not user_query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    try:
        intent_identifier = get_intent_identifier()
        result = await intent_identifier.identify_intent(user_query, conversation_history)
        return result
    except Exception as e:
        _logger.error(f"Error in intent identification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/supervisor/conversation/history')
async def get_conversation_history_endpoint(
    user: User = Depends(auth.require_auth),
    limit: int = 10
):
    """Get conversation history for the current user."""
    history = memory_manager.get_conversation_history(user.id, limit=limit)
    return {
        "user_id": user.id,
        "messages": history,
        "count": len(history)
    }

@app.get('/api/supervisor/conversation/summary')
async def get_conversation_summary_endpoint(user: User = Depends(auth.require_auth)):
    """Get a summary of the user's conversation."""
    summary = memory_manager.get_conversation_summary(user.id)
    return summary

@app.delete('/api/supervisor/conversation/clear')
async def clear_conversation_history_endpoint(user: User = Depends(auth.require_auth)):
    """Clear conversation history for the current user."""
    memory_manager.clear_conversation_history(user.id)
    return {"message": "Conversation history cleared successfully"}

@app.post('/api/supervisor/citation/process')
async def supervisor_citation_process(
    payload: dict,
    user: User = Depends(auth.require_auth)
):
    agent_id = "citation_manager_agent"
    try:
        params = payload or {}
        agent_specific = {"agent_specific_data": {"payload": params}}
        forward_payload = RequestPayload(agentId=agent_id, request=str(params.get("raw_text") or params.get("request") or ""), autoRoute=False)
        rr = await forward_to_agent(agent_id, forward_payload, agent_specific=agent_specific)
        return rr.dict() if hasattr(rr, 'dict') else {"response": str(rr)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/supervisor/citation/bibliography')
async def supervisor_citation_bibliography(
    payload: dict,
    user: User = Depends(auth.require_auth)
):
    agent_id = "citation_manager_agent"
    try:
        params = payload or {}
        forward_payload = RequestPayload(agentId=agent_id, request=str(params.get("request") or ""), autoRoute=False)
        rr = await forward_to_agent(agent_id, forward_payload, agent_specific=params)
        return rr.dict() if hasattr(rr, 'dict') else {"response": str(rr)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/supervisor/citation/upload-pdf')
async def supervisor_citation_upload_pdf(
    file: UploadFile = File(...),
    style: str = "APA",
    includeDOI: bool = True,
    llm_parse: bool = True,
    save: bool = False,
    save_all: bool = False,
    user: User = Depends(auth.require_auth)
):
    agent = registry.get_agent("citation_manager_agent")
    if not agent:
        raise HTTPException(status_code=404, detail="citation_manager_agent not found")
    try:
        data = await file.read()
        form = {
            "style": style,
            "includeDOI": str(bool(includeDOI)).lower(),
            "llm_parse": str(bool(llm_parse)).lower(),
            "save": str(bool(save)).lower(),
            "save_all": str(bool(save_all)).lower(),
            "user_id": user.id,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{agent.url}/upload/pdf",
                data=form,
                files={"file": (file.filename or "upload.pdf", data, "application/pdf")},
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/supervisor/citation/ltm/retrieve')
async def supervisor_citation_ltm_retrieve(
    payload: dict,
    user: User = Depends(auth.require_auth)
):
    agent_id = "citation_manager_agent"
    try:
        params = payload or {}
        if "user_id" not in params:
            params["user_id"] = user.id
        agent_specific = {"agent_specific_data": {"payload": params}}
        forward_payload = RequestPayload(agentId=agent_id, request=str(params.get("query") or ""), autoRoute=False)
        rr = await forward_to_agent(agent_id, forward_payload, agent_specific=agent_specific)
        return rr.dict() if hasattr(rr, 'dict') else {"response": str(rr)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
