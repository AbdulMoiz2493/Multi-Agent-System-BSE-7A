"""Supervisor routing helpers.

Provides functions used by supervisor.main to decide which agent(s)
should handle a user request and to build agent-specific payloads.
"""
import logging
from typing import List, Dict, Any, Optional

from supervisor.intent_identifier import get_intent_identifier
from supervisor import registry

_logger = logging.getLogger(__name__)


async def decide_agent(payload: Any, available_agents: List[Any], conversation_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Decide which agent(s) should handle the given payload.

    Args:
        payload: object or dict containing at least a `.request` string and
                 optionally an `.agentId` override.
        available_agents: list of Agent objects (from registry.list_agents())
        conversation_history: optional recent conversation for context

    Returns a dict with keys:
        - agent_ids: ordered list of candidate agent ids (primary first)
        - intent_info: raw intent identifier result
        - needs_clarification: bool
        - clarifying_questions: list
    """
    # Extract user query and optional explicit agent override
    if hasattr(payload, 'request'):
        user_query = getattr(payload, 'request')
        explicit_agent = getattr(payload, 'agentId', None) if hasattr(payload, 'agentId') else None
    elif isinstance(payload, dict):
        user_query = payload.get('request', '')
        explicit_agent = payload.get('agentId')
    else:
        user_query = str(payload)
        explicit_agent = None

    # If caller supplied an explicit agentId, try to use it (if registered)
    if explicit_agent:
        a = registry.get_agent(explicit_agent)
        if a:
            _logger.info(f"Explicit agentId provided: {explicit_agent}")
            return {
                "agent_ids": [explicit_agent],
                "intent_info": {"agent_id": explicit_agent, "confidence": 1.0, "reasoning": "Explicit agent requested by caller.", "extracted_params": {}},
                "needs_clarification": False,
                "clarifying_questions": []
            }
        else:
            _logger.warning(f"Explicit agentId {explicit_agent} not found in registry; falling back to intent identification")

    # Use the intent identifier (LLM-backed) to pick an agent
    try:
        intent_identifier = get_intent_identifier()
        intent_result = await intent_identifier.identify_intent(user_query, conversation_history)
    except Exception as e:
        _logger.error(f"Error running intent identifier: {e}")
        # Fallback: return no agents so caller can handle
        return {
            "agent_ids": [],
            "intent_info": {},
            "needs_clarification": False,
            "clarifying_questions": []
        }

    # Ensure agent id returned is normalized to registry entries
    primary_agent = intent_result.get('agent_id')
    alternative_agents = intent_result.get('alternative_agents', []) or []

    # Convert known alias 'gemini-wrapper' to registry id if present
    if primary_agent == 'gemini-wrapper':
        # prefer registry naming with _agent suffix if exists
        if registry.get_agent('gemini_wrapper_agent'):
            primary_agent = 'gemini_wrapper_agent'

    normalized_alternatives = []
    for a in alternative_agents:
        if a == 'gemini-wrapper' and registry.get_agent('gemini_wrapper_agent'):
            normalized_alternatives.append('gemini_wrapper_agent')
        else:
            normalized_alternatives.append(a)

    agent_candidates = [primary_agent] + [x for x in normalized_alternatives if x and x != primary_agent]

    needs_clarification = bool(intent_result.get('is_ambiguous', False))
    clarifying_questions = intent_result.get('clarifying_questions', []) or []

    return {
        "agent_ids": agent_candidates,
        "intent_info": intent_result,
        "needs_clarification": needs_clarification,
        "clarifying_questions": clarifying_questions
    }


def build_agent_payload(agent_id: str, user_request: str, intent_info: Dict[str, Any]) -> Dict[str, Any]:
    """Construct an agent-specific payload fragment from the user request and extracted params.

    This returns a dict that will be added as `agent_specific_data` to the
    RequestPayload forwarded to the worker.
    """
    extracted = intent_info.get('extracted_params', {}) if intent_info else {}

    # Standard default payload: put the original request under `request`
    payload = {"request": user_request}

    # Agent-specific shaping
    if agent_id in ("research_scout_agent", "research-scout-agent", "research_scout"):
        # research_scout expects a `data` object with topic/keywords/year_range/max_results
        data = {}
        if extracted.get('topic'):
            data['topic'] = extracted.get('topic')
        if extracted.get('keywords'):
            data['keywords'] = extracted.get('keywords')
        # Support multiple year_range / date formats from the intent extractor
        yr = extracted.get('year_range') or extracted.get('yearRange')
        if not yr:
            # Common alternate extracted keys
            if extracted.get('start_year') and extracted.get('end_year'):
                yr = {'from': extracted.get('start_year'), 'to': extracted.get('end_year')}
            elif extracted.get('from_year') and extracted.get('to_year'):
                yr = {'from': extracted.get('from_year'), 'to': extracted.get('to_year')}
            elif extracted.get('date_range') and isinstance(extracted.get('date_range'), str):
                # e.g. '2019-2023' or '2019 to 2023'
                dr = extracted.get('date_range')
                import re
                parts = re.findall(r"(\d{4})", dr)
                if len(parts) >= 2:
                    yr = {'from': parts[0], 'to': parts[1]}

        if isinstance(yr, dict):
            # Expect keys named 'from'/'to' or 'from_year'/'to_year'
            if 'from' in yr and 'to' in yr:
                data['year_range'] = {'from': yr['from'], 'to': yr['to']}
            elif 'from_year' in yr and 'to_year' in yr:
                data['year_range'] = {'from': yr['from_year'], 'to': yr['to_year']}
        if extracted.get('max_results'):
            data['max_results'] = extracted.get('max_results')
        # Fallbacks
        if 'keywords' not in data:
            data['keywords'] = []
        if 'topic' not in data:
            data['topic'] = user_request
        payload['data'] = data

    elif agent_id in ("gemini_wrapper_agent", "gemini-wrapper", "gemini_wrapper"):
        # General assistant expects `request` and optional model override
        if extracted.get('modelOverride'):
            payload['modelOverride'] = extracted.get('modelOverride')
        # pass-through any other extracted params
        payload.update({k: v for k, v in extracted.items() if k not in ('topic', 'keywords', 'year_range', 'max_results')})

    elif agent_id in ("adaptive_quiz_master_agent", "adaptive-quiz-master", "adaptive_quiz_master"):
        # Quiz master expects agent_name, intent, and nested payload structure
        import uuid as _uuid
        
        # Map difficulty to bloom taxonomy level
        difficulty = (extracted.get("difficulty") or "intermediate").lower()
        bloom_map = {
            "beginner": "remember",
            "easy": "remember",
            "intermediate": "understand",
            "medium": "apply",
            "advanced": "analyze",
            "hard": "evaluate",
            "expert": "create"
        }
        bloom_level = bloom_map.get(difficulty, "understand")
        
        # Use Python Loops as default - a topic that exists in the question bank
        topic = extracted.get("topic") or extracted.get("subject") or "Python Loops"
        
        return {
            "agent_name": "adaptive_quiz_master_agent",
            "intent": "generate_adaptive_quiz",
            "payload": {
                "user_info": {
                    "user_id": extracted.get("user_id") or "default_user",
                    "learning_level": difficulty
                },
                "quiz_request": {
                    "topic": topic,
                    "num_questions": int(extracted.get("num_questions", 5)) if extracted.get("num_questions") else 5,
                    "question_types": ["mcq", "true_false"],
                    "bloom_taxonomy_level": bloom_level,
                    "adaptive": True
                },
                "session_info": {
                    "session_id": str(_uuid.uuid4())
                }
            }
        }

    elif agent_id in ("concept_reinforcement_agent", "concept-reinforcement-agent", "concept_reinforcement"):
        # concept_reinforcement expects a specific payload structure
        payload_data = {
            "student_id": extracted.get('student_id') or extracted.get('user_id') or 'default_student',
            "weak_topics": extracted.get('weak_topics') or extracted.get('topics') or [],
            "preferences": {
                "learning_style": extracted.get('learning_style') or 'visual',
                "max_tasks": extracted.get('max_tasks') or 3
            }
        }
        payload['payload'] = payload_data

    elif agent_id in ("presentation_feedback_agent", "presentation-feedback-agent", "presentation_feedback"):
        # presentation_feedback expects data with presentation details
        import uuid as _uuid
        metadata = {
            "language": extracted.get("language") or "en",
            "duration_minutes": extracted.get("duration_minutes"),
            "target_audience": extracted.get("target_audience"),
            "presentation_type": extracted.get("presentation_type"),
        }
        analysis_parameters = {
            "focus_areas": extracted.get("focus_areas") or ["clarity", "pacing", "engagement", "material_relevance", "structure"],
            "detail_level": extracted.get("detail_level") or "high"
        }
        payload['data'] = {
            "presentation_id": extracted.get("presentation_id") or str(_uuid.uuid4()),
            "title": extracted.get("title") or "Untitled Presentation",
            "presenter_name": extracted.get("presenter_name") or extracted.get("user_id") or "Anonymous",
            "transcript": extracted.get("transcript") or payload.get("request", ""),
            "metadata": metadata,
            "analysis_parameters": analysis_parameters
        }

    elif agent_id in ("daily_revision_proctor_agent", "daily-revision-proctor-agent", "daily_revision_proctor"):
        # daily_revision_proctor expects supervisor analyze format
        from datetime import datetime as _dt
        activity_log = extracted.get("activity_log") or []
        if not activity_log:
            today = _dt.now().strftime("%Y-%m-%d")
            activity_log = [{
                "date": today,
                "subject": extracted.get("subject") or "General Study",
                "hours": extracted.get("hours") or 1.0,
                "status": "completed"
            }]
        
        payload = {
            "student_id": extracted.get("student_id") or extracted.get("user_id") or "1",
            "profile": {
                "name": extracted.get("name") or "Student",
                "grade": extracted.get("grade") or "N/A"
            },
            "study_schedule": {
                "preferred_times": extracted.get("preferred_times") or ["09:00", "14:00", "19:00"],
                "daily_goal_hours": extracted.get("daily_goal_hours") or 3.0
            },
            "activity_log": activity_log,
            "user_feedback": {
                "reminder_effectiveness": extracted.get("reminder_effectiveness") or 4,
                "motivation_level": extracted.get("motivation_level") or "medium"
            },
            "context": {
                "request_type": extracted.get("request_type") or "analysis",
                "supervisor_id": "supervisor_main",
                "priority": "normal"
            }
        }

    elif agent_id in ("peer_collaboration_agent", "peer-collaboration-agent", "peer_collaboration"):
        # peer_collaboration expects team data and discussion logs
        import uuid as _uuid
        import re
        
        team_members = extracted.get("team_members") or []
        if isinstance(team_members, str):
            team_members = [m.strip() for m in team_members.split(",") if m.strip()]
        
        discussion_logs = extracted.get("discussion_logs") or []
        
        # Normalize discussion logs to ensure proper format
        normalized_logs = []
        if discussion_logs:
            for log in discussion_logs:
                if isinstance(log, dict):
                    normalized_logs.append({
                        "user_id": log.get("user_id") or log.get("user") or log.get("name") or "unknown",
                        "message": log.get("message") or log.get("text") or log.get("content") or "",
                        "timestamp": log.get("timestamp") or log.get("time") or ""
                    })
                elif isinstance(log, str):
                    # Parse string format like "Alice (2025-11-29 10:00): message"
                    match = re.match(r'^([^(]+)\s*\(([^)]+)\):\s*(.+)$', log.strip())
                    if match:
                        normalized_logs.append({
                            "user_id": match.group(1).strip(),
                            "timestamp": match.group(2).strip(),
                            "message": match.group(3).strip().strip('"\'')
                        })
                    else:
                        normalized_logs.append({
                            "user_id": "unknown",
                            "message": log,
                            "timestamp": ""
                        })
        
        payload = {
            "agent_name": "peer_collaboration_agent",
            "intent": "analyze_collaboration",
            "payload": {
                "project_id": extracted.get("project_id") or str(_uuid.uuid4()),
                "team_members": team_members,
                "action": extracted.get("action") or "analyze",
                "discussion_logs": normalized_logs
            }
        }

    elif agent_id in ("exam_readiness_agent", "exam-readiness-agent", "exam_readiness"):
        # exam_readiness expects assessment generation parameters
        # Map assessment_type to valid enum values
        assessment_type = (extracted.get("assessment_type") or "quiz").lower()
        valid_types = ["quiz", "exam", "assignment"]
        if assessment_type not in valid_types:
            assessment_type = "quiz"
        
        # Map difficulty to valid enum values
        difficulty = (extracted.get("difficulty") or "medium").lower()
        valid_difficulties = ["easy", "medium", "hard"]
        if difficulty not in valid_difficulties:
            difficulty_map = {
                "beginner": "easy",
                "intermediate": "medium", 
                "advanced": "hard"
            }
            difficulty = difficulty_map.get(difficulty, "medium")
        
        # Get question count
        question_count = extracted.get("question_count") or extracted.get("num_questions") or 5
        if isinstance(question_count, str):
            try:
                question_count = int(question_count)
            except ValueError:
                question_count = 5
        
        # Build type_counts
        type_counts = extracted.get("type_counts")
        if not type_counts:
            type_counts = {"mcq": question_count}
        
        payload = {
            "subject": extracted.get("subject") or extracted.get("topic") or "General",
            "assessment_type": assessment_type,
            "difficulty": difficulty,
            "question_count": question_count,
            "type_counts": type_counts,
            "allow_latex": extracted.get("allow_latex", True),
            "created_by": extracted.get("created_by") or "supervisor",
            "use_rag": extracted.get("use_rag", False),
            "export_pdf": extracted.get("export_pdf", False)
        }

    elif agent_id in ("assignment_coach_agent", "assignment-coach-agent", "assignment_coach"):
        # assignment_coach expects task_description and optional subject
        task_description = extracted.get("task_description") or extracted.get("assignment") or user_request
        subject = extracted.get("subject") or extracted.get("topic") or ""
        
        # Build the request message with subject context if provided
        if subject:
            request_message = f"[Subject: {subject}] {task_description}"
        else:
            request_message = task_description
        
        payload = {
            "request": request_message
        }

    else:
        # Generic fallback: include extracted params under `params`
        if extracted:
            payload['parameters'] = extracted

    return payload
