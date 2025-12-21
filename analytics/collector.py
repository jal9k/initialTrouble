"""Analytics collector for tracking diagnostic sessions."""

import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

from .cost import CostCalculator
from .models import (
    Event,
    EventType,
    Feedback,
    IssueCategory,
    ResolutionPath,
    Session,
    SessionOutcome,
    ToolEvent,
)
from .storage import AnalyticsStorage


class AnalyticsCollector:
    """Collector for tracking analytics during diagnostic sessions."""

    def __init__(
        self,
        storage: AnalyticsStorage | None = None,
        db_path: str | Path = "analytics.db",
    ):
        """Initialize the collector."""
        self.storage = storage or AnalyticsStorage(db_path)
        self.cost_calculator = CostCalculator()
        
        # Current session tracking
        self._current_session: Session | None = None
        self._tool_sequence: list[str] = []
        self._last_tool_name: str | None = None
        self._consecutive_tool_count: int = 0

    # Session management

    def start_session(self, session_id: str | None = None) -> Session:
        """Start a new analytics session."""
        self._current_session = Session(
            session_id=session_id,
        ) if session_id else Session()
        self._tool_sequence = []
        self._last_tool_name = None
        self._consecutive_tool_count = 0
        self.storage.save_session(self._current_session)
        return self._current_session

    def get_session(self, session_id: str | None = None) -> Session | None:
        """Get current or specified session."""
        if session_id:
            return self.storage.get_session(session_id)
        return self._current_session

    def end_session(
        self,
        outcome: SessionOutcome = SessionOutcome.ABANDONED,
        issue_category: IssueCategory | None = None,
        osi_layer: int | None = None,
    ) -> Session | None:
        """End the current session."""
        if self._current_session is None:
            return None

        self._current_session.ended_at = datetime.utcnow()
        self._current_session.outcome = outcome
        
        if issue_category:
            self._current_session.issue_category = issue_category
        if osi_layer:
            self._current_session.osi_layer_resolved = osi_layer

        # Save resolution path
        if self._tool_sequence:
            path = ResolutionPath(
                session_id=self._current_session.session_id,
                tool_sequence=self._tool_sequence.copy(),
                was_successful=outcome == SessionOutcome.RESOLVED,
            )
            self.storage.save_resolution_path(path)

        self.storage.save_session(self._current_session)
        
        session = self._current_session
        self._current_session = None
        return session

    def set_session_backend(
        self,
        backend: str,
        model_name: str,
        had_fallback: bool = False,
    ) -> None:
        """Set the LLM backend info for current session."""
        if self._current_session:
            self._current_session.llm_backend = backend
            self._current_session.model_name = model_name
            self._current_session.had_fallback = had_fallback
            self.storage.save_session(self._current_session)

    # LLM call tracking

    @contextmanager
    def track_llm_call(
        self,
        model_name: str | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Context manager to track an LLM call.
        
        Usage:
            with collector.track_llm_call() as tracker:
                response = await llm.chat(...)
                tracker["response"] = response
        """
        start_time = time.perf_counter()
        tracker: dict[str, Any] = {
            "start_time": start_time,
            "response": None,
        }
        
        try:
            yield tracker
        finally:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            response = tracker.get("response")
            
            prompt_tokens = 0
            completion_tokens = 0
            
            if response and hasattr(response, "usage") and response.usage:
                prompt_tokens = response.usage.get("prompt_tokens", 0)
                completion_tokens = response.usage.get("completion_tokens", 0)
            
            # Record event
            if self._current_session:
                event = Event(
                    session_id=self._current_session.session_id,
                    event_type=EventType.LLM_CALL,
                    duration_ms=duration_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    metadata={"model": model_name or self._current_session.model_name},
                )
                self.storage.save_event(event)
                
                # Update session totals
                self._current_session.total_prompt_tokens += prompt_tokens
                self._current_session.total_completion_tokens += completion_tokens
                self._current_session.total_llm_time_ms += duration_ms
                self._current_session.message_count += 1
                
                # Calculate cost for OpenAI
                if self._current_session.llm_backend == "openai":
                    cost = self.cost_calculator.calculate_cost(
                        model_name or self._current_session.model_name or "gpt-4o-mini",
                        prompt_tokens,
                        completion_tokens,
                    )
                    self._current_session.estimated_cost_usd += cost
                
                self.storage.save_session(self._current_session)

    def record_llm_call(
        self,
        duration_ms: int,
        prompt_tokens: int,
        completion_tokens: int,
        model_name: str | None = None,
    ) -> None:
        """Record an LLM call directly (alternative to context manager)."""
        if self._current_session is None:
            return

        event = Event(
            session_id=self._current_session.session_id,
            event_type=EventType.LLM_CALL,
            duration_ms=duration_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            metadata={"model": model_name or self._current_session.model_name},
        )
        self.storage.save_event(event)

        # Update session totals
        self._current_session.total_prompt_tokens += prompt_tokens
        self._current_session.total_completion_tokens += completion_tokens
        self._current_session.total_llm_time_ms += duration_ms
        self._current_session.message_count += 1

        # Calculate cost for OpenAI
        if self._current_session.llm_backend == "openai":
            cost = self.cost_calculator.calculate_cost(
                model_name or self._current_session.model_name or "gpt-4o-mini",
                prompt_tokens,
                completion_tokens,
            )
            self._current_session.estimated_cost_usd += cost

        self.storage.save_session(self._current_session)

    # Tool call tracking

    @contextmanager
    def track_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Context manager to track a tool call.
        
        Usage:
            with collector.track_tool_call("ping_gateway") as tracker:
                result = await tool.execute()
                tracker["result"] = result
                tracker["success"] = result.success
        """
        start_time = time.perf_counter()
        tracker: dict[str, Any] = {
            "start_time": start_time,
            "result": None,
            "success": True,
            "error_message": None,
        }
        
        try:
            yield tracker
        finally:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            
            # Check for loops
            is_repeated = tool_name == self._last_tool_name
            if is_repeated:
                self._consecutive_tool_count += 1
            else:
                self._consecutive_tool_count = 1
            self._last_tool_name = tool_name
            
            # Add to sequence
            self._tool_sequence.append(tool_name)
            
            if self._current_session:
                # Get result summary
                result = tracker.get("result")
                result_summary = None
                if result and hasattr(result, "content"):
                    content = result.content
                    result_summary = content[:200] if len(content) > 200 else content
                
                tool_event = ToolEvent(
                    session_id=self._current_session.session_id,
                    tool_name=tool_name,
                    execution_time_ms=duration_ms,
                    success=tracker.get("success", True),
                    error_message=tracker.get("error_message"),
                    is_repeated=is_repeated and self._consecutive_tool_count >= 2,
                    consecutive_count=self._consecutive_tool_count,
                    arguments=arguments or {},
                    result_summary=result_summary,
                )
                self.storage.save_tool_event(tool_event)
                
                # Update session
                self._current_session.tool_call_count += 1
                self._current_session.total_tool_time_ms += duration_ms
                self.storage.save_session(self._current_session)

    def record_tool_call(
        self,
        tool_name: str,
        duration_ms: int,
        success: bool = True,
        error_message: str | None = None,
        arguments: dict[str, Any] | None = None,
        result_summary: str | None = None,
    ) -> None:
        """Record a tool call directly (alternative to context manager)."""
        if self._current_session is None:
            return

        # Check for loops
        is_repeated = tool_name == self._last_tool_name
        if is_repeated:
            self._consecutive_tool_count += 1
        else:
            self._consecutive_tool_count = 1
        self._last_tool_name = tool_name

        # Add to sequence
        self._tool_sequence.append(tool_name)

        tool_event = ToolEvent(
            session_id=self._current_session.session_id,
            tool_name=tool_name,
            execution_time_ms=duration_ms,
            success=success,
            error_message=error_message,
            is_repeated=is_repeated and self._consecutive_tool_count >= 2,
            consecutive_count=self._consecutive_tool_count,
            arguments=arguments or {},
            result_summary=result_summary,
        )
        self.storage.save_tool_event(tool_event)

        # Update session
        self._current_session.tool_call_count += 1
        self._current_session.total_tool_time_ms += duration_ms
        self.storage.save_session(self._current_session)

    # User message tracking

    def record_user_message(self, message: str) -> None:
        """Record a user message."""
        if self._current_session is None:
            return

        event = Event(
            session_id=self._current_session.session_id,
            event_type=EventType.USER_MESSAGE,
            metadata={"message_length": len(message)},
        )
        self.storage.save_event(event)

        self._current_session.user_message_count += 1
        self.storage.save_session(self._current_session)

    # Feedback handling

    def record_feedback(
        self,
        score: int,
        comment: str | None = None,
        source: str = "cli",
        session_id: str | None = None,
    ) -> Feedback:
        """Record user feedback for a session."""
        target_session_id = session_id or (
            self._current_session.session_id if self._current_session else None
        )
        
        if not target_session_id:
            raise ValueError("No session ID provided and no current session")

        feedback = Feedback(
            session_id=target_session_id,
            score=score,
            comment=comment,
            source=source,
        )
        self.storage.save_feedback(feedback)

        # Update session if it's the current one
        if self._current_session and self._current_session.session_id == target_session_id:
            self._current_session.feedback_score = score
            self._current_session.feedback_comment = comment
            self.storage.save_session(self._current_session)
        else:
            # Update stored session
            session = self.storage.get_session(target_session_id)
            if session:
                session.feedback_score = score
                session.feedback_comment = comment
                self.storage.save_session(session)

        return feedback

    # Fallback tracking

    def record_fallback(
        self,
        from_backend: str,
        to_backend: str,
        reason: str | None = None,
    ) -> None:
        """Record a fallback event."""
        if self._current_session is None:
            return

        event = Event(
            session_id=self._current_session.session_id,
            event_type=EventType.FALLBACK,
            metadata={
                "from_backend": from_backend,
                "to_backend": to_backend,
                "reason": reason,
            },
        )
        self.storage.save_event(event)

        self._current_session.had_fallback = True
        self.storage.save_session(self._current_session)

    # Utility methods

    def categorize_issue(self, tools_used: list[str]) -> IssueCategory:
        """Auto-categorize issue based on tools used."""
        tool_set = set(tools_used)
        
        if "enable_wifi" in tool_set or any("wifi" in t.lower() for t in tool_set):
            return IssueCategory.WIFI
        if "test_dns_resolution" in tool_set or any("dns" in t.lower() for t in tool_set):
            return IssueCategory.DNS
        if "ping_gateway" in tool_set:
            return IssueCategory.GATEWAY
        if "ping_dns" in tool_set or "check_connectivity" in tool_set:
            return IssueCategory.CONNECTIVITY
        if "get_ip_config" in tool_set:
            return IssueCategory.IP_CONFIG
        if "check_adapter_status" in tool_set:
            return IssueCategory.ADAPTER
        
        return IssueCategory.OTHER

    @property
    def current_session_id(self) -> str | None:
        """Get the current session ID."""
        return self._current_session.session_id if self._current_session else None


# Global collector instance
_collector: AnalyticsCollector | None = None


def get_collector(db_path: str | Path = "analytics.db") -> AnalyticsCollector:
    """Get or create global analytics collector."""
    global _collector
    if _collector is None:
        _collector = AnalyticsCollector(db_path=db_path)
    return _collector


def reset_collector() -> None:
    """Reset the global collector (for testing)."""
    global _collector
    _collector = None

