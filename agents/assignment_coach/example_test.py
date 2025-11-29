"""
Example test script for Assignment Coach Agent
Run this after starting the agent with: python agents/assignment_coach/example_test.py
"""
import requests
import json
from datetime import datetime

# Configuration
SUPERVISOR_URL = "http://localhost:8000"
COACH_URL = "http://localhost:5011"

def test_direct_agent():
    """Test the agent directly (bypassing supervisor)"""
    print("\n" + "="*60)
    print("TEST 1: Direct Agent Call")
    print("="*60)
    
    # Check health
    health_response = requests.get(f"{COACH_URL}/health")
    print(f"\n✓ Health Check: {health_response.json()}")
    
    # Test assignment request
    input_data = {
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
    
    task_envelope = {
        "message_id": "test-123",
        "sender": "TestClient",
        "recipient": "assignment-coach",
        "type": "task_assignment",
        "task": {
            "name": "process_request",
            "parameters": {
                "request": json.dumps(input_data)
            }
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    response = requests.post(f"{COACH_URL}/process", json=task_envelope)
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ Status: {result['status']}")
        
        if result['status'] == 'SUCCESS':
            output = json.loads(result['results']['output'])
            print(f"\n📝 Assignment Summary:")
            print(f"   {output['response']['assignment_summary']}")
            
            print(f"\n📋 Task Plan:")
            for task in output['response']['task_plan']:
                print(f"   Step {task['step']}: {task['task']} ({task['estimated_time']})")
            
            print(f"\n📚 Recommended Resources:")
            for resource in output['response']['recommended_resources']:
                print(f"   - {resource['type'].upper()}: {resource['title']}")
            
            print(f"\n💡 Feedback: {output['response']['feedback']}")
            print(f"🌟 Motivation: {output['response']['motivation']}")
        else:
            print(f"\n✗ Error: {result['results'].get('error')}")
    else:
        print(f"\n✗ Request failed: {response.status_code}")
        print(response.text)

def test_via_supervisor():
    """Test the agent through the supervisor"""
    print("\n" + "="*60)
    print("TEST 2: Via Supervisor")
    print("="*60)
    
    # Login
    login_response = requests.post(
        f"{SUPERVISOR_URL}/api/auth/login",
        json={"email": "test@example.com", "password": "password"}
    )
    
    if login_response.status_code != 200:
        print("✗ Login failed. Make sure supervisor is running!")
        return
    
    token = login_response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"✓ Logged in successfully")
    
    # Check registry
    registry_response = requests.get(f"{SUPERVISOR_URL}/api/supervisor/registry", headers=headers)
    agents = registry_response.json()["agents"]
    
    coach_agent = next((a for a in agents if a["id"] == "assignment-coach"), None)
    if coach_agent:
        print(f"✓ Assignment Coach found in registry: {coach_agent['name']}")
        print(f"  Status: {coach_agent.get('status', 'unknown')}")
    else:
        print("✗ Assignment Coach not found in registry!")
        return
    
    # Submit request through supervisor
    input_data = {
        "agent_name": "assignment_coach_agent",
        "intent": "generate_assignment_guidance",
        "payload": {
            "student_id": "stu_002",
            "assignment_title": "Machine Learning Model Comparison",
            "assignment_description": "Compare different ML algorithms for classification tasks and provide recommendations.",
            "subject": "Machine Learning",
            "deadline": "2025-11-30",
            "difficulty": "Advanced",
            "student_profile": {
                "learning_style": "hands-on",
                "progress": 0.1,
                "skills": ["coding", "mathematics"],
                "weaknesses": ["documentation"]
            }
        }
    }
    
    request_payload = {
        "agentId": "assignment-coach",
        "request": json.dumps(input_data),
        "priority": 1,
        "autoRoute": False
    }
    
    print(f"\n📤 Submitting request to supervisor...")
    response = requests.post(
        f"{SUPERVISOR_URL}/api/supervisor/request",
        headers=headers,
        json=request_payload,
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Response received from {result.get('agentId')}")
        
        if result.get('response'):
            output = json.loads(result['response'])
            print(f"\n📝 Assignment Summary:")
            print(f"   {output['response']['assignment_summary']}")
            
            print(f"\n📋 Task Plan ({len(output['response']['task_plan'])} steps)")
            
            print(f"\n💡 Feedback: {output['response']['feedback']}")
            
            print(f"\n⏱️  Execution Time: {result.get('metadata', {}).get('executionTime', 0):.2f}ms")
            print(f"🔄 Cached: {result.get('metadata', {}).get('cached', False)}")
        else:
            print(f"✗ Error: {result.get('error', {}).get('message')}")
    else:
        print(f"✗ Request failed: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    print("\n🤖 Assignment Coach Agent - Test Suite")
    print("=" * 60)
    
    print("\nMake sure the following services are running:")
    print("  1. Supervisor (port 8000)")
    print("  2. Assignment Coach Agent (port 5011)")
    
    input("\nPress Enter to start tests...")
    
    try:
        # Test direct agent call first
        test_direct_agent()
        
        # Then test via supervisor
        test_via_supervisor()
        
        print("\n" + "="*60)
        print("✅ All tests completed!")
        print("="*60)
        
    except requests.exceptions.ConnectionError as e:
        print(f"\n✗ Connection Error: Make sure all services are running!")
        print(f"   Details: {e}")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
