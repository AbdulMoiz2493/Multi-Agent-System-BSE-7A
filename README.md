# Multi-Agent Backend

This repository contains the backend for a multi-agent system, featuring a Supervisor and pluggable worker agents. This initial version includes a `gemini-wrapper` agent.

## Project Structure

```
/
├── config/
│   ├── registry.json         # Agent registration file
│   └── settings.yaml         # Main configuration for services
├── supervisor/               # Supervisor FastAPI application
│   ├── __init__.py
│   ├── main.py               # Main FastAPI app for supervisor
│   ├── auth.py               # Authentication logic
│   ├── memory_manager.py     # Short-term memory handler
│   ├── registry.py           # Agent registry management
│   ├── routing.py            # Request routing logic
│   ├── worker_client.py      # Client for communicating with workers
│   └── tests/                # Tests for the supervisor
├── agents/
│   ├── gemini_wrapper/       # Gemini-wrapper worker agent
│   │   ├── __init__.py
│   │   ├── app.py            # Main FastAPI app for the worker
│   │   ├── client.py         # Logic for calling Gemini API or mock
│   │   ├── ltm.py            # Long-term memory (SQLite)
│   │   └── tests/            # Tests for the gemini wrapper
│   └── peer_collaboration/   # Peer Collaboration agent
│       ├── __init__.py
│       ├── app.py            # Main FastAPI app for the agent
│       ├── analysis.py       # Discussion analysis logic
│       ├── models.py         # Data models
│       ├── routing.py        # API routing
│       ├── suggestions.py    # Suggestion generation
│       └── tests/            # Tests for peer collaboration
├── shared/
│   └── models.py             # Pydantic models shared across services
├── tests/
│   └── integration_test.py   # Manual integration test script
├── .env.example              # Example environment file for cloud mode
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── run_supervisor.sh         # Script to run the supervisor
└── run_gemini.sh             # Script to run the gemini wrapper
```

## Quickstart

### 1. Installation

Create a virtual environment and install the required packages.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Running the Services

You need to run the Supervisor and all worker agents in separate terminals. Make sure you have installed `textblob`:

```bash
source venv/bin/activate
pip install textblob
```

**Terminal 1: Run the Supervisor**
```bash
source venv/bin/activate
uvicorn supervisor.main:app --host 0.0.0.0 --port 8000 --reload
```
The Supervisor will be available at `http://127.0.0.1:8000`.

**Terminal 2: Run the Gemini Wrapper Agent**
```bash
source venv/bin/activate
uvicorn agents.gemini_wrapper.app:app --host 0.0.0.0 --port 5010 --reload
```
The Gemini Wrapper will be available at `http://127.0.0.1:5010`. By default, it runs in `mock` mode.

**Terminal 3: Run the Peer Collaboration Agent**
```bash
source venv/bin/activate
uvicorn agents.peer_collaboration.app:app --host 0.0.0.0 --port 5020 --reload
```
The Peer Collaboration Agent will be available at `http://127.0.0.1:5020`. This agent analyzes team discussions, sentiment, participation, and provides engagement insights.

## Gemini Wrapper Modes

The `gemini-wrapper` can run in two modes, configured in `config/settings.yaml`.

*   **`mock` mode (default):** No external API calls are made. The agent returns a deterministic mock response. This is useful for local development and testing without needing API keys.
*   **`cloud` mode:** The agent calls a real Gemini-like API. To enable this, you must:
    1.  Set `mode: "cloud"` or `mode: "auto"` in `config/settings.yaml`.
    2.  Create a `.env` file by copying `.env.example`.
    3.  Fill in your `GEMINI_API_URL` and `GEMINI_API_KEY` in the `.env` file.

## Peer Collaboration Agent

The **Peer Collaboration Agent** analyzes team discussions and provides insights on:

*   **Participation Analysis:** Identifies active and inactive team members based on message counts
*   **Sentiment Analysis:** Uses TextBlob to analyze the overall tone of discussions (positive, negative, or neutral)
*   **Topic Extraction:** Identifies dominant topics and keywords from discussion logs
*   **Engagement Scoring:** Computes engagement scores based on participation and sentiment
*   **Suggestions:** Provides recommendations for improving team collaboration

**Features:**
- Analyzes discussion logs from team meetings or chat conversations
- Provides actionable insights for team leads and managers
- Helps identify communication gaps and engagement issues
- Runs on port 5020 by default

## Running Tests

### Unit Tests

To run the unit tests for both services, use `pytest`:

