#!/usr/bin/env python

"""
Implementation of the ConceptReinforcementAgent using LangChain.

This version is UPDATED to parse the new custom JSON format from the Supervisor.
It overrides the base 'handle_incoming_message' method.
"""

# --- Core Python & Abstract Class ---
from abc import ABC, abstractmethod
import json
import uuid
import os
import hashlib
import time
from typing import Any, Optional, List, Dict, Literal
from dotenv import load_dotenv

load_dotenv()

# --- Pydantic & LangChain Imports ---
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

# --- 1. ABSTRACT BASE CLASS ---
# (This is unchanged from your project spec)

class AbstractWorkerAgent(ABC):
    """
    Abstract Base Class for all worker agents, including LTM functionality.
    """
    def __init__(self, agent_id: str, supervisor_id: str):
        self._id = agent_id
        self._supervisor_id = supervisor_id
        self._current_task_id = None 
        print(f"[{self._id}] Agent initialized. Supervisor: [{self._supervisor_id}]")

    @abstractmethod
    def process_task(self, task_data: dict) -> dict:
        """The worker's unique business logic. Must return a dictionary of results."""
        pass

    @abstractmethod
    def send_message(self, recipient: str, message_obj: dict):
        """Sends the final JSON message object through the communication layer."""
        pass
    
    @abstractmethod
    def write_to_ltm(self, key: str, value: Any) -> bool:
        """Writes a key-value pair to the agent's Long-Term Memory (LTM)."""
        pass

    @abstractmethod
    def read_from_ltm(self, key: str) -> Optional[Any]:
        """Reads a value from the agent's LTM based on the key."""
        pass

    # --- BASE CLASS PROTOCOL METHODS ---
    # We leave these here, but our new agent will OVERRIDE handle_incoming_message

    def handle_incoming_message(self, json_message: str):
        """Receives and processes an incoming JSON message from the supervisor."""
        try:
            message = json.loads(json_message)
            msg_type = message.get("type")
            
            if msg_type == "task_assignment":
                task_params = message.get("task", {}).get("parameters", {})
                self._current_task_id = message.get("message_id")
                print(f"\n[{self._id}] Received task '{message.get('task', {}).get('name')}' (ID: {self._current_task_id})")
                self._execute_task(task_params, self._current_task_id)
            else:
                print(f"[{self._id}] Received unhandled message type: {msg_type}")
            
        except json.JSONDecodeError as e:
            print(f"[{self._id}] ERROR decoding message: {e}")
            self._report_completion(
                message.get("message_id", "unknown"), 
                "FAILURE", 
                {"error": "JSONDecodeError", "details": str(e)}
            )

    def _execute_task(self, task_data: dict, related_msg_id: str):
        """Executes the concrete process_task logic and handles result reporting."""
        status = "FAILURE"
        results = {}
        
        try:
            results = self.process_task(task_data)
            status = "SUCCESS"
        except Exception as e:
            results = {"error": str(e), "details": "Task processing failed."}
            print(f"[{self._id}] Task FAILED: {e}")
            
        self._report_completion(related_msg_id, status, results)

    def _report_completion(self, related_msg_id: str, status: str, results: dict):
        """Constructs and sends a task completion report."""
        report = {
            "message_id": str(uuid.uuid4()),
            "sender": self._id,
            "recipient": self._supervisor_id,
            "type": "completion_report",
            "related_message_id": related_msg_id,
            "status": status,
            "results": results,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        self.send_message(self._supervisor_id, report)
        self._current_task_id = None

# --- 2. PYDANTIC MODELS FOR LANGCHAIN ---
# (These are unchanged)

class LearningActivity(BaseModel):
    """A single, self-contained micro-learning activity."""
    topic: str = Field(description="The specific topic this activity covers.")
    level: str = Field(description="The difficulty level, e.g., 'beginner'.")
    activity_type: Literal["quiz", "flashcard", "mini_task"] = Field(description="The type of activity.")
    activity_data: dict = Field(description="A dictionary with activity content.")

class LearningActivities(BaseModel):
    """A list of generated learning activities."""
    activities: List[LearningActivity]

# --- 3. LANGCHAIN-POWERED AGENT IMPLEMENTATION ---

class ConceptReinforcementAgent(AbstractWorkerAgent):
    """
    Generates short learning activities using a LangChain LLM chain.
    
    This agent OVERRIDES 'handle_incoming_message' to parse the
    new custom JSON format.
    """

    def __init__(self, agent_id: str, supervisor_id: str, ltm_base_path: str = "./LTM"):
        """
        Initializes the agent, its LTM directory, and the LangChain chain.
        """
        super().__init__(agent_id, supervisor_id)
        
        self.ltm_path = os.path.join(ltm_base_path, self._id)
        os.makedirs(self.ltm_path, exist_ok=True)
        print(f"[{self._id}] LTM initialized at: {self.ltm_path}")

        try:
            self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.7)
        except Exception as e:
            print(f"[{self._id}] ERROR: Could not initialize LLM. Is API key set? {e}")
            raise
            
        # Define the LLM Prompt - UPDATED to use new payload fields
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", 
             "You are a helpful education assistant. Your task is to generate short, "
             "focused learning activities (quizzes, flashcards, or mini-tasks) for a student. "
             "You must return your response in the requested structured format."),
            ("user", 
             "Please generate {max_tasks} micro-learning activities for student '{student_id}' "
             "who needs help with these topics: {topics}. "
             "The student prefers a '{learning_style}' learning style.")
        ])

        self.structured_llm = self.llm.with_structured_output(LearningActivities)
        self.chain = self.prompt_template | self.structured_llm
        
        print(f"[{self._id}] LangChain chain initialized with model {self.llm.model_name}.")

    # --- NEW: OVERRIDE THE MESSAGE HANDLER ---
    
    def handle_incoming_message(self, json_message: str):
        """
        Receives and processes an incoming JSON message from the supervisor.
        This OVERRIDES the base class method to parse the new format.
        """
        try:
            message = json.loads(json_message)
            
            # Check if this message is for this agent
            if message.get("agent_name") != self._id:
                print(f"[{self._id}] Received message for another agent '{message.get('agent_name')}', ignoring.")
                return

            # Get the "message_id" (REQUIRED for reporting)
            message_id = message.get("message_id")
            if not message_id:
                print(f"[{self._id}] ERROR: Message received without a 'message_id'. Cannot process.")
                return 
                
            self._current_task_id = message_id
            intent = message.get("intent")

            # Route based on the new "intent" field
            if intent == "generate_reinforcement_tasks":
                task_params = message.get("payload", {})
                print(f"\n[{self._id}] Received intent '{intent}' (ID: {self._current_task_id})")
                # Call the standard _execute_task method
                self._execute_task(task_params, self._current_task_id)
            else:
                print(f"[{self._id}] Received unhandled intent: {intent}")
                self._report_completion(
                    message_id, 
                    "FAILURE", 
                    {"error": "UnknownIntent", "details": f"Intent '{intent}' not recognized."}
                )
            
        except json.JSONDecodeError as e:
            print(f"[{self._id}] ERROR decoding message: {e}")
        except Exception as e:
            print(f"[{self._id}] ERROR in message handling: {e}")

    # --- LTM Key Generation (Unchanged) ---

    def _get_ltm_key(self, task_data: dict) -> str:
        canonical_key = json.dumps(task_data, sort_keys=True)
        return hashlib.md5(canonical_key.encode('utf-8')).hexdigest() + ".json"

    # --- Abstract Method Implementations (LTM & Comms) ---

    def send_message(self, recipient: str, message_obj: dict):
        """Simulates sending a JSON message to another agent."""
        print(f"[{self._id}] --- SENDING MESSAGE to {recipient} ---")
        print(json.dumps(message_obj, indent=2))
        print(f"[{self._id}] --- END OF MESSAGE ---")

    def write_to_ltm(self, key: str, value: Any) -> bool:
        """Writes a successful response to the agent's LTM (a JSON file)."""
        filepath = os.path.join(self.ltm_path, key)
        try:
            with open(filepath, 'w') as f:
                json.dump(value, f, indent=2)
            print(f"[{self._id}] LTM: Wrote key '{key}'")
            return True
        except Exception as e:
            print(f"[{self._id}] LTM: ERROR writing key '{key}': {e}")
            return False

    def read_from_ltm(self, key: str) -> Optional[Any]:
        """Reads a response from the agent's LTM (a JSON file)."""
        filepath = os.path.join(self.ltm_path, key)
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            print(f"[{self._id}] LTM: Read successful response from key '{key}'")
            return data
        except Exception as e:
            print(f"[{self._id}] LTM: ERROR reading key '{key}': {e}")
            return None

    # --- Abstract Method Implementation (Core Logic) ---

    def process_task(self, task_data: dict) -> dict:
        """
        Core logic, UPDATED to read from the new "payload" structure.
        'task_data' *is* the payload.
        """
        print(f"[{self._id}] Processing task payload: {task_data}")
        
        ltm_key = self._get_ltm_key(task_data)
        
        cached_response = self.read_from_ltm(ltm_key)
        if cached_response:
            cached_response["source"] = "LTM_CACHE"
            return cached_response

        print(f"[{self._id}] No LTM entry found. Invoking LangChain chain...")
        
        # Extract data from the payload structure
        weak_topics = task_data.get("weak_topics", [])
        student_id = task_data.get("student_id")
        preferences = task_data.get("preferences", {})
        learning_style = preferences.get("learning_style", "visual")
        max_tasks = preferences.get("max_tasks", 2)
        
        try:
            # Invoke the chain with the new parameters
            learning_activities_obj = self.chain.invoke({
                "topics": ", ".join(weak_topics),
                "student_id": student_id,
                "learning_style": learning_style,
                "max_tasks": max_tasks
            })
            
            results = {
                "generated_activities": [
                    act.model_dump() for act in learning_activities_obj.activities
                ],
                "target_student": student_id,
                "source": f"LANGCHAIN_GENERATED_BY_{self.llm.model_name}"
            }
        except Exception as e:
            print(f"[{self._id}] LangChain invocation FAILED: {e}")
            raise

        self.write_to_ltm(ltm_key, results)
        
        return results

