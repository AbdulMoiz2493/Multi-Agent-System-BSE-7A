"""
Example script to test Assignment Coach Agent integration
Run this after starting both Supervisor and Assignment Coach services
"""

import requests
import json
import time

SUPERVISOR_URL = "http://localhost:8000"
ASSIGNMENT_COACH_URL = "http://localhost:5011"

def test_assignment_coach_integration():
    print("=" * 60)
    print("Assignment Coach Agent Integration Test")
    print("=" * 60)
    
    # Step 1: Check if Assignment Coach is healthy
    print("\n[1/5] Checking Assignment Coach health...")
    try:
        response = requests.get(f"{ASSIGNMENT_COACH_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Assignment Coach is healthy!")
            print(f"   Response: {response.json()}")
        else:
            print("❌ Assignment Coach health check failed")
            return
    except requests.RequestException as e:
        print(f"❌ Cannot connect to Assignment Coach: {e}")
        print("   Make sure to run: uvicorn agents.assignment_coach.app:app --host 0.0.0.0 --port 5011 --reload")
        return
    
    # Step 2: Check Supervisor health
    print("\n[2/5] Checking Supervisor health...")
    try:
        response = requests.get(f"{SUPERVISOR_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Supervisor is healthy!")
    except requests.RequestException as e:
        print(f"❌ Cannot connect to Supervisor: {e}")
        return
    
    # Step 3: Login to Supervisor
    print("\n[3/5] Logging in to Supervisor...")
    login_payload = {"email": "test@example.com", "password": "password"}
    response = requests.post(f"{SUPERVISOR_URL}/api/auth/login", json=login_payload)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        return
    
    token = response.json()["token"]
    print("✅ Login successful!")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Step 4: Check registry
    print("\n[4/5] Checking if Assignment Coach is registered...")
    response = requests.get(f"{SUPERVISOR_URL}/api/supervisor/registry", headers=headers)
    agents = response.json().get("agents", [])
    
    coach_agent = next((a for a in agents if a["id"] == "assignment-coach"), None)
    if coach_agent:
        print("✅ Assignment Coach found in registry!")
        print(f"   Name: {coach_agent['name']}")
        print(f"   Status: {coach_agent.get('status', 'unknown')}")
        print(f"   Capabilities: {', '.join(coach_agent['capabilities'])}")
    else:
        print("❌ Assignment Coach not found in registry")
        return
    
    # Step 5: Submit assignment coaching request
    print("\n[5/5] Submitting assignment coaching request...")
    
    assignment_input = {
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
    
    request_payload = {
        "agentId": "assignment-coach",
        "request": json.dumps(assignment_input),
        "priority": 1,
        "autoRoute": False
    }
    
    print("   Sending request...")
    response = requests.post(
        f"{SUPERVISOR_URL}/api/supervisor/request",
        headers=headers,
        json=request_payload,
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"❌ Request failed: {response.text}")
        return
    
    result = response.json()
    print("✅ Request successful!")
    print(f"\n{'='*60}")
    print("RESPONSE FROM ASSIGNMENT COACH:")
    print(f"{'='*60}")
    
    if result.get("response"):
        output = json.loads(result["response"])
        print(f"\nAgent: {output['agent_name']}")
        print(f"Status: {output['status']}")
        print(f"\n📝 Assignment Summary:")
        print(f"   {output['response']['assignment_summary']}")
        
        print(f"\n📋 Task Plan:")
        for task in output['response']['task_plan']:
            print(f"   {task['step']}. {task['task']} ({task['estimated_time']})")
        
        print(f"\n📚 Recommended Resources:")
        for resource in output['response']['recommended_resources']:
            print(f"   [{resource['type']}] {resource['title']}")
            print(f"   URL: {resource['url']}")
        
        print(f"\n💬 Feedback:")
        print(f"   {output['response']['feedback']}")
        
        print(f"\n✨ Motivation:")
        print(f"   {output['response']['motivation']}")
        
        print(f"\n⏰ Timestamp: {output['response']['timestamp']}")
        
        if result.get("metadata"):
            print(f"\n📊 Metadata:")
            print(f"   Execution Time: {result['metadata'].get('executionTime', 0):.2f} ms")
            print(f"   Cached: {result['metadata'].get('cached', False)}")
    else:
        print(json.dumps(result, indent=2))
    
    print(f"\n{'='*60}")
    print("✅ Integration test completed successfully!")
    print(f"{'='*60}")
    
    # Test caching on second request
    print("\n[BONUS] Testing LTM caching with identical request...")
    time.sleep(1)
    response = requests.post(
        f"{SUPERVISOR_URL}/api/supervisor/request",
        headers=headers,
        json=request_payload,
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get("metadata", {}).get("cached"):
            print("✅ Response was retrieved from cache (LTM)!")
        else:
            print("ℹ️  Response was generated fresh (not cached yet)")

if __name__ == "__main__":
    test_assignment_coach_integration()
