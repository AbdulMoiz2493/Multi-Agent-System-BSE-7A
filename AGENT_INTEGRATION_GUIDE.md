# New Agent Integration Guide

## Overview

This guide provides a comprehensive prompt/checklist for integrating a new agent into the SPM Multi-Agent System. When you add a new agent folder, follow these steps to fully integrate it with the supervisor, frontend, Docker, and Gemini orchestration.

---

## Pre-Integration Checklist

Before starting, ensure your new agent has:
- [ ] A folder under `agents/` (e.g., `agents/my_new_agent/`)
- [ ] An `app.py` with FastAPI endpoints (`/health`, `/process`)
- [ ] A `requirements.txt` for dependencies
- [ ] Clear understanding of what parameters your agent needs

---

## Step-by-Step Integration

### 1. Agent Structure (Your Agent Folder)

Your agent should follow this structure:

```
agents/my_new_agent/
├── app.py              # FastAPI application
├── requirements.txt    # Python dependencies
├── __init__.py         # Package init (can be empty)
└── ... (other files)   # Agent-specific logic
```

#### Required Endpoints in `app.py`:

```python
from fastapi import FastAPI, Request, HTTPException
from datetime import datetime, UTC
import uuid

# Import shared models
import sys
sys.path.insert(0, '/app')
from shared.models import TaskEnvelope, CompletionReport

app = FastAPI()

@app.get('/health')
async def health():
    """Health check endpoint - REQUIRED"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now(UTC).isoformat()
    }

@app.post('/process', response_model=CompletionReport)
async def process_task(req: Request):
    """Main processing endpoint - REQUIRED"""
    try:
        body = await req.json()
        task_envelope = TaskEnvelope(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request body: {e}")
    
    task_params = task_envelope.task.parameters
    
    # Option 1: Structured format (recommended for complex agents)
    # Expects: agent_name, intent, payload
    if "agent_name" in task_params and "intent" in task_params and "payload" in task_params:
        payload = task_params["payload"]
        # Process using structured payload
        result = process_structured_request(payload)
    
    # Option 2: Simple format (for simpler agents)
    # Expects: request (user query), data (optional parameters)
    else:
        request_text = task_params.get("request", "")
        data = task_params.get("data", {})
        result = process_simple_request(request_text, data)
    
    return CompletionReport(
        message_id=str(uuid.uuid4()),
        sender="MyNewAgent",
        recipient=task_envelope.sender,
        related_message_id=task_envelope.message_id,
        status="SUCCESS",
        results={"response": result}
    )
```

---

### 2. Docker Configuration

#### A. Create Dockerfile in agent folder (optional, if agent has special needs)

Or use the existing pattern. Add to `docker-compose.yml`:

```yaml
  my-new-agent:
    build:
      context: ./Multi-Agent-System-BSE-7A-Backend
      dockerfile: agents/my_new_agent/Dockerfile  # Or use shared Dockerfile pattern
    ports:
      - "5025:5025"  # Choose unique port
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    env_file:
      - ./Multi-Agent-System-BSE-7A-Backend/.env
    networks:
      - app_network
```

#### B. If using shared Dockerfile pattern, create `agents/my_new_agent/Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/my_new_agent ./agents/my_new_agent
COPY shared ./shared

# Set Python path to find shared modules
ENV PYTHONPATH=/app

# Expose your chosen port
EXPOSE 5025

CMD ["uvicorn", "agents.my_new_agent.app:app", "--host", "0.0.0.0", "--port", "5025"]
```

---

### 3. Registry Configuration

#### Update `config/registry.json`:

Add your agent to the agents array:

```json
{
  "id": "my_new_agent",
  "name": "My New Agent",
  "url": "http://my-new-agent:5025",
  "description": "Description of what this agent does",
  "capabilities": ["capability1", "capability2", "capability3"],
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "status": "unknown"
}
```

**Important fields:**
- `id`: Unique identifier (snake_case, used in code)
- `url`: Docker internal URL (service-name:port)
- `capabilities`: List of things the agent can do
- `keywords`: Words that help identify when to route to this agent

---

### 4. Intent Identifier Configuration

#### Update `supervisor/intent_identifier.py`:

Find the `AGENT_DESCRIPTIONS` dict and add your agent:

```python
AGENT_DESCRIPTIONS = {
    # ... existing agents ...
    
    "my_new_agent": {
        "name": "My New Agent",
        "description": "Detailed description of what this agent does and when to use it",
        "keywords": ["keyword1", "keyword2", "keyword3", "related_term"],
        "capabilities": [
            "Capability 1 description",
            "Capability 2 description"
        ],
        "required_params": ["param1", "param2"],  # Parameters that MUST be collected
        "optional_params": ["param3", "param4"]   # Nice-to-have parameters
    },
}
```

#### Also update the parameter validation section (around line 240):

```python
# Add validation for your agent's required parameters
if agent_id == "my_new_agent":
    required_params = ["param1", "param2"]
    extracted = intent_result.get("extracted_params", {})
    missing = [p for p in required_params if not extracted.get(p)]
    if missing:
        intent_result["is_ambiguous"] = True
        if not intent_result.get("clarifying_questions"):
            intent_result["clarifying_questions"] = [
                f"What {missing[0]} would you like?",
                "Please provide more details about your request."
            ]
```

---

### 5. Gemini Chat Orchestrator Configuration

#### Update `supervisor/gemini_chat_orchestrator.py`:

##### A. Add to the prompt's agent list (in `_build_prompt` method):

Find the `## Available Agents` section and add:

