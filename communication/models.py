"""
Communication Models
Defines the core message structures for inter-agent communication.
These models represent the protocol contract between supervisor and worker agents.
"""

from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


class Task(BaseModel):
    """Task definition sent from supervisor to worker."""
    name: str
    parameters: dict


class TaskEnvelope(BaseModel):
    """
    Message envelope for task assignment from supervisor to worker.
    This is the standard format for all task assignments.
    """
    message_id: str
    sender: str
    recipient: str
    type: str = "task_assignment"
    task: Task
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CompletionReport(BaseModel):
    """
    Message envelope for task completion report from worker to supervisor.
    This is the standard format for all completion reports.
    """
    message_id: str
    sender: str
    recipient: str
    type: str = "completion_report"
    related_message_id: str
    status: Literal["SUCCESS", "FAILURE"]
    results: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)
