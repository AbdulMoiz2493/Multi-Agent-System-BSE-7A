"""Quick health check for Assignment Coach Agent"""
import requests
import sys

try:
    response = requests.get("http://localhost:5011/health", timeout=5)
    if response.status_code == 200:
        print("✅ Assignment Coach Agent is HEALTHY!")
        print(f"   Response: {response.json()}")
        sys.exit(0)
    else:
        print(f"⚠️  Agent responded with status {response.status_code}")
        sys.exit(1)
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to Assignment Coach Agent on port 5011")
    print("   Make sure it's running with: uvicorn agents.assignment_coach.app:app --port 5011")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
