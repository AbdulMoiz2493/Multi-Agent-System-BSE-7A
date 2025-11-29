# supervisor/gemini_chat_orchestrator.py
"""
Unified Gemini-powered chat orchestrator for multi-agent system.
Handles intent identification, parameter extraction, and agent formatting in a single flow.
Eliminates sequential back-and-forth by using one powerful Gemini call per user message.
"""

import logging
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

import google.generativeai as genai
from pydantic import BaseModel

_logger = logging.getLogger(__name__)

# Configure Gemini API - Supervisor uses its own key
GEMINI_API_KEY = os.getenv("SUPERVISOR_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    _logger.error("SUPERVISOR_GEMINI_API_KEY not found in environment variables")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# Configuration thresholds
CONFIDENCE_THRESHOLD = 0.60  # Minimum confidence to proceed without clarification
MIN_ACCEPTABLE_CONFIDENCE = 0.40  # Below this, always ask for clarification
MAX_HISTORY_MESSAGES = 10  # Keep last N messages for context


class GeminiChatOrchestratorResponse(BaseModel):
    """Response model from the unified orchestrator."""
    status: str  # "READY_TO_ROUTE" or "CLARIFICATION_NEEDED"
    agent_id: Optional[str] = None
    confidence: float
    reasoning: str
    extracted_params: Dict[str, Any]
    clarifying_questions: List[str] = []
    agent_payload: Optional[Dict[str, Any]] = None  # Pre-formatted for agent if READY_TO_ROUTE


class GeminiChatOrchestrator:
    """
    Unified Gemini-powered chat handler for multi-agent system.
    
    Handles:
    1. Intent identification from user message
    2. Parameter extraction conversationally
    3. Clarification requests when needed
    4. Agent-specific payload formatting
    5. Conversation state management
    """

    def __init__(self, api_key: Optional[str] = None, agent_definitions: Optional[Dict] = None):
        """
        Initialize the orchestrator.
        
        Args:
            api_key: Gemini API key (uses env var if not provided)
            agent_definitions: Dict of agent configs (auto-loaded from registry if not provided)
        """
        if api_key:
            genai.configure(api_key=api_key)
        
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.agents = agent_definitions or self._load_agent_definitions()
        self.conversation_history = []  # Per-session conversation history
        self.current_agent_id = None  # Currently identified agent (persists across messages)
        self.extracted_params = {}  # Accumulated parameters across messages
        self.confidence_threshold = CONFIDENCE_THRESHOLD
        self.min_acceptable_confidence = MIN_ACCEPTABLE_CONFIDENCE

    def _load_agent_definitions(self) -> Dict[str, Dict]:
        """Load agent definitions from registry.json."""
        try:
            registry_path = Path(__file__).parent.parent / "config" / "registry.json"
            with open(registry_path, 'r') as f:
                agents_list = json.load(f)
            
            agents = {}
            for agent in agents_list:
                agent_id = agent.get('id')
                agents[agent_id] = {
                    "id": agent_id,
                    "name": agent.get('name'),
                    "description": agent.get('description'),
                    "capabilities": agent.get('capabilities', []),
                    "keywords": agent.get('keywords', []),
                    "url": agent.get('url'),
                    "required_params": self._get_required_params_for_agent(agent_id)
                }
            
            _logger.info(f"Loaded {len(agents)} agent definitions from registry")
            return agents
        except Exception as e:
            _logger.error(f"Error loading agent definitions: {e}")
            return {}

    def _get_required_params_for_agent(self, agent_id: str) -> List[str]:
        """Get required parameters for each agent type."""
        required_params = {
            "adaptive_quiz_master_agent": ["topic", "num_questions"],
            "research_scout_agent": ["topic"],
            "assignment_coach_agent": ["task_description"],
            "plagiarism_prevention_agent": ["text_content"],
            "gemini_wrapper_agent": [],  # No required params
        }
        return required_params.get(agent_id, [])

    def _build_system_prompt(self) -> str:
        """
        Build comprehensive system prompt with all agent definitions and instructions.
        This is the core of the unified orchestrator.
        """
        agent_definitions = self._build_agent_definitions_section()
        
        system_prompt = f"""You are an intelligent educational assistant orchestrator powered by Gemini. Your role is to:

1. **Understand** the student's request in natural language
2. **Identify** which specialized agent can best help them
3. **Extract** all required parameters from the request
4. **Ask clarifying questions** if the request is ambiguous or missing required data
5. **Return structured JSON** that helps route to the right agent

## Available Agents

{agent_definitions}

## Your Decision Process

When analyzing a user request, follow these steps:

1. **Match Intent**: Identify which agent's capabilities match the user's intent
   - Look for keyword matches
   - Consider the action the user wants (create, find, analyze, explain, check)
   - Match with agent descriptions

2. **Assess Clarity**: Determine if you have enough information
   - Check if all REQUIRED parameters for the identified agent are present
   - Check if extracted parameters make sense (e.g., valid difficulty levels)
   - Determine confidence level (0.0-1.0)

3. **Extract Parameters**: Pull out specific details
   - Topic/subject/keywords
   - Quantity/number (e.g., number of questions)
   - Difficulty/level
   - Style/format/type
   - Any other agent-specific parameters

4. **Determine Status**:
   - If confidence >= {self.confidence_threshold} AND all required params present → "READY_TO_ROUTE"
   - If confidence < {self.min_acceptable_confidence} OR missing critical params → "CLARIFICATION_NEEDED"
   - If {self.min_acceptable_confidence} <= confidence < {self.confidence_threshold} → Ask clarifying questions

5. **Ask Smart Questions** (if needed):
   - Ask for SPECIFIC missing information, not generic questions
   - Focus on one or two most critical pieces of information
   - Provide examples to guide the user

## Response Format

You MUST respond with ONLY a valid JSON object (no markdown, no extra text):

{{
    "status": "READY_TO_ROUTE" | "CLARIFICATION_NEEDED",
    "agent_id": "agent_id_from_list_above" | null,
    "confidence": 0.95,
    "reasoning": "Explanation of your analysis",
    "extracted_params": {{
        "param_name": "value",
        ...
    }},
    "clarifying_questions": ["question1", "question2"]  // Empty if READY_TO_ROUTE
}}

## Key Rules

1. **ESSENTIAL PARAMETERS MUST BE PROVIDED**: Some agents require specific parameters:
   - **adaptive_quiz_master_agent**: REQUIRES "topic" (what subject to quiz on) - DO NOT route without it
   - **research_scout_agent**: REQUIRES "topic" (what to research) - DO NOT route without it
   - **plagiarism_prevention_agent**: REQUIRES text content to check
   - **gemini_wrapper_agent**: No required params, can handle any general question

2. **ASK FOR REQUIRED PARAMS**: If the user's request matches an agent but is missing REQUIRED params, set status to "CLARIFICATION_NEEDED" and ask specifically for those params.

3. **Be Conversational**: When clarification is needed, ask in a friendly, helpful way
4. **Maintain Context**: Remember previous messages in the conversation
5. **Validate Extractions**: Only extract parameters that make sense for the agent
6. **Confidence Scoring**:
   - 0.90-1.0: Clear intent AND all required params → READY_TO_ROUTE
   - 0.70-0.89: Clear intent but missing optional params → READY_TO_ROUTE
   - 0.50-0.69: Clear intent but missing REQUIRED params → CLARIFICATION_NEEDED
   - <0.50: Unclear intent → CLARIFICATION_NEEDED

7. **SPECIFIC QUESTIONS ONLY**: When asking for clarification, ask about the SPECIFIC missing required parameter:
   - For quiz: "What topic would you like to be quizzed on? (e.g., Python, Math, History)"
   - For research: "What topic would you like me to research?"
   - NEVER ask generic questions like "What do you need help with?"

8. **Parameter Extraction Tips**:
   - Numbers: Extract exact numbers mentioned
   - Difficulty: Recognize "easy", "hard", "beginner", "intermediate", "advanced", "level 1", etc.
   - Topics: Extract subject/topic from context - this is CRITICAL for quiz and research agents
   - Optional params can use defaults (num_questions=5, difficulty=intermediate)

9. **Always Valid JSON**: Your response must be parseable JSON

## Special Handling

- **General Questions** ("What is...?", "Explain...", "Help me"): Route to gemini_wrapper_agent with confidence 0.85
- **Quiz Request WITHOUT Topic**: Ask "What topic would you like to be quizzed on?"
- **Research Request WITHOUT Topic**: Ask "What topic would you like me to research?"
- **User Corrections**: If user says "Actually, change X to Y", update extracted_params
- **Progressive Information**: Track what's been extracted across messages

---

Now analyze the user's message and respond with ONLY the JSON object (no preamble, no markdown).
"""
        return system_prompt

    def _build_agent_definitions_section(self) -> str:
        """Build the agent definitions section for the system prompt."""
        definitions = ""
        
        for agent_id, agent_info in self.agents.items():
            definitions += f"""
### Agent: {agent_info.get('name', agent_id)}
- **ID**: {agent_id}
- **Description**: {agent_info.get('description', 'N/A')}
- **Capabilities**: {', '.join(agent_info.get('capabilities', []))}
- **Keywords**: {', '.join(agent_info.get('keywords', []))}
- **Required Parameters**: {', '.join(agent_info.get('required_params', [])) or 'None'}
- **When to Use**: Use this agent when the user's request matches the description above
"""
        
        definitions += """
## Agent-Specific Parameter Examples

### Adaptive Quiz Master Agent
- Required: topic, num_questions
- Optional: difficulty (beginner/intermediate/advanced), question_type (mcq/true-false/short-answer), style
- Example: "Create a 10-question quiz on Python at intermediate difficulty"
→ Extracted: {topic: "Python", num_questions: 10, difficulty: "intermediate"}

### Research Scout Agent
- Required: topic
- Optional: keywords (list), year_range (from-to), max_results
- Example: "Find papers on neural networks from 2020 to 2023"
→ Extracted: {topic: "neural networks", year_range: {from: "2020", to: "2023"}}

### Assignment Coach Agent
- Required: task_description
- Optional: subject, difficulty_level, deadline
- Example: "Help me with my essay on photosynthesis"
→ Extracted: {task_description: "essay on photosynthesis", subject: "Biology"}

### Plagiarism Prevention Agent
- Required: text_content
- Optional: check_type (check/rephrase), citation_style (APA/MLA/Chicago)
- Example: "Check this paragraph for plagiarism: [text]"
→ Extracted: {text_content: "[text]", check_type: "check"}

### Gemini Wrapper Agent
- Required: None (accepts any query)
- Optional: Any parameters to pass through
- Example: "What is photosynthesis?"
→ Extracted: {} (will just forward the query)

### Concept Reinforcement Agent
- Required: weak_topics (list of topics to reinforce)
- Optional: learning_style (visual/auditory/reading/kinesthetic), max_tasks
- Example: "Help me practice my weak areas in Python loops and functions"
→ Extracted: {weak_topics: ["Python loops", "Python functions"], learning_style: "visual"}
- Keywords: weak topics, practice, reinforce, struggle with, need help with, practice concepts

### Presentation Feedback Agent
- Required: transcript (the presentation text to analyze)
- Optional: title, presenter_name, duration_minutes, target_audience, presentation_type, focus_areas, detail_level
- Example: "Analyze my presentation: Hello everyone, today I will talk about machine learning..."
→ Extracted: {transcript: "Hello everyone, today I will talk about machine learning...", title: "Machine Learning Presentation"}
- Keywords: presentation, speech, feedback, analyze presentation, public speaking, delivery
"""
        return definitions

    async def process_message(self, user_message: str) -> GeminiChatOrchestratorResponse:
        """
        Process a user message and return routing decision or clarification request.
        
        This is the main method. It:
        1. Adds message to conversation history
        2. Builds the system prompt
        3. Calls Gemini
        4. Parses the response
        5. Returns structured decision
        
        Args:
            user_message: The user's current message
            
        Returns:
            GeminiChatOrchestratorResponse with status and routing info
        """
        try:
            # Add to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Trim history to last N messages
            if len(self.conversation_history) > MAX_HISTORY_MESSAGES:
                self.conversation_history = self.conversation_history[-MAX_HISTORY_MESSAGES:]
            
            # Build system prompt
            system_prompt = self._build_system_prompt()
            
            # Call Gemini
            _logger.info(f"Processing message: {user_message[:100]}...")
            gemini_response = await self._call_gemini(system_prompt, user_message)
            
            # Parse response
            parsed_response = self._parse_gemini_response(gemini_response)
            
            # Add to history
            self.conversation_history.append({
                "role": "assistant",
                "content": json.dumps(parsed_response),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Format the response
            if parsed_response.get("status") == "READY_TO_ROUTE":
                return await self._format_routing_response(parsed_response, user_message)
            else:
                return self._format_clarification_response(parsed_response)
                
        except Exception as e:
            _logger.error(f"Error processing message: {e}", exc_info=True)
            # Return clarification asking user to rephrase
            return GeminiChatOrchestratorResponse(
                status="CLARIFICATION_NEEDED",
                agent_id=None,
                confidence=0.0,
                reasoning=f"Error processing request: {str(e)}",
                extracted_params={},
                clarifying_questions=["Could you please rephrase your request? I had trouble understanding it."]
            )

    async def _call_gemini(self, system_prompt: str, user_message: str) -> str:
        """
        Call Gemini API with conversation context.
        
        Args:
            system_prompt: System prompt with agent definitions
            user_message: Current user message
            
        Returns:
            Raw Gemini response text
        """
        try:
            # Build messages for Gemini (include conversation context)
            messages = []
            
            # Add system prompt as first message (Gemini will use it for context)
            messages.append({
                "role": "user",
                "parts": [system_prompt + "\n\nCONVERSATION HISTORY:"]
            })
            
            messages.append({
                "role": "model",
                "parts": ["I understand. I will analyze student requests, identify the appropriate agent, extract parameters, and respond with JSON. Ready to process messages."]
            })
            
            # Add recent conversation history for context
            for msg in self.conversation_history[:-1]:  # Exclude the last message we just added
                role = msg["role"]
                content = msg["content"]
                
                gemini_role = "user" if role == "user" else "model"
                messages.append({
                    "role": gemini_role,
                    "parts": [content]
                })
            
            # Add current user message
            messages.append({
                "role": "user",
                "parts": [f"User message to analyze: {user_message}"]
            })
            
            # Call Gemini
            response = self.model.generate_content(
                messages,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # Lower temperature for more consistent JSON
                    max_output_tokens=1024
                )
            )
            
            response_text = response.text.strip()
            _logger.debug(f"Gemini response: {response_text[:200]}...")
            
            return response_text
            
        except Exception as e:
            _logger.error(f"Error calling Gemini: {e}")
            raise

    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse and validate Gemini JSON response.
        
        Args:
            response_text: Raw response from Gemini
            
        Returns:
            Parsed JSON dict
        """
        try:
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()
            
            # Parse JSON
            parsed = json.loads(response_text)
            
            # Validate required fields
            if "status" not in parsed:
                raise ValueError("Response missing 'status' field")
            
            if parsed["status"] not in ["READY_TO_ROUTE", "CLARIFICATION_NEEDED"]:
                raise ValueError(f"Invalid status: {parsed['status']}")
            
            # Ensure extracted_params exists
            if "extracted_params" not in parsed:
                parsed["extracted_params"] = {}
            
            # Ensure clarifying_questions exists and is a list of strings
            if "clarifying_questions" not in parsed:
                parsed["clarifying_questions"] = []
            else:
                # Normalize clarifying_questions - Gemini might return objects like
                # [{field: "topic", question: "..."}, ...] instead of plain strings
                raw_questions = parsed["clarifying_questions"]
                normalized_questions = []
                for q in raw_questions:
                    if isinstance(q, str):
                        normalized_questions.append(q)
                    elif isinstance(q, dict):
                        # Extract the question text from object format
                        question_text = q.get("question") or q.get("text") or q.get("message") or str(q)
                        normalized_questions.append(question_text)
                    else:
                        normalized_questions.append(str(q))
                parsed["clarifying_questions"] = normalized_questions
            
            # Ensure confidence
            if "confidence" not in parsed:
                parsed["confidence"] = 0.0
            
            return parsed
            
        except json.JSONDecodeError as e:
            _logger.error(f"Failed to parse JSON response: {response_text[:200]}... Error: {e}")
            # Return a default clarification response
            return {
                "status": "CLARIFICATION_NEEDED",
                "agent_id": None,
                "confidence": 0.0,
                "reasoning": "Unable to parse response",
                "extracted_params": {},
                "clarifying_questions": ["Could you please rephrase your request?"]
            }
        except Exception as e:
            _logger.error(f"Error parsing Gemini response: {e}")
            return {
                "status": "CLARIFICATION_NEEDED",
                "agent_id": None,
                "confidence": 0.0,
                "reasoning": "Error processing response",
                "extracted_params": {},
                "clarifying_questions": ["Let me try again. Could you clarify what you need?"]
            }

    def _format_clarification_response(self, parsed: Dict) -> GeminiChatOrchestratorResponse:
        """
        Format response asking for clarification.
        
        Args:
            parsed: Parsed Gemini response
            
        Returns:
            GeminiChatOrchestratorResponse
        """
        clarifying_questions = parsed.get("clarifying_questions", [])
        
        # If no questions provided, generate a friendly one
        if not clarifying_questions:
            clarifying_questions = ["Could you provide more details about what you need?"]
        
        return GeminiChatOrchestratorResponse(
            status="CLARIFICATION_NEEDED",
            agent_id=None,
            confidence=parsed.get("confidence", 0.0),
            reasoning=parsed.get("reasoning", "Need more information to help you"),
            extracted_params=parsed.get("extracted_params", {}),
            clarifying_questions=clarifying_questions
        )

    async def _format_routing_response(
        self, 
        parsed: Dict, 
        user_message: str
    ) -> GeminiChatOrchestratorResponse:
        """
        Format response ready to route to agent.
        Pre-formats the payload for the specific agent.
        
        Args:
            parsed: Parsed Gemini response
            user_message: Original user message
            
        Returns:
            GeminiChatOrchestratorResponse with agent_payload
        """
        agent_id = parsed.get("agent_id")
        extracted_params = parsed.get("extracted_params", {})
        
        # Update accumulated parameters
        self.extracted_params.update(extracted_params)
        
        # Format for the specific agent
        agent_payload = self._format_for_agent(agent_id, extracted_params, user_message)
        
        return GeminiChatOrchestratorResponse(
            status="READY_TO_ROUTE",
            agent_id=agent_id,
            confidence=parsed.get("confidence", 0.0),
            reasoning=parsed.get("reasoning", ""),
            extracted_params=extracted_params,
            clarifying_questions=[],
            agent_payload=agent_payload
        )

    def _format_for_agent(
        self, 
        agent_id: str, 
        extracted_params: Dict, 
        user_request: str
    ) -> Dict[str, Any]:
        """
        Format extracted parameters for the specific agent's expected format.
        
        Each agent has its own payload structure that we need to respect.
        
        Args:
            agent_id: Which agent to format for
            extracted_params: Extracted parameters
            user_request: Original user request
            
        Returns:
            Agent-specific formatted payload
        """
        # Base payload always includes the request
        base_payload = {"request": user_request}
        
        if agent_id == "adaptive_quiz_master_agent":
            return self._format_for_quiz_master(base_payload, extracted_params)
        elif agent_id == "research_scout_agent":
            return self._format_for_research_scout(base_payload, extracted_params)
        elif agent_id == "assignment_coach_agent":
            return self._format_for_assignment_coach(base_payload, extracted_params)
        elif agent_id == "plagiarism_prevention_agent":
            return self._format_for_plagiarism_agent(base_payload, extracted_params)
        elif agent_id == "gemini_wrapper_agent":
            return self._format_for_gemini_wrapper(base_payload, extracted_params)
        elif agent_id == "concept_reinforcement_agent":
            return self._format_for_concept_reinforcement(base_payload, extracted_params)
        elif agent_id == "presentation_feedback_agent":
            return self._format_for_presentation_feedback(base_payload, extracted_params)
        else:
            # Fallback: just include extracted params
            _logger.warning(f"Unknown agent {agent_id}, using generic format")
            base_payload["parameters"] = extracted_params
            return base_payload

    def _format_for_quiz_master(self, payload: Dict, params: Dict) -> Dict:
        """Format for Adaptive Quiz Master Agent with correct nested structure."""
        import uuid as _uuid
        
        # Map difficulty to bloom taxonomy level
        difficulty = (params.get("difficulty") or "intermediate").lower()
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
        topic = params.get("topic") or params.get("subject") or "Python Loops"
        
        return {
            "agent_name": "adaptive_quiz_master_agent",
            "intent": "generate_adaptive_quiz",
            "payload": {
                "user_info": {
                    "user_id": params.get("user_id") or "default_user",
                    "learning_level": difficulty
                },
                "quiz_request": {
                    "topic": topic,
                    "num_questions": int(params.get("num_questions", 5)),
                    "question_types": ["mcq", "true_false"],
                    "bloom_taxonomy_level": bloom_level,
                    "adaptive": True
                },
                "session_info": {
                    "session_id": str(_uuid.uuid4())
                }
            }
        }

    def _format_for_research_scout(self, payload: Dict, params: Dict) -> Dict:
        """Format for Research Scout Agent - expects 'data' object."""
        data = {
            "topic": params.get("topic", ""),
            "keywords": params.get("keywords", []) if isinstance(params.get("keywords"), list) else [params.get("keywords", "")] if params.get("keywords") else [],
            "max_results": int(params.get("max_results", 10))
        }
        
        if params.get("year_range"):
            data["year_range"] = params.get("year_range")
        
        # Keep the request in payload for fallback extraction
        return {
            "request": payload.get("request", ""),
            "data": data
        }

    def _format_for_assignment_coach(self, payload: Dict, params: Dict) -> Dict:
        """Format for Assignment Coach Agent."""
        payload["task_description"] = params.get("task_description", "")
        if params.get("subject"):
            payload["subject"] = params.get("subject")
        if params.get("difficulty_level"):
            payload["difficulty_level"] = params.get("difficulty_level")
        if params.get("deadline"):
            payload["deadline"] = params.get("deadline")
        return payload

    def _format_for_plagiarism_agent(self, payload: Dict, params: Dict) -> Dict:
        """Format for Plagiarism Prevention Agent."""
        payload["text_content"] = params.get("text_content", "")
        payload["check_type"] = params.get("check_type", "check")
        if params.get("citation_style"):
            payload["citation_style"] = params.get("citation_style")
        return payload

    def _format_for_gemini_wrapper(self, payload: Dict, params: Dict) -> Dict:
        """Format for Gemini Wrapper Agent - most flexible."""
        # Just pass through any additional params
        payload.update(params)
        return payload

    def _format_for_concept_reinforcement(self, payload: Dict, params: Dict) -> Dict:
        """Format for Concept Reinforcement Agent - expects agent_name, intent, payload structure."""
        # Extract weak topics - could be a list or a single topic
        weak_topics = params.get("weak_topics") or params.get("topics") or []
        if isinstance(weak_topics, str):
            weak_topics = [weak_topics]
        
        # If topic is provided but not weak_topics, use topic as weak_topics
        if not weak_topics and params.get("topic"):
            weak_topics = [params.get("topic")]
        
        return {
            "agent_name": "concept_reinforcement_agent",
            "intent": "generate_reinforcement_tasks",
            "payload": {
                "student_id": params.get("student_id") or params.get("user_id") or "default_student",
                "weak_topics": weak_topics,
                "preferences": {
                    "learning_style": params.get("learning_style") or "visual",
                    "max_tasks": int(params.get("max_tasks") or 3)
                }
            }
        }

    def _format_for_presentation_feedback(self, payload: Dict, params: Dict) -> Dict:
        """Format for Presentation Feedback Agent - expects presentation data structure."""
        import uuid as _uuid
        
        # Build metadata from extracted params
        metadata = {
            "language": params.get("language") or "en",
            "duration_minutes": params.get("duration_minutes"),
            "target_audience": params.get("target_audience"),
            "presentation_type": params.get("presentation_type"),
        }
        
        # Build analysis parameters
        analysis_parameters = {
            "focus_areas": params.get("focus_areas") or ["clarity", "pacing", "engagement", "material_relevance", "structure"],
            "detail_level": params.get("detail_level") or "high"
        }
        
        return {
            "data": {
                "presentation_id": params.get("presentation_id") or str(_uuid.uuid4()),
                "title": params.get("title") or "Untitled Presentation",
                "presenter_name": params.get("presenter_name") or params.get("user_id") or "Anonymous",
                "transcript": params.get("transcript") or payload.get("request", ""),
                "metadata": metadata,
                "analysis_parameters": analysis_parameters
            }
        }

    def reset_conversation(self):
        """Reset conversation state (for new user or new conversation)."""
        self.conversation_history = []
        self.current_agent_id = None
        self.extracted_params = {}
        _logger.info("Conversation reset")

    def get_conversation_history(self) -> List[Dict]:
        """Get current conversation history."""
        return self.conversation_history.copy()

    def get_state(self) -> Dict:
        """Get current orchestrator state for debugging."""
        return {
            "current_agent_id": self.current_agent_id,
            "extracted_params": self.extracted_params,
            "conversation_length": len(self.conversation_history),
            "available_agents": list(self.agents.keys())
        }


# Singleton instance management
_orchestrator_instance: Optional[GeminiChatOrchestrator] = None


def get_orchestrator(agent_definitions: Optional[Dict] = None) -> GeminiChatOrchestrator:
    """Get or create singleton orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = GeminiChatOrchestrator(agent_definitions=agent_definitions)
    return _orchestrator_instance


def create_orchestrator(agent_definitions: Optional[Dict] = None) -> GeminiChatOrchestrator:
    """Create a new orchestrator instance (not singleton)."""
    return GeminiChatOrchestrator(agent_definitions=agent_definitions)


def reset_orchestrator():
    """Reset singleton instance."""
    global _orchestrator_instance
    _orchestrator_instance = None
