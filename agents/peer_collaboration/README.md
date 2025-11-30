# Peer Collaboration Agent

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

