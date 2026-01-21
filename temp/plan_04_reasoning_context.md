# Plan: Add Reasoning Context Preservation

**Priority**: Medium  
**Effort**: Medium  
**Status**: Not Started

---

## Problem

Current implementation doesn't preserve reasoning context between conversation turns:
- Each turn re-reasons from scratch
- Inefficient token usage on cloud models
- Lost context from previous diagnostic steps
- Can't leverage `previous_response_id` patterns from OpenAI/Anthropic

```python
# Current: Only message history preserved, not reasoning
messages_for_llm = [
    {"role": msg.role, "content": msg.content or ""}
    for msg in messages
    if msg.role != "system"
]
```

## Goal

Implement a reasoning context cache that preserves model reasoning between turns, reducing redundant computation and improving multi-turn diagnostic coherence.

---

## Background: How Reasoning Models Work

### OpenAI o1/o3 Models
- Return `reasoning_content` alongside `content`
- Support `previous_response_id` for continuation

### Anthropic Claude with Extended Thinking
- Returns `thinking` blocks in responses
- Can include previous thinking as context

### Ollama (Local Models)
- No explicit reasoning tokens
- Can simulate with explicit chain-of-thought in prompt

---

## Implementation Steps

### Step 1: Create Reasoning Cache Module

**File: `backend/llm/reasoning_cache.py`**

