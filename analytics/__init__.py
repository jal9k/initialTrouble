"""Analytics module for Network Diagnostics.

This module provides comprehensive analytics tracking including:
- Token usage and response timing
- Time to resolution
- Tool analytics (frequency, success rates, execution time)
- Diagnostic patterns (issue categories, OSI layer stats, resolution paths)
- Conversation quality (messages to resolution, loop detection, drop-offs)
- Model performance (backend used, fallback events)
- Cost tracking (for OpenAI)
"""

from .models import (
    Session,
    Event,
    ToolEvent,
    Feedback,
    ResolutionPath,
    SessionOutcome,
    IssueCategory,
    EventType,
    ToolStats,
    SessionSummary,
    QualityMetrics,
)
from .collector import AnalyticsCollector, get_collector, reset_collector
from .storage import AnalyticsStorage
from .cost import CostCalculator
from .patterns import PatternAnalyzer

__all__ = [
    # Models
    "Session",
    "Event",
    "ToolEvent",
    "Feedback",
    "ResolutionPath",
    "SessionOutcome",
    "IssueCategory",
    "EventType",
    "ToolStats",
    "SessionSummary",
    "QualityMetrics",
    # Core
    "AnalyticsCollector",
    "get_collector",
    "reset_collector",
    "AnalyticsStorage",
    "CostCalculator",
    "PatternAnalyzer",
]