```bash
pytest
```

### Integration Test

A manual integration test script is provided in `tests/integration_test.py`. Make sure both services are running before executing it.

```bash
python tests/integration_test.py
```

## Example API Usage

Here are some `curl` commands to interact with the Supervisor API.

### 1. Login

First, log in to get an authentication token. The default test user is `test@example.com` with password `password`.

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login -H 'Content-Type: application/json' -d '{"email":"test@example.com", "password":"password"}'
```

This will return a JSON object with a `token`. Copy the token for the next step.

### 2. Submit a Request

Replace `<TOKEN>` with the token you received.

```bash
TOKEN="<YOUR_TOKEN_HERE>"

curl -X POST http://127.0.0.1:8000/api/supervisor/request \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"agentId":"gemini-wrapper","request":"Summarize: The impact of AI on modern software development.","priority":1}'
```

You should receive a `RequestResponse` from the `gemini-wrapper` agent. In `mock` mode, the response will be a templated message. In `cloud` mode, it will be the output from the configured LLM.

---

# Peer Collaboration Agent (Detailed)

*A focused micro-service for analyzing team discussions, extracting themes, and offering collaboration insights.*

This agent listens to the rhythm of group conversations — who speaks, who drifts, where the tone leans — and transforms that raw chatter into structured, actionable guidance. It runs independently as part of a multi-agent ecosystem but can also be used as a standalone FastAPI microservice.

---

## 📁 Project Structure (Agent-Only)

```
peer_collaboration/
├── app.py            # FastAPI entrypoint
├── analysis.py       # Discussion + sentiment analysis
├── suggestions.py    # Collaboration improvement suggestions
├── routing.py        # API routing
├── models.py         # Pydantic request/response schemas
└── tests/            # Unit tests
```

---

## 🚀 Quickstart

### 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install textblob
```

### 2. Run the Agent

```bash
uvicorn agents.peer_collaboration.app:app --host 0.0.0.0 --port 5020 --reload
```

Service will be available at:

```
http://127.0.0.1:5020
```

---

## 📡 API Overview

The Peer Collaboration Agent exposes a single unified endpoint that accepts three actions:

* `analyze_discussion`
* `suggest_improvement`
* `summarize_collaboration`

The agent automatically interprets the request and performs the matching analysis.

---

## 📨 Request Format

### **Endpoint**

```
POST /api/peer-collab/analyze
Content-Type: application/json
```

### **Example Request Body**

```json
{
  "project_id": "alpha-42",
  "team_members": ["u01", "u02", "u03"],
  "action": "analyze_discussion",
  "content": {
    "discussion_logs": [
      {
        "user_id": "u01",
        "timestamp": "2025-11-30T12:32:00Z",
        "message": "We should finalize the UI wireframes today."
      },
      {
        "user_id": "u03",
        "timestamp": "2025-11-30T12:33:00Z",
        "message": "Backend APIs will be ready by tomorrow."
      }
    ],
    "meeting_transcript": "",
    "time_range": {
      "start": "2025-11-29T00:00:00Z",
      "end": "2025-11-30T23:59:59Z"
    }
  }
}
```

---

## 📤 Response Format

### **Example Output**

```json
{
  "status": "success",
  "collaboration_summary": {
    "active_participants": ["u01", "u03"],
    "inactive_participants": ["u02"],
    "discussion_sentiment": "positive",
    "dominant_topics": ["UI design", "backend progress"]
  },
  "improvement_suggestions": [
    "Encourage quieter members to share updates.",
    "Clarify task ownership to reduce confusion.",
    "Schedule short weekly syncs to maintain progress."
  ],
  "collaboration_score": "82"
}
```

---

## 🧠 What the Agent Does

### **1. Participation Analysis**

Counts contributions and differentiates between active and silent team members.

### **2. Sentiment Interpretation**

Uses TextBlob to assess emotional tone across the discussion.

### **3. Topic Extraction**

Detects recurring themes and keywords to reveal what the team is centered on.

### **4. Engagement Scoring**

Computes a 0–100 score blending participation, tone, and topical focus.

### **5. Suggestions**

Generates targeted, human-readable recommendations for better collaboration.

---

## 🧪 Running Tests

```bash
pytest agents/peer_collaboration/tests
```

---

## 🌱 Notes

* Works fully offline (no external API calls).
* Designed to be plugged into a Supervisor service but operates independently as a microservice.
* Suitable for team analytics dashboards, meeting-assist tools, and workflow automation systems.

