"""Pydantic models for analytics data."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SessionOutcome(str, Enum):
    """Possible outcomes for a diagnostic session."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    ABANDONED = "abandoned"
    IN_PROGRESS = "in_progress"


class IssueCategory(str, Enum):
    """Categories of network issues."""

    WIFI = "wifi"
    DNS = "dns"
    GATEWAY = "gateway"
    CONNECTIVITY = "connectivity"
    IP_CONFIG = "ip_config"
    ADAPTER = "adapter"
    OTHER = "other"
    UNKNOWN = "unknown"


class EventType(str, Enum):
    """Types of trackable events."""

    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"
    FALLBACK = "fallback"
    ERROR = "error"


class Session(BaseModel):
    """Tracks a complete diagnostic conversation."""

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
    
    # Token tracking
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    
    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self.total_prompt_tokens + self.total_completion_tokens
    
    # Outcome tracking
    outcome: SessionOutcome = SessionOutcome.IN_PROGRESS
    feedback_score: int | None = None  # 1-5 or None
    feedback_comment: str | None = None
    
    # Diagnostic categorization
    issue_category: IssueCategory = IssueCategory.UNKNOWN
    osi_layer_resolved: int | None = None  # 1-7 or None
    
    # Conversation metrics
    message_count: int = 0
    user_message_count: int = 0
    tool_call_count: int = 0
    
    # Model tracking
    llm_backend: str | None = None  # "ollama" or "openai"
    model_name: str | None = None
    had_fallback: bool = False
    
    # Cost tracking (for OpenAI)
    estimated_cost_usd: float = 0.0
    
    # Timing
    total_llm_time_ms: int = 0
    total_tool_time_ms: int = 0
    
    @property
    def time_to_resolution_seconds(self) -> float | None:
        """Calculate time from start to resolution."""
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at).total_seconds()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "outcome": self.outcome.value,
            "feedback_score": self.feedback_score,
            "feedback_comment": self.feedback_comment,
            "issue_category": self.issue_category.value,
            "osi_layer_resolved": self.osi_layer_resolved,
            "message_count": self.message_count,
            "user_message_count": self.user_message_count,
            "tool_call_count": self.tool_call_count,
            "llm_backend": self.llm_backend,
            "model_name": self.model_name,
            "had_fallback": self.had_fallback,
            "estimated_cost_usd": self.estimated_cost_usd,
            "total_llm_time_ms": self.total_llm_time_ms,
            "total_tool_time_ms": self.total_tool_time_ms,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            started_at=datetime.fromisoformat(data["started_at"]),
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            total_prompt_tokens=data.get("total_prompt_tokens", 0),
            total_completion_tokens=data.get("total_completion_tokens", 0),
            outcome=SessionOutcome(data.get("outcome", "in_progress")),
            feedback_score=data.get("feedback_score"),
            feedback_comment=data.get("feedback_comment"),
            issue_category=IssueCategory(data.get("issue_category", "unknown")),
            osi_layer_resolved=data.get("osi_layer_resolved"),
            message_count=data.get("message_count", 0),
            user_message_count=data.get("user_message_count", 0),
            tool_call_count=data.get("tool_call_count", 0),
            llm_backend=data.get("llm_backend"),
            model_name=data.get("model_name"),
            had_fallback=data.get("had_fallback", False),
            estimated_cost_usd=data.get("estimated_cost_usd", 0.0),
            total_llm_time_ms=data.get("total_llm_time_ms", 0),
            total_tool_time_ms=data.get("total_tool_time_ms", 0),
        )


class Event(BaseModel):
    """Individual trackable moment in a session."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: int | None = None
    
    # Token tracking (for LLM calls)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    
    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        """Create from dictionary."""
        return cls(
            event_id=data["event_id"],
            session_id=data["session_id"],
            event_type=EventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            duration_ms=data.get("duration_ms"),
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            metadata=data.get("metadata", {}),
        )


class ToolEvent(BaseModel):
    """Tool-specific tracking extending Event."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Tool-specific fields
    tool_name: str
    execution_time_ms: int = 0
    success: bool = True
    error_message: str | None = None
    
    # Loop detection
    is_repeated: bool = False  # Same tool called consecutively
    consecutive_count: int = 1  # How many times in a row
    
    # Tool arguments and result summary
    arguments: dict[str, Any] = Field(default_factory=dict)
    result_summary: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "tool_name": self.tool_name,
            "execution_time_ms": self.execution_time_ms,
            "success": self.success,
            "error_message": self.error_message,
            "is_repeated": self.is_repeated,
            "consecutive_count": self.consecutive_count,
            "arguments": self.arguments,
            "result_summary": self.result_summary,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolEvent":
        """Create from dictionary."""
        return cls(
            event_id=data["event_id"],
            session_id=data["session_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tool_name=data["tool_name"],
            execution_time_ms=data.get("execution_time_ms", 0),
            success=data.get("success", True),
            error_message=data.get("error_message"),
            is_repeated=data.get("is_repeated", False),
            consecutive_count=data.get("consecutive_count", 1),
            arguments=data.get("arguments", {}),
            result_summary=data.get("result_summary"),
        )


class Feedback(BaseModel):
    """Explicit user feedback for a session."""

    feedback_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    score: int = Field(ge=1, le=5)  # 1-5 scale
    comment: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Source of feedback
    source: str = "cli"  # "cli", "api", "gui"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "feedback_id": self.feedback_id,
            "session_id": self.session_id,
            "score": self.score,
            "comment": self.comment,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Feedback":
        """Create from dictionary."""
        return cls(
            feedback_id=data["feedback_id"],
            session_id=data["session_id"],
            score=data["score"],
            comment=data.get("comment"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data.get("source", "cli"),
        )


class ResolutionPath(BaseModel):
    """Sequence of tools leading to resolution."""

    path_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    tool_sequence: list[str] = Field(default_factory=list)
    was_successful: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "path_id": self.path_id,
            "session_id": self.session_id,
            "tool_sequence": self.tool_sequence,
            "was_successful": self.was_successful,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResolutionPath":
        """Create from dictionary."""
        return cls(
            path_id=data["path_id"],
            session_id=data["session_id"],
            tool_sequence=data.get("tool_sequence", []),
            was_successful=data.get("was_successful", False),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


# Summary models for API responses

class ToolStats(BaseModel):
    """Aggregated statistics for a tool."""

    tool_name: str
    total_calls: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_execution_time_ms: float = 0.0
    total_execution_time_ms: int = 0
    loop_occurrences: int = 0  # Times it was part of a loop
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.success_count / self.total_calls) * 100


class SessionSummary(BaseModel):
    """Summary statistics across sessions."""

    total_sessions: int = 0
    resolved_count: int = 0
    unresolved_count: int = 0
    abandoned_count: int = 0
    in_progress_count: int = 0
    
    avg_tokens_per_session: float = 0.0
    avg_time_to_resolution_seconds: float = 0.0
    avg_messages_per_session: float = 0.0
    
    total_cost_usd: float = 0.0
    
    # Backend breakdown
    ollama_sessions: int = 0
    openai_sessions: int = 0
    fallback_count: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate resolution success rate."""
        completed = self.resolved_count + self.unresolved_count
        if completed == 0:
            return 0.0
        return (self.resolved_count / completed) * 100


class QualityMetrics(BaseModel):
    """Conversation quality metrics."""

    avg_messages_to_resolution: float = 0.0
    sessions_with_loops: int = 0
    total_loop_occurrences: int = 0
    abandoned_sessions: int = 0
    drop_off_rate: float = 0.0  # Percentage of sessions abandoned

