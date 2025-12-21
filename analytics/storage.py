"""SQLite storage backend for analytics data."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

from .models import (
    Event,
    Feedback,
    IssueCategory,
    ResolutionPath,
    Session,
    SessionOutcome,
    SessionSummary,
    ToolEvent,
    ToolStats,
    QualityMetrics,
)


class AnalyticsStorage:
    """SQLite storage backend for analytics data."""

    def __init__(self, db_path: str | Path = "analytics.db"):
        """Initialize storage with database path."""
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    total_prompt_tokens INTEGER DEFAULT 0,
                    total_completion_tokens INTEGER DEFAULT 0,
                    outcome TEXT DEFAULT 'in_progress',
                    feedback_score INTEGER,
                    feedback_comment TEXT,
                    issue_category TEXT DEFAULT 'unknown',
                    osi_layer_resolved INTEGER,
                    message_count INTEGER DEFAULT 0,
                    user_message_count INTEGER DEFAULT 0,
                    tool_call_count INTEGER DEFAULT 0,
                    llm_backend TEXT,
                    model_name TEXT,
                    had_fallback INTEGER DEFAULT 0,
                    estimated_cost_usd REAL DEFAULT 0.0,
                    total_llm_time_ms INTEGER DEFAULT 0,
                    total_tool_time_ms INTEGER DEFAULT 0
                )
            """)

            # Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    duration_ms INTEGER,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)

            # Tool events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tool_events (
                    event_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    execution_time_ms INTEGER DEFAULT 0,
                    success INTEGER DEFAULT 1,
                    error_message TEXT,
                    is_repeated INTEGER DEFAULT 0,
                    consecutive_count INTEGER DEFAULT 1,
                    arguments TEXT,
                    result_summary TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)

            # Feedback table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    comment TEXT,
                    timestamp TEXT NOT NULL,
                    source TEXT DEFAULT 'cli',
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)

            # Resolution paths table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resolution_paths (
                    path_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    tool_sequence TEXT NOT NULL,
                    was_successful INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)

            # Create indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_started_at 
                ON sessions(started_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_outcome 
                ON sessions(outcome)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_session_id 
                ON events(session_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tool_events_session_id 
                ON tool_events(session_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tool_events_tool_name 
                ON tool_events(tool_name)
            """)

            conn.commit()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # Session operations

    def save_session(self, session: Session) -> None:
        """Save or update a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sessions (
                    session_id, started_at, ended_at, total_prompt_tokens,
                    total_completion_tokens, outcome, feedback_score, feedback_comment,
                    issue_category, osi_layer_resolved, message_count, user_message_count,
                    tool_call_count, llm_backend, model_name, had_fallback,
                    estimated_cost_usd, total_llm_time_ms, total_tool_time_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id,
                session.started_at.isoformat(),
                session.ended_at.isoformat() if session.ended_at else None,
                session.total_prompt_tokens,
                session.total_completion_tokens,
                session.outcome.value,
                session.feedback_score,
                session.feedback_comment,
                session.issue_category.value,
                session.osi_layer_resolved,
                session.message_count,
                session.user_message_count,
                session.tool_call_count,
                session.llm_backend,
                session.model_name,
                1 if session.had_fallback else 0,
                session.estimated_cost_usd,
                session.total_llm_time_ms,
                session.total_tool_time_ms,
            ))
            conn.commit()

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_session(row)

    def get_sessions(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        outcome: SessionOutcome | None = None,
        category: IssueCategory | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Session]:
        """Get sessions with optional filters."""
        query = "SELECT * FROM sessions WHERE 1=1"
        params: list[Any] = []

        if start_date:
            query += " AND started_at >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND started_at <= ?"
            params.append(end_date.isoformat())
        if outcome:
            query += " AND outcome = ?"
            params.append(outcome.value)
        if category:
            query += " AND issue_category = ?"
            params.append(category.value)

        query += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [self._row_to_session(row) for row in cursor.fetchall()]

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        """Convert a database row to a Session object."""
        return Session(
            session_id=row["session_id"],
            started_at=datetime.fromisoformat(row["started_at"]),
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            total_prompt_tokens=row["total_prompt_tokens"],
            total_completion_tokens=row["total_completion_tokens"],
            outcome=SessionOutcome(row["outcome"]),
            feedback_score=row["feedback_score"],
            feedback_comment=row["feedback_comment"],
            issue_category=IssueCategory(row["issue_category"]),
            osi_layer_resolved=row["osi_layer_resolved"],
            message_count=row["message_count"],
            user_message_count=row["user_message_count"],
            tool_call_count=row["tool_call_count"],
            llm_backend=row["llm_backend"],
            model_name=row["model_name"],
            had_fallback=bool(row["had_fallback"]),
            estimated_cost_usd=row["estimated_cost_usd"],
            total_llm_time_ms=row["total_llm_time_ms"],
            total_tool_time_ms=row["total_tool_time_ms"],
        )

    # Event operations

    def save_event(self, event: Event) -> None:
        """Save an event."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO events (
                    event_id, session_id, event_type, timestamp,
                    duration_ms, prompt_tokens, completion_tokens, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.session_id,
                event.event_type.value,
                event.timestamp.isoformat(),
                event.duration_ms,
                event.prompt_tokens,
                event.completion_tokens,
                json.dumps(event.metadata),
            ))
            conn.commit()

    def get_events(self, session_id: str) -> list[Event]:
        """Get all events for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM events WHERE session_id = ? ORDER BY timestamp",
                (session_id,)
            )
            return [self._row_to_event(row) for row in cursor.fetchall()]

    def _row_to_event(self, row: sqlite3.Row) -> Event:
        """Convert a database row to an Event object."""
        from .models import EventType
        return Event(
            event_id=row["event_id"],
            session_id=row["session_id"],
            event_type=EventType(row["event_type"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            duration_ms=row["duration_ms"],
            prompt_tokens=row["prompt_tokens"],
            completion_tokens=row["completion_tokens"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    # Tool event operations

    def save_tool_event(self, tool_event: ToolEvent) -> None:
        """Save a tool event."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO tool_events (
                    event_id, session_id, timestamp, tool_name,
                    execution_time_ms, success, error_message,
                    is_repeated, consecutive_count, arguments, result_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tool_event.event_id,
                tool_event.session_id,
                tool_event.timestamp.isoformat(),
                tool_event.tool_name,
                tool_event.execution_time_ms,
                1 if tool_event.success else 0,
                tool_event.error_message,
                1 if tool_event.is_repeated else 0,
                tool_event.consecutive_count,
                json.dumps(tool_event.arguments),
                tool_event.result_summary,
            ))
            conn.commit()

    def get_tool_events(self, session_id: str) -> list[ToolEvent]:
        """Get all tool events for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM tool_events WHERE session_id = ? ORDER BY timestamp",
                (session_id,)
            )
            return [self._row_to_tool_event(row) for row in cursor.fetchall()]

    def _row_to_tool_event(self, row: sqlite3.Row) -> ToolEvent:
        """Convert a database row to a ToolEvent object."""
        return ToolEvent(
            event_id=row["event_id"],
            session_id=row["session_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            tool_name=row["tool_name"],
            execution_time_ms=row["execution_time_ms"],
            success=bool(row["success"]),
            error_message=row["error_message"],
            is_repeated=bool(row["is_repeated"]),
            consecutive_count=row["consecutive_count"],
            arguments=json.loads(row["arguments"]) if row["arguments"] else {},
            result_summary=row["result_summary"],
        )

    # Feedback operations

    def save_feedback(self, feedback: Feedback) -> None:
        """Save feedback."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO feedback (
                    feedback_id, session_id, score, comment, timestamp, source
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                feedback.feedback_id,
                feedback.session_id,
                feedback.score,
                feedback.comment,
                feedback.timestamp.isoformat(),
                feedback.source,
            ))
            conn.commit()

    def get_feedback(self, session_id: str) -> Feedback | None:
        """Get feedback for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM feedback WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return Feedback(
                feedback_id=row["feedback_id"],
                session_id=row["session_id"],
                score=row["score"],
                comment=row["comment"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                source=row["source"],
            )

    # Resolution path operations

    def save_resolution_path(self, path: ResolutionPath) -> None:
        """Save a resolution path."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO resolution_paths (
                    path_id, session_id, tool_sequence, was_successful, created_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                path.path_id,
                path.session_id,
                json.dumps(path.tool_sequence),
                1 if path.was_successful else 0,
                path.created_at.isoformat(),
            ))
            conn.commit()

    def get_resolution_paths(
        self, 
        successful_only: bool = False,
        limit: int = 100
    ) -> list[ResolutionPath]:
        """Get resolution paths."""
        query = "SELECT * FROM resolution_paths"
        params: list[Any] = []
        
        if successful_only:
            query += " WHERE was_successful = 1"
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [
                ResolutionPath(
                    path_id=row["path_id"],
                    session_id=row["session_id"],
                    tool_sequence=json.loads(row["tool_sequence"]),
                    was_successful=bool(row["was_successful"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                for row in cursor.fetchall()
            ]

    # Aggregation methods

    def get_session_summary(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> SessionSummary:
        """Get aggregated session statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Build date filter
            date_filter = ""
            params: list[Any] = []
            if start_date:
                date_filter += " AND started_at >= ?"
                params.append(start_date.isoformat())
            if end_date:
                date_filter += " AND started_at <= ?"
                params.append(end_date.isoformat())

            # Count by outcome
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'resolved' THEN 1 ELSE 0 END) as resolved,
                    SUM(CASE WHEN outcome = 'unresolved' THEN 1 ELSE 0 END) as unresolved,
                    SUM(CASE WHEN outcome = 'abandoned' THEN 1 ELSE 0 END) as abandoned,
                    SUM(CASE WHEN outcome = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                    AVG(total_prompt_tokens + total_completion_tokens) as avg_tokens,
                    AVG(message_count) as avg_messages,
                    SUM(estimated_cost_usd) as total_cost,
                    SUM(CASE WHEN llm_backend = 'ollama' THEN 1 ELSE 0 END) as ollama_count,
                    SUM(CASE WHEN llm_backend = 'openai' THEN 1 ELSE 0 END) as openai_count,
                    SUM(had_fallback) as fallback_count
                FROM sessions
                WHERE 1=1 {date_filter}
            """, params)
            
            row = cursor.fetchone()

            # Calculate average time to resolution for resolved sessions
            cursor.execute(f"""
                SELECT AVG(
                    (julianday(ended_at) - julianday(started_at)) * 86400
                ) as avg_ttr
                FROM sessions
                WHERE outcome = 'resolved' AND ended_at IS NOT NULL {date_filter}
            """, params)
            ttr_row = cursor.fetchone()
            avg_ttr = ttr_row["avg_ttr"] if ttr_row and ttr_row["avg_ttr"] else 0.0

            return SessionSummary(
                total_sessions=row["total"] or 0,
                resolved_count=row["resolved"] or 0,
                unresolved_count=row["unresolved"] or 0,
                abandoned_count=row["abandoned"] or 0,
                in_progress_count=row["in_progress"] or 0,
                avg_tokens_per_session=row["avg_tokens"] or 0.0,
                avg_time_to_resolution_seconds=avg_ttr,
                avg_messages_per_session=row["avg_messages"] or 0.0,
                total_cost_usd=row["total_cost"] or 0.0,
                ollama_sessions=row["ollama_count"] or 0,
                openai_sessions=row["openai_count"] or 0,
                fallback_count=row["fallback_count"] or 0,
            )

    def get_tool_stats(self) -> list[ToolStats]:
        """Get aggregated tool statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    tool_name,
                    COUNT(*) as total_calls,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failure_count,
                    AVG(execution_time_ms) as avg_time,
                    SUM(execution_time_ms) as total_time,
                    SUM(CASE WHEN is_repeated = 1 THEN 1 ELSE 0 END) as loop_count
                FROM tool_events
                GROUP BY tool_name
                ORDER BY total_calls DESC
            """)
            
            return [
                ToolStats(
                    tool_name=row["tool_name"],
                    total_calls=row["total_calls"],
                    success_count=row["success_count"],
                    failure_count=row["failure_count"],
                    avg_execution_time_ms=row["avg_time"] or 0.0,
                    total_execution_time_ms=row["total_time"] or 0,
                    loop_occurrences=row["loop_count"] or 0,
                )
                for row in cursor.fetchall()
            ]

    def get_quality_metrics(self) -> QualityMetrics:
        """Get conversation quality metrics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Average messages to resolution
            cursor.execute("""
                SELECT AVG(user_message_count) as avg_messages
                FROM sessions
                WHERE outcome = 'resolved'
            """)
            row = cursor.fetchone()
            avg_messages = row["avg_messages"] if row and row["avg_messages"] else 0.0

            # Sessions with loops
            cursor.execute("""
                SELECT COUNT(DISTINCT session_id) as sessions_with_loops,
                       COUNT(*) as total_loops
                FROM tool_events
                WHERE is_repeated = 1
            """)
            row = cursor.fetchone()
            sessions_with_loops = row["sessions_with_loops"] or 0
            total_loops = row["total_loops"] or 0

            # Abandoned sessions
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'abandoned' THEN 1 ELSE 0 END) as abandoned
                FROM sessions
            """)
            row = cursor.fetchone()
            total = row["total"] or 1
            abandoned = row["abandoned"] or 0
            drop_off_rate = (abandoned / total) * 100 if total > 0 else 0.0

            return QualityMetrics(
                avg_messages_to_resolution=avg_messages,
                sessions_with_loops=sessions_with_loops,
                total_loop_occurrences=total_loops,
                abandoned_sessions=abandoned,
                drop_off_rate=drop_off_rate,
            )

    def get_common_resolution_paths(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get most common successful resolution paths."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tool_sequence, COUNT(*) as count
                FROM resolution_paths
                WHERE was_successful = 1
                GROUP BY tool_sequence
                ORDER BY count DESC
                LIMIT ?
            """, (limit,))
            
            return [
                {
                    "tool_sequence": json.loads(row["tool_sequence"]),
                    "count": row["count"],
                }
                for row in cursor.fetchall()
            ]

    def get_issue_category_breakdown(self) -> dict[str, int]:
        """Get breakdown of sessions by issue category."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT issue_category, COUNT(*) as count
                FROM sessions
                GROUP BY issue_category
            """)
            return {row["issue_category"]: row["count"] for row in cursor.fetchall()}

    def get_cost_by_period(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        group_by: str = "day",  # "day", "week", "month"
    ) -> list[dict[str, Any]]:
        """Get cost breakdown by time period."""
        date_format = {
            "day": "%Y-%m-%d",
            "week": "%Y-%W",
            "month": "%Y-%m",
        }.get(group_by, "%Y-%m-%d")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = f"""
                SELECT 
                    strftime('{date_format}', started_at) as period,
                    SUM(estimated_cost_usd) as total_cost,
                    SUM(total_prompt_tokens + total_completion_tokens) as total_tokens,
                    COUNT(*) as session_count
                FROM sessions
                WHERE llm_backend = 'openai'
            """
            params: list[Any] = []
            
            if start_date:
                query += " AND started_at >= ?"
                params.append(start_date.isoformat())
            if end_date:
                query += " AND started_at <= ?"
                params.append(end_date.isoformat())
            
            query += f" GROUP BY strftime('{date_format}', started_at) ORDER BY period"
            
            cursor.execute(query, params)
            return [
                {
                    "period": row["period"],
                    "total_cost": row["total_cost"] or 0.0,
                    "total_tokens": row["total_tokens"] or 0,
                    "session_count": row["session_count"],
                }
                for row in cursor.fetchall()
            ]

