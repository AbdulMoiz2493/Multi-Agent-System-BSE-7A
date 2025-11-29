import pytest
from fastapi.testclient import TestClient
import uuid
import json
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.assignment_coach.app import app
from shared.models import Task, TaskEnvelope

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_process_assignment_request():
    # Sample input matching the required format
    input_payload = {
        "agent_name": "assignment_coach_agent",
        "intent": "generate_assignment_guidance",
        "payload": {
            "student_id": "stu_001",
            "assignment_title": "AI Chatbot Design Report",
            "assignment_description": "Prepare a detailed report explaining the architecture and training process of a conversational AI chatbot.",
            "subject": "Artificial Intelligence",
            "deadline": "2025-10-20",
            "difficulty": "Intermediate",
            "student_profile": {
                "learning_style": "visual",
                "progress": 0.25,
                "skills": ["writing", "communication"],
                "weaknesses": ["time management"]
            }
        }
    }
    
    task = Task(name="process_assignment", parameters={"request": json.dumps(input_payload)})
    envelope = TaskEnvelope(
        message_id=str(uuid.uuid4()),
        sender="test_supervisor",
        recipient="assignment-coach",
        task=task
    )
    
    response = client.post("/process", json=envelope.model_dump(mode='json'))
    
    assert response.status_code == 200
    report = response.json()
    assert report["status"] == "SUCCESS"
    assert "output" in report["results"]
    
    # Parse output
    output_data = json.loads(report["results"]["output"])
    assert output_data["agent_name"] == "assignment_coach_agent"
    assert output_data["status"] == "success"
    assert "assignment_summary" in output_data["response"]
    assert "task_plan" in output_data["response"]
    assert len(output_data["response"]["task_plan"]) > 0
    assert "recommended_resources" in output_data["response"]
    assert "feedback" in output_data["response"]
    assert "motivation" in output_data["response"]
    
    print("\n✅ Test passed! Output:")
    print(json.dumps(output_data, indent=2))
