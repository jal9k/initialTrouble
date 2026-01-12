"""Convert GlueLLM ExecutionResult to ChatService response types.

This adapter bridges GlueLLM's response format with our existing
ChatServiceResponse, preserving analytics and diagnostics compatibility.
"""

import logging
from datetime import datetime
from typing import Any

from gluellm import ExecutionResult

logger = logging.getLogger("techtime.llm.result_adapter")


def to_chat_service_response(
    result: ExecutionResult,
    session_id: str,
    tool_timings: list[tuple[str, int, bool]] | None = None,
) -> "ChatServiceResponse":
    """
    Convert GlueLLM ExecutionResult to ChatServiceResponse.
    
    Args:
        result: GlueLLM execution result
        session_id: Session ID to attach to the response
        tool_timings: Optional list of (tool_name, duration_ms, success) tuples
                     from our timing callback (GlueLLM doesn't track timing)
    
    Returns:
        ChatServiceResponse compatible with existing frontend/API
    """
    # Import here to avoid circular imports
    from ..chat_service import (
        ChatServiceResponse,
        ResponseDiagnosticsData,
        ToolUsedInfo,
    )
    
    diagnostics = extract_diagnostics(result, tool_timings)
    
    tool_calls = None
    if result.tool_execution_history:
        tool_calls = [
            {
                "name": tc.get("tool_name", "unknown"),
                "arguments": tc.get("arguments", {}),
                "result": tc.get("result", ""),
                "success": not tc.get("error", False),
            }
            for tc in result.tool_execution_history
        ]
    
    return ChatServiceResponse(
        content=result.final_response or "",
        tool_calls=tool_calls,
        session_id=session_id,
        diagnostics=diagnostics,
        timestamp=datetime.utcnow(),
    )


def extract_diagnostics(
    result: ExecutionResult,
    tool_timings: list[tuple[str, int, bool]] | None = None,
) -> "ResponseDiagnosticsData":
    """
    Extract diagnostics from ExecutionResult.
    
    Creates ResponseDiagnosticsData with:
    - Confidence score calculated from tool success rate
    - Thoughts about the execution (model, tokens, tool count)
    - Tools used list
    
    Args:
        result: GlueLLM execution result
        tool_timings: Optional timing data from our callback
    
    Returns:
        ResponseDiagnosticsData populated from the result
    """
    from ..chat_service import ResponseDiagnosticsData, ToolUsedInfo
    
    diagnostics = ResponseDiagnosticsData()
    
    # Add execution metadata as thoughts
    if result.model:
        diagnostics.thoughts.append(f"Model: {result.model}")
    
    diagnostics.thoughts.append(f"Tool calls made: {result.tool_calls_made}")
    
    if result.tokens_used:
        total = result.tokens_used.get("total", 0)
        prompt = result.tokens_used.get("prompt", 0)
        completion = result.tokens_used.get("completion", 0)
        diagnostics.thoughts.append(
            f"Tokens: {total} (prompt: {prompt}, completion: {completion})"
        )
    
    if result.estimated_cost_usd is not None:
        diagnostics.thoughts.append(f"Estimated cost: ${result.estimated_cost_usd:.6f}")
    
    # Calculate confidence from tool success rate
    diagnostics.confidence_score = calculate_confidence(result.tool_execution_history)
    
    # Build tools_used list with timing data if available
    timing_map = {}
    if tool_timings:
        for name, duration_ms, success in tool_timings:
            timing_map[name] = (duration_ms, success)
    
    for tc in result.tool_execution_history or []:
        tool_name = tc.get("tool_name", "unknown")
        success = not tc.get("error", False)
        
        # Get timing from our callback if available
        duration_ms = None
        if tool_name in timing_map:
            duration_ms, _ = timing_map[tool_name]
        
        diagnostics.tools_used.append(ToolUsedInfo(
            name=tool_name,
            success=success,
            duration_ms=duration_ms,
        ))
    
    return diagnostics


def calculate_confidence(history: list[dict[str, Any]] | None) -> float:
    """
    Calculate confidence score from tool execution history.
    
    Scoring logic:
    - Base confidence: 0.5
    - Each successful tool adds up to 0.1 (total max 0.4 bonus)
    - Failed tools reduce the bonus proportionally
    
    Args:
        history: List of tool execution records from GlueLLM
    
    Returns:
        Confidence score between 0.0 and 1.0
    """
    if not history:
        return 0.5
    
    total = len(history)
    successes = sum(1 for tc in history if not tc.get("error", False))
    
    # Base confidence + bonus for successful tools
    base = 0.5
    if total > 0:
        success_rate = successes / total
        bonus = success_rate * 0.4  # Max +0.4 for 100% success
    else:
        bonus = 0
    
    confidence = min(1.0, base + bonus)
    
    logger.debug(
        f"Calculated confidence: {confidence:.2f} "
        f"({successes}/{total} tools succeeded)"
    )
    
    return confidence


def extract_token_usage(result: ExecutionResult) -> dict[str, int]:
    """
    Extract token usage in a standardized format.
    
    Args:
        result: GlueLLM execution result
    
    Returns:
        Dict with prompt_tokens, completion_tokens, total_tokens
    """
    if not result.tokens_used:
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
    
    return {
        "prompt_tokens": result.tokens_used.get("prompt", 0),
        "completion_tokens": result.tokens_used.get("completion", 0),
        "total_tokens": result.tokens_used.get("total", 0),
    }
