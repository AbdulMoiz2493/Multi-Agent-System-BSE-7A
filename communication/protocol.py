"""
Communication Protocol Constants
Defines enums and constants for the inter-agent communication protocol.
"""

from enum import Enum


class MessageType(str, Enum):
    """Types of messages exchanged between agents."""
    TASK_ASSIGNMENT = "task_assignment"
    COMPLETION_REPORT = "completion_report"
    HEALTH_CHECK = "health_check"
    STATUS_UPDATE = "status_update"


class TaskStatus(str, Enum):
    """Status values for task execution."""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING = "PENDING"


class AgentStatus(str, Enum):
    """Status values for agent health."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


# Protocol Version
PROTOCOL_VERSION = "1.0"

# Default timeouts (seconds)
DEFAULT_TASK_TIMEOUT = 30
DEFAULT_HEALTH_CHECK_INTERVAL = 15
