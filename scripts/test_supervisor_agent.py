#!/usr/bin/env python3
"""
Simple test script to verify supervisor and agents are reachable and to submit
an example research request. Prints responses and highlights clarification
payloads (including parameters snapshot).

Usage:
  python scripts/test_supervisor_agent.py

Environment variables (optional):
  SUPERVISOR_URL  (default: http://localhost:8000)
  RS_AGENT_URL    (default: http://localhost:5014)
  GW_AGENT_URL    (default: http://localhost:5010)
  EMAIL           (default: test@example.com)
  PASSWORD        (default: password)
"""

import os
import sys
import json
from pprint import pprint

try:
    import requests
except Exception as e:
    print("The `requests` library is required. Install with: pip install requests")
    sys.exit(2)

SUPERVISOR = os.getenv("SUPERVISOR_URL", "http://localhost:8000")
RS_AGENT = os.getenv("RS_AGENT_URL", "http://localhost:5014")
GW_AGENT = os.getenv("GW_AGENT_URL", "http://localhost:5010")
EMAIL = os.getenv("EMAIL", "test@example.com")
PASSWORD = os.getenv("PASSWORD", "password")

TIMEOUT = 5

EXAMPLE_TEXT = "Find research papers with keywords data science, ai from 2010-2020 max results 3"


def check_health(url, name):
    health_url = url.rstrip("/") + "/health"
    print(f"Checking {name} health: {health_url}")
    try:
        r = requests.get(health_url, timeout=TIMEOUT)
        print(f"  status_code: {r.status_code}")
        try:
            pprint(r.json())
        except Exception:
            print("  (non-json body):", r.text[:500])
        return r.status_code == 200
    except Exception as e:
        print(f"  ERROR contacting {name}: {e}")
        return False


def login_supervisor():
    url = SUPERVISOR.rstrip("/") + "/api/auth/login"
    print(f"Logging into supervisor at {url} as {EMAIL}")
    payload = {"email": EMAIL, "password": PASSWORD}
    try:
        r = requests.post(url, json=payload, timeout=TIMEOUT)
    except Exception as e:
        print(f"  ERROR contacting supervisor login: {e}")
        return None
    if r.status_code != 200:
        print(f"  Login failed: status={r.status_code} body={r.text}")
        return None
    try:
        body = r.json()
        token = body.get("token")
        user = body.get("user")
        print("  Login succeeded. User:")
        pprint(user)
        return token
    except Exception as e:
        print(f"  Could not parse login response: {e}")
        return None


def submit_supervisor_request(token, text):
    url = SUPERVISOR.rstrip("/") + "/api/supervisor/request"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "request": text,
        "autoRoute": True,
        "includeHistory": False
    }
    print(f"Submitting request to supervisor: {text}")
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
    except Exception as e:
        print(f"  ERROR sending request to supervisor: {e}")
        return None, None
    print(f"  status={r.status_code}")
    try:
        body = r.json()
        print("Response JSON:")
        pprint(body)
        return r.status_code, body
    except Exception:
        print("Non-JSON response:", r.text[:1000])
        return r.status_code, None


def identify_intent(token, query):
    url = SUPERVISOR.rstrip("/") + "/api/supervisor/identify-intent"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"query": query}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
    except Exception as e:
        print(f"  ERROR contacting identify-intent: {e}")
        return None
    try:
        return r.json()
    except Exception:
        print("  identify-intent returned non-json:", r.text[:1000])
        return None