```python
"""Reasoning context preservation for multi-turn conversations.

This module provides a cache for storing and retrieving reasoning
context (chain-of-thought, model thinking) between conversation turns.
"""

import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger("techtime.llm.reasoning_cache")


@dataclass
class ReasoningEntry:
    """A cached reasoning entry for a conversation turn."""
    
    reasoning_content: str | None
    """The model's reasoning/thinking content."""
    
    summary: str | None
    """Condensed summary for context injection."""
    
    response_id: str | None
    """Provider-specific response ID for continuation (OpenAI)."""
    
    tool_results: list[dict[str, Any]]
    """Tool call results from this turn."""
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    """When this entry was created."""
    
    provider: str = ""
    """Which provider generated this reasoning."""


class ReasoningCache:
    """
    Cache for reasoning context across conversation turns.
    
    Features:
    - Per-session reasoning storage
    - TTL-based expiration
    - Size limits to prevent memory bloat
    - Provider-specific handling
    
    Example:
        cache = ReasoningCache()
        
        # After first LLM call
        cache.store(
            session_id="abc123",
            reasoning_content="The user reports WiFi issues...",
            response_id="resp_xyz",
            tool_results=[{"name": "check_adapter_status", "result": "..."}]
        )
        
        # Before next LLM call
        context = cache.get_context_for_prompt(session_id="abc123", provider="openai")
    """
    
    def __init__(
        self,
        max_sessions: int = 100,
        max_entries_per_session: int = 10,
        entry_ttl_minutes: int = 60,
    ):
        """
        Initialize the reasoning cache.
        
        Args:
            max_sessions: Maximum number of sessions to cache
            max_entries_per_session: Maximum reasoning entries per session
            entry_ttl_minutes: Time-to-live for entries in minutes
        """
        self._max_sessions = max_sessions
        self._max_entries = max_entries_per_session
        self._entry_ttl = timedelta(minutes=entry_ttl_minutes)
        
        # session_id -> list of ReasoningEntry (newest last)
        self._cache: OrderedDict[str, list[ReasoningEntry]] = OrderedDict()
    
    def store(
        self,
        session_id: str,
        reasoning_content: str | None = None,
        response_id: str | None = None,
        tool_results: list[dict[str, Any]] | None = None,
        provider: str = "",
    ) -> None:
        """
        Store reasoning context from an LLM response.
        
        Args:
            session_id: The conversation session ID
            reasoning_content: The model's reasoning/thinking content
            response_id: Provider-specific response ID
            tool_results: Tool call results from this turn
            provider: Which provider generated this
        """
        entry = ReasoningEntry(
            reasoning_content=reasoning_content,
            summary=self._summarize_reasoning(reasoning_content),
            response_id=response_id,
            tool_results=tool_results or [],
            provider=provider,
        )
        
        # Initialize session list if needed
        if session_id not in self._cache:
            self._cache[session_id] = []
            self._cache.move_to_end(session_id)  # LRU update
        
        # Add entry
        self._cache[session_id].append(entry)
        
        # Trim old entries
        self._trim_session(session_id)
        self._trim_cache()
        
        logger.debug(
            f"Stored reasoning for session {session_id}: "
            f"{len(reasoning_content or '')} chars, "
            f"{len(tool_results or [])} tool results"
        )
    
    def get_latest(self, session_id: str) -> ReasoningEntry | None:
        """Get the most recent reasoning entry for a session."""
        entries = self._cache.get(session_id, [])
        self._expire_old_entries(session_id)
        entries = self._cache.get(session_id, [])
        return entries[-1] if entries else None
    
    def get_response_id(self, session_id: str) -> str | None:
        """Get the latest response ID for OpenAI continuation."""
        latest = self.get_latest(session_id)
        return latest.response_id if latest else None
    
    def get_context_for_prompt(
        self,
        session_id: str,
        provider: str,
        max_tokens: int = 2000,
    ) -> str | None:
        """
        Generate context string to inject into the next prompt.
        
        Args:
            session_id: The conversation session ID
            provider: The target provider (affects formatting)
            max_tokens: Approximate max tokens for context
        
        Returns:
            Formatted context string, or None if no context available
        """
        entries = self._cache.get(session_id, [])
        self._expire_old_entries(session_id)
        entries = self._cache.get(session_id, [])
        
        if not entries:
            return None
        
        # Format based on provider
        if provider == "anthropic":
            return self._format_for_anthropic(entries, max_tokens)
        elif provider in ("openai", "xai", "google"):
            return self._format_for_openai(entries, max_tokens)
        else:  # ollama, others
            return self._format_for_local(entries, max_tokens)
    
    def _format_for_anthropic(
        self, entries: list[ReasoningEntry], max_tokens: int
    ) -> str:
        """Format context with XML tags for Claude."""
        parts = ["<previous_reasoning>"]
        
        for entry in entries[-3:]:  # Last 3 turns
            if entry.reasoning_content:
                parts.append(f"<turn>{entry.summary or entry.reasoning_content[:500]}</turn>")
            if entry.tool_results:
                tool_summary = ", ".join(
                    f"{t.get('name')}: {t.get('success', 'unknown')}"
                    for t in entry.tool_results
                )
                parts.append(f"<tools_used>{tool_summary}</tools_used>")
        
        parts.append("</previous_reasoning>")
        return "\n".join(parts)
    
    def _format_for_openai(
        self, entries: list[ReasoningEntry], max_tokens: int
    ) -> str:
        """Format context for GPT models."""
        parts = ["## Previous Diagnostic Context\n"]
        
        for i, entry in enumerate(entries[-3:], 1):
            parts.append(f"### Turn {i}")
            if entry.summary:
                parts.append(f"Reasoning: {entry.summary}")
            if entry.tool_results:
                parts.append("Tools: " + ", ".join(
                    f"{t.get('name')}" for t in entry.tool_results
                ))
            parts.append("")
        
        return "\n".join(parts)
    
    def _format_for_local(
        self, entries: list[ReasoningEntry], max_tokens: int
    ) -> str:
        """Format context for local models (condensed)."""
        # Local models have limited context, be very brief
        latest = entries[-1] if entries else None
        if not latest:
            return None
        
        parts = []
        if latest.tool_results:
            tools = [t.get('name') for t in latest.tool_results]
            parts.append(f"Previous: ran {', '.join(tools)}")
        
        return " | ".join(parts) if parts else None
    
    def _summarize_reasoning(self, content: str | None) -> str | None:
        """Create a brief summary of reasoning content."""
        if not content:
            return None
        
        # Simple truncation for now; could use LLM summarization
        if len(content) <= 200:
            return content
        return content[:197] + "..."
    
    def _trim_session(self, session_id: str) -> None:
        """Remove oldest entries if session exceeds limit."""
        entries = self._cache.get(session_id, [])
        if len(entries) > self._max_entries:
            self._cache[session_id] = entries[-self._max_entries:]
    
    def _trim_cache(self) -> None:
        """Remove oldest sessions if cache exceeds limit."""
        while len(self._cache) > self._max_sessions:
            oldest_session = next(iter(self._cache))
            del self._cache[oldest_session]
            logger.debug(f"Evicted session {oldest_session} from reasoning cache")
    
    def _expire_old_entries(self, session_id: str) -> None:
        """Remove entries older than TTL."""
        now = datetime.utcnow()
        entries = self._cache.get(session_id, [])
        self._cache[session_id] = [
            e for e in entries
            if now - e.created_at < self._entry_ttl
        ]
    
    def clear_session(self, session_id: str) -> None:
        """Clear all reasoning for a session."""
        if session_id in self._cache:
            del self._cache[session_id]
    
    def clear_all(self) -> None:
        """Clear the entire cache."""
        self._cache.clear()


# Global instance
_reasoning_cache: ReasoningCache | None = None


def get_reasoning_cache() -> ReasoningCache:
    """Get the global reasoning cache instance."""
    global _reasoning_cache
    if _reasoning_cache is None:
        _reasoning_cache = ReasoningCache()
    return _reasoning_cache
```