```python
**my_new_agent**
- Description: What this agent does
- Use when: User wants to [specific use cases]
- Keywords: keyword1, keyword2, keyword3
- REQUIRED parameters: param1, param2
- Optional parameters: param3, param4
```

##### B. Add formatting method:

```python
def _format_for_my_new_agent(self, payload: Dict, params: Dict) -> Dict:
    """Format payload for My New Agent."""
    # Option 1: Structured format (for complex agents)
    return {
        "agent_name": "my_new_agent",
        "intent": "process_request",  # Or specific intent
        "payload": {
            "param1": params.get("param1", ""),
            "param2": params.get("param2", ""),
            "param3": params.get("param3", None),
            # Add all parameters your agent expects
        }
    }
    
    # Option 2: Simple format (for simpler agents)
    # return {
    #     "request": payload.get("request", ""),
    #     "data": {
    #         "param1": params.get("param1", ""),
    #         "param2": params.get("param2", ""),
    #     }
    # }
```

##### C. Add to the `_format_for_agent` routing method:

```python
def _format_for_agent(self, agent_id: str, extracted_params: Dict, user_message: str) -> Dict:
    base_payload = {"request": user_message}
    
    if agent_id == "adaptive_quiz_master_agent":
        return self._format_for_quiz_master(base_payload, extracted_params)
    elif agent_id == "research_scout_agent":
        return self._format_for_research_scout(base_payload, extracted_params)
    # ... existing agents ...
    
    # ADD YOUR AGENT HERE:
    elif agent_id == "my_new_agent":
        return self._format_for_my_new_agent(base_payload, extracted_params)
    
    else:
        return base_payload
```

---

### 6. Routing Configuration (Legacy Path)

#### Update `supervisor/routing.py`:

Find the `build_agent_payload` function and add your agent:

```python
def build_agent_payload(agent_id: str, intent_info: dict, original_request: str) -> dict:
    extracted_params = intent_info.get("extracted_params", {})
    
    # ... existing agent handlers ...
    
    # ADD YOUR AGENT:
    if agent_id == "my_new_agent":
        return {
            "agent_name": "my_new_agent",
            "intent": "process_request",
            "payload": {
                "param1": extracted_params.get("param1", ""),
                "param2": extracted_params.get("param2", ""),
                # Match your agent's expected format
            }
        }
    
    # Default fallback
    return {
        "request": original_request,
        "parameters": extracted_params
    }
```

---

### 7. Frontend Updates (Optional but Recommended)

#### A. Add agent icon/styling in `components/agent-card.tsx` or similar

#### B. Update mock data if needed in `mock-data.json`

#### C. The agent should automatically appear in the UI once registered, but you may want to add:
- Custom icons
- Agent-specific response formatting
- Special UI components for agent responses

---

## Testing Your Integration

### 1. Build and Start

```bash
docker compose down
docker compose build my-new-agent supervisor
docker compose up
```

### 2. Verify Health

```bash
curl http://localhost:5025/health
```

### 3. Test via Frontend

1. Go to http://localhost:3000
2. Type a query that should route to your agent
3. Check the supervisor logs for routing decisions:
   ```bash
   docker compose logs supervisor -f
   ```

### 4. Test Direct API

```bash
curl -X POST http://localhost:8000/api/supervisor/request \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "agentId": "",
    "request": "Your test query that should route to your agent",
    "autoRoute": true
  }'
```

---

## Troubleshooting

### Agent not appearing in registry
- Check `config/registry.json` syntax
- Verify Docker service name matches URL in registry
- Check supervisor logs for registry loading errors

### Agent not being routed to
- Check keywords in `AGENT_DESCRIPTIONS`
- Verify the Gemini prompt includes your agent
- Check intent_identifier logs for routing decisions

### "Missing required fields" error
- Compare your `_format_for_agent` output with what your agent's `/process` endpoint expects
- Check the exact structure in your agent's `app.py`

### Agent unhealthy
- Verify the agent container is running: `docker compose ps`
- Check agent logs: `docker compose logs my-new-agent`
- Test health endpoint directly: `curl http://localhost:5025/health`

---

## Summary Checklist

- [ ] Agent folder created with `app.py`, `requirements.txt`
- [ ] `/health` and `/process` endpoints implemented
- [ ] Dockerfile created or pattern followed
- [ ] Added to `docker-compose.yml`
- [ ] Added to `config/registry.json`
- [ ] Added to `supervisor/intent_identifier.py` AGENT_DESCRIPTIONS
- [ ] Added parameter validation in intent_identifier.py
- [ ] Added to Gemini prompt in `supervisor/gemini_chat_orchestrator.py`
- [ ] Added `_format_for_my_agent` method
- [ ] Added to `_format_for_agent` routing
- [ ] Added to `supervisor/routing.py` build_agent_payload
- [ ] Docker build and test successful
- [ ] Health check passing
- [ ] Routing working correctly
- [ ] Response format displaying properly in frontend

---

## File Reference

| File | Purpose |
|------|---------|
| `agents/my_agent/app.py` | Your agent's FastAPI application |
| `agents/my_agent/Dockerfile` | Docker build instructions |
| `docker-compose.yml` | Service definition |
| `config/registry.json` | Agent registration |
| `supervisor/intent_identifier.py` | Keyword-based routing & descriptions |
| `supervisor/gemini_chat_orchestrator.py` | AI-based routing & payload formatting |
| `supervisor/routing.py` | Legacy routing & payload building |
| `supervisor/worker_client.py` | Agent communication (usually no changes needed) |
| `shared/models.py` | Shared data models (usually no changes needed) |
