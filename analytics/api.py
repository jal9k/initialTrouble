"""FastAPI router for analytics endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .models import (
    Feedback,
    IssueCategory,
    QualityMetrics,
    Session,
    SessionOutcome,
    SessionSummary,
    ToolStats,
)
from .patterns import PatternAnalyzer
from .storage import AnalyticsStorage


# Request/Response Models

class FeedbackRequest(BaseModel):
    """Request body for submitting feedback."""
    
    session_id: str = Field(description="Session ID to provide feedback for")
    score: int = Field(ge=1, le=5, description="Feedback score (1-5)")
    comment: str | None = Field(default=None, description="Optional comment")
    source: str = Field(default="api", description="Source of feedback")


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""
    
    feedback_id: str
    session_id: str
    score: int
    message: str = "Feedback recorded successfully"


class SessionResponse(BaseModel):
    """Response for a single session."""
    
    session_id: str
    started_at: datetime
    ended_at: datetime | None
    total_tokens: int
    outcome: str
    feedback_score: int | None
    issue_category: str
    osi_layer_resolved: int | None
    message_count: int
    user_message_count: int
    tool_call_count: int
    llm_backend: str | None
    model_name: str | None
    had_fallback: bool
    estimated_cost_usd: float
    time_to_resolution_seconds: float | None


class SessionListResponse(BaseModel):
    """Response for session list."""
    
    sessions: list[SessionResponse]
    total: int
    limit: int
    offset: int


class SessionDetailResponse(SessionResponse):
    """Detailed session response with events."""
    
    events: list[dict[str, Any]]
    tool_events: list[dict[str, Any]]
    feedback: dict[str, Any] | None


class SummaryResponse(BaseModel):
    """Response for analytics summary."""
    
    total_sessions: int
    resolved_count: int
    unresolved_count: int
    abandoned_count: int
    in_progress_count: int
    success_rate: float
    avg_tokens_per_session: float
    avg_time_to_resolution_seconds: float
    avg_messages_per_session: float
    total_cost_usd: float
    ollama_sessions: int
    openai_sessions: int
    fallback_count: int


class ToolStatsResponse(BaseModel):
    """Response for tool statistics."""
    
    tools: list[dict[str, Any]]


class PatternsResponse(BaseModel):
    """Response for pattern analysis."""
    
    common_paths: list[dict[str, Any]]
    category_stats: dict[str, Any]
    osi_layer_stats: dict[str, Any]
    problematic_tools: list[dict[str, Any]]
    optimization_suggestions: list[str]


class CostResponse(BaseModel):
    """Response for cost breakdown."""
    
    periods: list[dict[str, Any]]
    total_cost: float
    total_tokens: int
    total_sessions: int


class QualityResponse(BaseModel):
    """Response for quality metrics."""
    
    avg_messages_to_resolution: float
    sessions_with_loops: int
    total_loop_occurrences: int
    abandoned_sessions: int
    drop_off_rate: float


def create_analytics_router(storage: AnalyticsStorage) -> APIRouter:
    """Create the analytics API router.
    
    Args:
        storage: The analytics storage instance to use
        
    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/analytics", tags=["analytics"])
    pattern_analyzer = PatternAnalyzer(storage)

    def session_to_response(session: Session) -> SessionResponse:
        """Convert Session to SessionResponse."""
        return SessionResponse(
            session_id=session.session_id,
            started_at=session.started_at,
            ended_at=session.ended_at,
            total_tokens=session.total_tokens,
            outcome=session.outcome.value,
            feedback_score=session.feedback_score,
            issue_category=session.issue_category.value,
            osi_layer_resolved=session.osi_layer_resolved,
            message_count=session.message_count,
            user_message_count=session.user_message_count,
            tool_call_count=session.tool_call_count,
            llm_backend=session.llm_backend,
            model_name=session.model_name,
            had_fallback=session.had_fallback,
            estimated_cost_usd=session.estimated_cost_usd,
            time_to_resolution_seconds=session.time_to_resolution_seconds,
        )

    @router.get("/sessions", response_model=SessionListResponse)
    async def list_sessions(
        start_date: datetime | None = Query(default=None, description="Filter by start date"),
        end_date: datetime | None = Query(default=None, description="Filter by end date"),
        outcome: str | None = Query(default=None, description="Filter by outcome"),
        category: str | None = Query(default=None, description="Filter by issue category"),
        limit: int = Query(default=100, ge=1, le=1000, description="Max results"),
        offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    ) -> SessionListResponse:
        """List sessions with optional filters."""
        outcome_enum = SessionOutcome(outcome) if outcome else None
        category_enum = IssueCategory(category) if category else None
        
        sessions = storage.get_sessions(
            start_date=start_date,
            end_date=end_date,
            outcome=outcome_enum,
            category=category_enum,
            limit=limit,
            offset=offset,
        )
        
        return SessionListResponse(
            sessions=[session_to_response(s) for s in sessions],
            total=len(sessions),
            limit=limit,
            offset=offset,
        )

    @router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
    async def get_session(session_id: str) -> SessionDetailResponse:
        """Get detailed session information."""
        session = storage.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        events = storage.get_events(session_id)
        tool_events = storage.get_tool_events(session_id)
        feedback = storage.get_feedback(session_id)
        
        return SessionDetailResponse(
            session_id=session.session_id,
            started_at=session.started_at,
            ended_at=session.ended_at,
            total_tokens=session.total_tokens,
            outcome=session.outcome.value,
            feedback_score=session.feedback_score,
            issue_category=session.issue_category.value,
            osi_layer_resolved=session.osi_layer_resolved,
            message_count=session.message_count,
            user_message_count=session.user_message_count,
            tool_call_count=session.tool_call_count,
            llm_backend=session.llm_backend,
            model_name=session.model_name,
            had_fallback=session.had_fallback,
            estimated_cost_usd=session.estimated_cost_usd,
            time_to_resolution_seconds=session.time_to_resolution_seconds,
            events=[e.to_dict() for e in events],
            tool_events=[te.to_dict() for te in tool_events],
            feedback=feedback.to_dict() if feedback else None,
        )

    @router.get("/summary", response_model=SummaryResponse)
    async def get_summary(
        start_date: datetime | None = Query(default=None, description="Filter by start date"),
        end_date: datetime | None = Query(default=None, description="Filter by end date"),
    ) -> SummaryResponse:
        """Get aggregated analytics summary."""
        summary = storage.get_session_summary(start_date=start_date, end_date=end_date)
        
        return SummaryResponse(
            total_sessions=summary.total_sessions,
            resolved_count=summary.resolved_count,
            unresolved_count=summary.unresolved_count,
            abandoned_count=summary.abandoned_count,
            in_progress_count=summary.in_progress_count,
            success_rate=summary.success_rate,
            avg_tokens_per_session=summary.avg_tokens_per_session,
            avg_time_to_resolution_seconds=summary.avg_time_to_resolution_seconds,
            avg_messages_per_session=summary.avg_messages_per_session,
            total_cost_usd=summary.total_cost_usd,
            ollama_sessions=summary.ollama_sessions,
            openai_sessions=summary.openai_sessions,
            fallback_count=summary.fallback_count,
        )

    @router.get("/tools", response_model=ToolStatsResponse)
    async def get_tool_stats() -> ToolStatsResponse:
        """Get tool usage statistics."""
        stats = storage.get_tool_stats()
        
        return ToolStatsResponse(
            tools=[
                {
                    "tool_name": s.tool_name,
                    "total_calls": s.total_calls,
                    "success_count": s.success_count,
                    "failure_count": s.failure_count,
                    "success_rate": s.success_rate,
                    "avg_execution_time_ms": s.avg_execution_time_ms,
                    "total_execution_time_ms": s.total_execution_time_ms,
                    "loop_occurrences": s.loop_occurrences,
                }
                for s in stats
            ]
        )

    @router.get("/patterns", response_model=PatternsResponse)
    async def get_patterns() -> PatternsResponse:
        """Get diagnostic pattern analysis."""
        return PatternsResponse(
            common_paths=pattern_analyzer.get_common_patterns(),
            category_stats=pattern_analyzer.get_category_stats(),
            osi_layer_stats=pattern_analyzer.get_osi_layer_stats(),
            problematic_tools=pattern_analyzer.detect_problematic_tools(),
            optimization_suggestions=pattern_analyzer.suggest_optimizations(),
        )

    @router.get("/costs", response_model=CostResponse)
    async def get_costs(
        start_date: datetime | None = Query(default=None, description="Filter by start date"),
        end_date: datetime | None = Query(default=None, description="Filter by end date"),
        group_by: str = Query(default="day", description="Group by: day, week, month"),
    ) -> CostResponse:
        """Get cost breakdown by time period."""
        periods = storage.get_cost_by_period(
            start_date=start_date,
            end_date=end_date,
            group_by=group_by,
        )
        
        total_cost = sum(p["total_cost"] for p in periods)
        total_tokens = sum(p["total_tokens"] for p in periods)
        total_sessions = sum(p["session_count"] for p in periods)
        
        return CostResponse(
            periods=periods,
            total_cost=total_cost,
            total_tokens=total_tokens,
            total_sessions=total_sessions,
        )

    @router.get("/quality", response_model=QualityResponse)
    async def get_quality() -> QualityResponse:
        """Get conversation quality metrics."""
        metrics = storage.get_quality_metrics()
        
        return QualityResponse(
            avg_messages_to_resolution=metrics.avg_messages_to_resolution,
            sessions_with_loops=metrics.sessions_with_loops,
            total_loop_occurrences=metrics.total_loop_occurrences,
            abandoned_sessions=metrics.abandoned_sessions,
            drop_off_rate=metrics.drop_off_rate,
        )

    return router


def create_feedback_router(storage: AnalyticsStorage) -> APIRouter:
    """Create the feedback API router.
    
    Args:
        storage: The analytics storage instance to use
        
    Returns:
        Configured APIRouter
    """
    router = APIRouter(tags=["feedback"])

    @router.post("/feedback", response_model=FeedbackResponse)
    async def submit_feedback(request: FeedbackRequest) -> FeedbackResponse:
        """Submit feedback for a session."""
        # Verify session exists
        session = storage.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Create feedback
        feedback = Feedback(
            session_id=request.session_id,
            score=request.score,
            comment=request.comment,
            source=request.source,
        )
        storage.save_feedback(feedback)
        
        # Update session
        session.feedback_score = request.score
        session.feedback_comment = request.comment
        storage.save_session(session)
        
        return FeedbackResponse(
            feedback_id=feedback.feedback_id,
            session_id=feedback.session_id,
            score=feedback.score,
        )

    @router.get("/feedback/{session_id}")
    async def get_feedback(session_id: str) -> dict[str, Any]:
        """Get feedback for a session."""
        feedback = storage.get_feedback(session_id)
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")
        
        return feedback.to_dict()

    return router