### Step 2: Update GlueLLMWrapper to Extract Reasoning

**Modify: `backend/llm/gluellm_wrapper.py`**

```python
from .reasoning_cache import get_reasoning_cache

class GlueLLMWrapper:
    def __init__(self, ...):
        # ... existing init ...
        self._reasoning_cache = get_reasoning_cache()
    
    async def chat(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str | None = None,
        session_id: str | None = None,  # NEW parameter
    ) -> "ChatServiceResponse":
        # ... existing setup ...
        
        # Get previous reasoning context if available
        reasoning_context = None
        if session_id:
            reasoning_context = self._reasoning_cache.get_context_for_prompt(
                session_id=session_id,
                provider=provider,
            )
        
        # Inject reasoning context into system prompt
        if reasoning_context and system_prompt:
            system_prompt = f"{system_prompt}\n\n{reasoning_context}"
        
        # ... existing LLM call ...
        
        # Store reasoning from response
        if session_id:
            reasoning_content = self._extract_reasoning(result)
            self._reasoning_cache.store(
                session_id=session_id,
                reasoning_content=reasoning_content,
                response_id=getattr(result, 'response_id', None),
                tool_results=[
                    {"name": name, "success": success}
                    for name, _, success in self._tool_timings
                ],
                provider=provider,
            )
        
        # ... rest of existing method ...
    
    def _extract_reasoning(self, result: Any) -> str | None:
        """
        Extract reasoning content from LLM response.
        
        Different providers expose this differently:
        - OpenAI: result.reasoning_content
        - Anthropic: result.thinking blocks
        - Others: May not have explicit reasoning
        """
        # Try various attributes that providers might use
        if hasattr(result, 'reasoning_content') and result.reasoning_content:
            return result.reasoning_content
        
        if hasattr(result, 'thinking') and result.thinking:
            return result.thinking
        
        # For providers without explicit reasoning, extract from tool chain
        if hasattr(result, 'tool_calls') and result.tool_calls:
            # Summarize tool sequence as implicit reasoning
            tools = [tc.get('name', 'unknown') for tc in result.tool_calls]
            return f"Diagnostic sequence: {' → '.join(tools)}"
        
        return None
```

### Step 3: Update ChatService to Pass Session ID

**Modify: `backend/chat_service.py`**

```python
async def chat(
    self,
    session_id: str | None,
    user_message: str,
    max_tool_rounds: int | None = None,
) -> ChatServiceResponse:
    # ... existing setup ...
    
    # Call GlueLLM wrapper with session ID for reasoning context
    response = await self._gluellm_wrapper.chat(
        messages=messages_for_llm,
        system_prompt=system_prompt,
        session_id=conv_id,  # NEW: Pass session for reasoning cache
    )
    
    # ... rest of existing method ...
```

### Step 4: Add Configuration

**Modify: `backend/config.py`**

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Reasoning Cache Configuration
    reasoning_cache_enabled: bool = True
    reasoning_cache_max_sessions: int = 100
    reasoning_cache_max_entries: int = 10
    reasoning_cache_ttl_minutes: int = 60
```

### Step 5: Create Tests

**File: `backend/tests/test_reasoning_cache.py`**

```python
"""Tests for reasoning context caching."""

import pytest
from datetime import datetime, timedelta

from backend.llm.reasoning_cache import ReasoningCache, ReasoningEntry