def run_intent_tests(token):
    print("\n=== Intent Routing Tests ===")
    # Expanded test cases to cover all agents present in registry.json
    test_cases = [
        {"query": "Find research papers about data science with keywords data science, ai from 2010-2020", "expected": "research_scout_agent"},
        {"query": "Create a 10 question multiple choice quiz on basic algebra", "expected": "adaptive_quiz_master_agent"},
        {"query": "Help me break down this assignment about implementing merge sort", "expected": "assignment_coach_agent"},
        {"query": "Check this document for plagiarism and originality", "expected": "plagiarism_prevention_agent"},
        {"query": "Explain quantum entanglement in simple terms", "expected": "gemini_wrapper_agent"},
        {"query": "Generate APA citation for a book", "expected": "citation_manager_agent"},
        {"query": "I need flashcards for memorizing calculus formulas", "expected": "adaptive_flashcard_agent"},
        {"query": "Predict likely exam questions for linear algebra final", "expected": "question_anticipator_agent"},
        {"query": "Create practice exercises to reinforce fractions and decimal skills", "expected": "concept_reinforcement_agent"},
        {"query": "Analyze this team discussion transcript and summarize contributions and blockers", "expected": "peer_collaboration_agent"},
        {"query": "Give feedback on my presentation slides about climate change", "expected": "presentation_feedback_agent"},
        {"query": "Analyze a lecture recording and generate concise notes", "expected": "lecture_insight_agent"},
        {"query": "Set daily revision reminders and track my study streak", "expected": "daily_revision_proctor_agent"},
        {"query": "Create a two-week study timetable leading up to my exams", "expected": "study_scheduler_agent"},
        {"query": "Assess my readiness for the calculus final and suggest improvements", "expected": "exam_readiness_agent"}
    ]

    passed = 0
    for idx, tc in enumerate(test_cases, start=1):
        print(f"\nTest {idx}: {tc['query']}")
        result = identify_intent(token, tc["query"])
        if not result:
            print("  FAIL: no result")
            continue
        got = result.get("agent_id") or result.get("agentId")
        print("  Intent result:")
        pprint(result)
        if got == tc["expected"]:
            print(f"  PASS: routed to {got}")
            passed += 1
        else:
            print(f"  FAIL: expected {tc['expected']}, got {got}")

    total = len(test_cases)
    print(f"\nIntent routing tests passed: {passed}/{total}")
    return passed, total


if __name__ == '__main__':
    print("\n=== Agent health checks ===")
    rs_ok = check_health(RS_AGENT, "research_scout_agent")
    gw_ok = check_health(GW_AGENT, "gemini_wrapper_agent")

    print("\n=== Supervisor login & request ===")
    token = login_supervisor()
    # support a command-line flag to only run intent tests
    intent_only = "--intent-only" in sys.argv

    if intent_only:
        passed, total = run_intent_tests(token)
        print("\nDone.")
        sys.exit(0 if passed == total else 2)

    if not token:
        print("Cannot continue without a valid supervisor token. Exiting.")
        sys.exit(1)

    status, body = submit_supervisor_request(token, EXAMPLE_TEXT)

    if body and isinstance(body, dict):
        if body.get("status") == "clarification_needed" or (body.get("error") and body.get("error").get("code") == "CLARIFICATION_NEEDED"):
            print("\n=== Clarification detected ===")
            # Extract agent-level snapshot if present
            example = body.get("example_request") or body.get("example") or (body.get("error") or {}).get("details")
            required_format = body.get("required_format")
            clar_qs = body.get("clarifying_questions") or []
            print("Clarifying questions:")
            pprint(clar_qs)
            print("Example / request template:")
            pprint(example)
            print("Required format:")
            pprint(required_format)
            # if parameters_snapshot is present at agent result, print it
            params_snap = None
            if body.get("parameters_snapshot"):
                params_snap = body.get("parameters_snapshot")
            elif body.get("error") and body.get("error").get("details"):
                # details may be a json string
                try:
                    parsed = json.loads(body.get("error").get("details"))
                    params_snap = parsed.get("parameters_snapshot")
                except Exception:
                    params_snap = None
            if params_snap:
                print("Parameters snapshot from agent:")
                pprint(params_snap)

    # After the example request, run the intent routing tests for coverage
    passed, total = run_intent_tests(token)
    # Exit with non-zero code if not all tests passed
    print("\nDone.")
    sys.exit(0 if passed == total else 2)