# --- 4. SIMULATION / MAIN ---
# UPDATED to send the new JSON format

if __name__ == "__main__":
    
    if not os.getenv("GROQ_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        print("="*50)
        print("ERROR: API Key not found.")
        print("Please set GROQ_API_KEY or OPENAI_API_KEY environment variables.")
        print("="*50)
    else:
        print("--- Multi-Agent System Simulation (New JSON Format) ---")
        
        SUPERVISOR_ID = "SupervisorAgent_Main"
        REINFORCER_ID = "concept_reinforcement_agent" # <-- Must match the ID in the JSON
        
        agent = ConceptReinforcementAgent(
            agent_id=REINFORCER_ID,
            supervisor_id=SUPERVISOR_ID
        )

        # 2. Define a sample task using YOUR new format
        # We add "message_id" as it's required for the agent's reply protocol.
        
        task_message_1 = {
          "message_id": "msg-12345-run-1",
          "agent_name": "concept_reinforcement_agent",
          "intent": "generate_reinforcement_tasks",
          "payload": {
            "student_id": "user_987",
            "weak_topics": ["Python 'while' loops"],
            "preferences": {
              "learning_style": "kinesthetic",
              "max_tasks": 2
            }
          }
        }
        
        # 3. --- RUN 1: Generate and Cache ---
        print("\n--- [SIMULATION] RUN 1: Sending new JSON format. (Should be LANGCHAIN_GENERATED) ---")
        message_json_run1 = json.dumps(task_message_1)
        agent.handle_incoming_message(message_json_run1)
        
        print("\n--- [SIMULATION] RUN 1: Completed. ---")

        # 4. --- RUN 2: Test LTM ---
        # Send the *exact same task* again, but with a new message_id
        
        task_message_2 = task_message_1.copy() # Make a copy
        task_message_2["message_id"] = "msg-67890-run-2" # Change the message_id
        
        print("\n--- [SIMULATION] RUN 2: Sending identical task. (Should be LTM_CACHE) ---")
        message_json_run2 = json.dumps(task_message_2)
        agent.handle_incoming_message(message_json_run2)
        
        print("\n--- [SIMULATION] RUN 2: Completed. ---")