class TestReasoningCache:
    """Test suite for ReasoningCache."""
    
    @pytest.fixture
    def cache(self):
        return ReasoningCache(
            max_sessions=10,
            max_entries_per_session=5,
            entry_ttl_minutes=60,
        )
    
    def test_store_and_retrieve(self, cache):
        """Should store and retrieve reasoning entries."""
        cache.store(
            session_id="session-1",
            reasoning_content="Testing WiFi connectivity...",
            tool_results=[{"name": "check_adapter_status", "success": True}],
            provider="openai",
        )
        
        latest = cache.get_latest("session-1")
        assert latest is not None
        assert latest.reasoning_content == "Testing WiFi connectivity..."
        assert len(latest.tool_results) == 1
    
    def test_multiple_entries_per_session(self, cache):
        """Should store multiple entries and return latest."""
        cache.store(session_id="s1", reasoning_content="First")
        cache.store(session_id="s1", reasoning_content="Second")
        cache.store(session_id="s1", reasoning_content="Third")
        
        latest = cache.get_latest("s1")
        assert latest.reasoning_content == "Third"
    
    def test_max_entries_trim(self, cache):
        """Should trim old entries when limit exceeded."""
        for i in range(10):
            cache.store(session_id="s1", reasoning_content=f"Entry {i}")
        
        # Should only have last 5
        entries = cache._cache.get("s1", [])
        assert len(entries) == 5
        assert entries[0].reasoning_content == "Entry 5"
    
    def test_max_sessions_trim(self, cache):
        """Should evict oldest sessions when limit exceeded."""
        for i in range(15):
            cache.store(session_id=f"session-{i}", reasoning_content=f"Content {i}")
        
        # Should only have 10 sessions
        assert len(cache._cache) == 10
        # Oldest sessions should be gone
        assert "session-0" not in cache._cache
        assert "session-14" in cache._cache
    
    def test_context_format_anthropic(self, cache):
        """Should format context with XML for Anthropic."""
        cache.store(
            session_id="s1",
            reasoning_content="Checking adapter status",
            tool_results=[{"name": "check_adapter_status", "success": True}],
        )
        
        context = cache.get_context_for_prompt("s1", provider="anthropic")
        assert "<previous_reasoning>" in context
        assert "</previous_reasoning>" in context
    
    def test_context_format_openai(self, cache):
        """Should format context with Markdown for OpenAI."""
        cache.store(
            session_id="s1",
            reasoning_content="Checking adapter status",
            tool_results=[{"name": "check_adapter_status", "success": True}],
        )
        
        context = cache.get_context_for_prompt("s1", provider="openai")
        assert "## Previous Diagnostic Context" in context
    
    def test_context_format_local(self, cache):
        """Should format condensed context for local models."""
        cache.store(
            session_id="s1",
            reasoning_content="Checking adapter status",
            tool_results=[{"name": "check_adapter_status", "success": True}],
        )
        
        context = cache.get_context_for_prompt("s1", provider="ollama")
        # Should be very brief
        assert len(context) < 100
    
    def test_no_context_for_new_session(self, cache):
        """Should return None for sessions without history."""
        context = cache.get_context_for_prompt("new-session", provider="openai")
        assert context is None
    
    def test_clear_session(self, cache):
        """Should clear specific session."""
        cache.store(session_id="s1", reasoning_content="Content 1")
        cache.store(session_id="s2", reasoning_content="Content 2")
        
        cache.clear_session("s1")
        
        assert cache.get_latest("s1") is None
        assert cache.get_latest("s2") is not None
```

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/llm/reasoning_cache.py` | Create | Reasoning cache implementation |
| `backend/llm/gluellm_wrapper.py` | Modify | Extract and inject reasoning |
| `backend/chat_service.py` | Modify | Pass session ID to wrapper |
| `backend/config.py` | Modify | Add cache configuration |
| `backend/tests/test_reasoning_cache.py` | Create | Unit tests |

---

## Testing Plan

1. **Unit Tests**
   - Store and retrieve entries
   - Session and entry limits
   - TTL expiration
   - Provider-specific formatting

2. **Integration Tests**
   - Verify reasoning preserved across turns
   - Context injection into prompts
   - Memory usage under load

3. **Manual Testing**
   - Multi-turn diagnostic conversation
   - Check if model references previous findings

---

## Success Criteria

- [ ] Reasoning extracted from LLM responses
- [ ] Context injected into subsequent prompts
- [ ] Provider-specific formatting works
- [ ] Memory bounded by limits
- [ ] Old entries expire correctly
- [ ] Multi-turn diagnostics reference previous findings
- [ ] All tests pass
