import uuid
import time
import logging
import httpx
from datetime import datetime

from shared.models import RequestPayload, RequestResponse, RequestResponseMetadata, ErrorInfo, Task, TaskEnvelope, CompletionReport, Agent
from supervisor.registry import get_agent

_logger = logging.getLogger(__name__)

async def _check_agent_health(agent: Agent):
    """Helper to perform a single agent health check."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{agent.url}/health", timeout=2.0)
            if response.status_code == 200 and response.json().get("status") == "healthy":
                agent.status = "healthy"
                return True
    except httpx.RequestError:
        pass
    agent.status = "offline"
    return False

async def forward_to_agent(agent_id: str, payload: RequestPayload) -> RequestResponse:
    agent = get_agent(agent_id)
    if not agent:
        return RequestResponse(
            error=ErrorInfo(code="AGENT_NOT_FOUND", message=f"Agent {agent_id} not found in registry.")
        )

    # If agent is not healthy, perform a quick re-check before failing.
    if agent.status != "healthy":
        _logger.warning(f"Agent {agent_id} is not healthy. Re-checking health before request.")
        if not await _check_agent_health(agent):
            _logger.error(f"Agent {agent_id} is confirmed offline.")
            return RequestResponse(
                error=ErrorInfo(code="AGENT_UNAVAILABLE", message=f"Agent {agent_id} is not available.")
            )
        _logger.info(f"Agent {agent_id} is now healthy. Proceeding with request.")

    task_envelope = TaskEnvelope(
        message_id=str(uuid.uuid4()),
        sender="SupervisorAgent_Main",
        recipient=agent.id,
        task=Task(name="process_request", parameters=payload.dict())
    )

    start_time = time.time()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{agent.url}/process", 
                content=task_envelope.json(), 
                headers={"Content-Type": "application/json"},
                timeout=45.0
            )
            response.raise_for_status()
            
            completion_report_data = response.json()
            completion_report = CompletionReport(**completion_report_data)

            execution_time = (time.time() - start_time) * 1000

            if completion_report.status == "SUCCESS":
                response_dict = {
                    "response": completion_report.results.get("output"),
                    "agentId": agent.id,
                    "timestamp": datetime.utcnow(),
                    "metadata": {
                        "executionTime": execution_time,
                        "agentTrace": [agent.id],
                        "participatingAgents": [agent.id],
                        "cached": completion_report.results.get("cached", False)
                    }
                }
                return RequestResponse.model_validate(response_dict)
            else:
                response_dict = {
                    "agentId": agent.id,
                    "timestamp": datetime.utcnow(),
                    "error": {
                        "code": "AGENT_EXECUTION_ERROR",
                        "message": completion_report.results.get("error", "Agent failed to process the request.")
                    },
                    "metadata": {
                        "executionTime": execution_time
                    }
                }
                return RequestResponse.model_validate(response_dict)

    except httpx.RequestError as e:
        _logger.error(f"Error forwarding request to agent {agent_id}: {e}")
        # Mark agent as offline if we can't reach it
        agent.status = "offline"
        return RequestResponse(
            error=ErrorInfo(code="COMMUNICATION_ERROR", message=f"Failed to communicate with agent {agent_id}.")
        )
    except Exception as e:
        # Added detailed logging for Pydantic errors
        if "ValidationError" in str(type(e)):
             _logger.exception(f"Pydantic ValidationError processing agent response: {e}")
        else:
            _logger.exception(f"An unexpected error occurred while processing agent response: {e}")
        return RequestResponse(
            error=ErrorInfo(code="UNEXPECTED_ERROR", message="An unexpected error occurred.")
        )
