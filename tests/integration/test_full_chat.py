"""
Integration tests for full chat workflow.

Tests the complete chat flow from API to ChatService to LLM response.
"""
from unittest.mock import MagicMock, AsyncMock, patch

import pytest


class TestFullChatWorkflow:
    """Tests for complete chat interaction flow."""
    
    @pytest.mark.asyncio
    async def test_chat_flow_with_session(self, initialized_chat_service, sample_session_id):
        """Test complete chat flow with a session."""
        # Send first message
        response1 = await initialized_chat_service.chat(
            sample_session_id,
            "My internet isn't working"
        )
        
        # Verify response structure
        assert response1.content is not None
        assert response1.session_id == sample_session_id
        assert response1.diagnostics is not None
        
        # Send follow-up
        response2 = await initialized_chat_service.chat(
            sample_session_id,
            "I've already restarted my router"
        )
        
        # Should maintain context
        assert response2.session_id == sample_session_id
        
        # Check conversation history
        messages = initialized_chat_service.get_session_messages(sample_session_id)
        user_messages = [m for m in messages if m['role'] == 'user']
        assert len(user_messages) == 2
    
    @pytest.mark.asyncio
    async def test_new_session_generation(self, initialized_chat_service):
        """Test that new sessions are generated when no ID provided."""
        response = await initialized_chat_service.chat(
            None,
            "Hello"
        )
        
        # Should have generated a session ID
        assert response.session_id is not None
        assert len(response.session_id) > 0
        
        # Session should be in the list
        sessions = initialized_chat_service.list_sessions()
        session_ids = [s['id'] for s in sessions]
        assert response.session_id in session_ids
    
    @pytest.mark.asyncio
    async def test_multiple_sessions_isolated(self, initialized_chat_service):
        """Test that multiple sessions are isolated from each other."""
        # Create two sessions
        response1 = await initialized_chat_service.chat("session-A", "Topic A")
        response2 = await initialized_chat_service.chat("session-B", "Topic B")
        
        # Get messages for each
        messages_a = initialized_chat_service.get_session_messages("session-A")
        messages_b = initialized_chat_service.get_session_messages("session-B")
        
        # Should have separate histories
        assert any("Topic A" in str(m.get('content', '')) for m in messages_a)
        assert any("Topic B" in str(m.get('content', '')) for m in messages_b)
        assert not any("Topic B" in str(m.get('content', '')) for m in messages_a)


class TestChatWithMockedTools:
    """Tests for chat interactions with mocked tool execution."""
    
    @pytest.mark.asyncio
    async def test_diagnostics_tracking(self, initialized_chat_service, sample_session_id):
        """Test that diagnostics are properly tracked."""
        response = await initialized_chat_service.chat(
            sample_session_id,
            "Check my network connection"
        )
        
        # Diagnostics should be populated
        diag = response.diagnostics
        assert diag is not None
        assert isinstance(diag.confidence_score, float)
        assert isinstance(diag.thoughts, list)
        assert len(diag.thoughts) > 0
    
    @pytest.mark.asyncio
    async def test_response_serialization(self, initialized_chat_service, sample_session_id):
        """Test that responses can be serialized to dict."""
        response = await initialized_chat_service.chat(
            sample_session_id,
            "Help me"
        )
        
        # Should convert to dict without error
        response_dict = response.to_dict()
        
        assert isinstance(response_dict, dict)
        assert 'response' in response_dict
        assert 'conversation_id' in response_dict


class TestStreamingChat:
    """Tests for streaming chat functionality."""
    
    @pytest.mark.asyncio
    async def test_streaming_emits_chunks(self, initialized_chat_service, sample_session_id):
        """Test that streaming emits multiple chunks."""
        chunks = []
        
        def on_chunk(chunk):
            chunks.append(chunk)
        
        await initialized_chat_service.chat_stream(
            sample_session_id,
            "Hello",
            on_chunk,
        )
        
        # Should have received at least one chunk
        assert len(chunks) > 0
        
        # Should have a done chunk
        chunk_types = [c.type for c in chunks]
        assert 'done' in chunk_types
    
    @pytest.mark.asyncio
    async def test_streaming_error_handling(self, chat_service, sample_session_id):
        """Test that streaming handles errors gracefully."""
        # Use non-initialized service to trigger error
        chunks = []
        
        def on_chunk(chunk):
            chunks.append(chunk)
        
        # This might emit an error chunk or work after auto-init
        await chat_service.chat_stream(
            sample_session_id,
            "Hello",
            on_chunk,
        )
        
        # Should still complete (either success or error chunk)
        chunk_types = [c.type for c in chunks]
        assert 'done' in chunk_types or 'error' in chunk_types


class TestSessionPersistence:
    """Tests for session data persistence."""
    
    @pytest.mark.asyncio
    async def test_session_messages_persist(self, initialized_chat_service, sample_session_id):
        """Test that messages are stored in session."""
        await initialized_chat_service.chat(sample_session_id, "Message 1")
        await initialized_chat_service.chat(sample_session_id, "Message 2")
        
        messages = initialized_chat_service.get_session_messages(sample_session_id)
        
        # Should have user messages
        user_messages = [m for m in messages if m['role'] == 'user']
        assert len(user_messages) >= 2
    
    @pytest.mark.asyncio
    async def test_session_deletion(self, initialized_chat_service, sample_session_id):
        """Test that sessions can be deleted."""
        await initialized_chat_service.chat(sample_session_id, "Hello")
        
        # Verify session exists
        assert len(initialized_chat_service.list_sessions()) > 0
        
        # Delete
        result = initialized_chat_service.delete_session(sample_session_id)
        assert result is True
        
        # Should be gone
        sessions = initialized_chat_service.list_sessions()
        session_ids = [s['id'] for s in sessions]
        assert sample_session_id not in session_ids

