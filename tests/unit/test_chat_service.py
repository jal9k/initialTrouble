"""
Unit tests for the ChatService.

UPDATED: Uses correct method signatures from phase1_updated ChatService.
- chat(session_id, user_message) instead of chat(message)
- ChatServiceResponse instead of ChatResponse
- _get_or_create_conversation() is internal
"""
from unittest.mock import MagicMock, AsyncMock

import pytest

from backend.chat_service import ChatService, ChatServiceResponse, StreamChunk


class TestChatBasic:
    """Tests for basic chat functionality."""
    
    @pytest.mark.asyncio
    async def test_chat_returns_response(self, initialized_chat_service, sample_session_id):
        """
        UPDATED: Chat should return ChatServiceResponse.
        """
        response = await initialized_chat_service.chat(
            sample_session_id,
            "Hello, I need help"
        )
        
        assert isinstance(response, ChatServiceResponse)
        assert response.content is not None
        assert response.session_id == sample_session_id
    
    @pytest.mark.asyncio
    async def test_chat_stores_messages(self, initialized_chat_service, sample_session_id):
        """Chat should store messages in conversation."""
        await initialized_chat_service.chat(sample_session_id, "Hello")
        
        messages = initialized_chat_service.get_session_messages(sample_session_id)
        
        # Should have at least user message
        assert len(messages) >= 1
        assert any(m['role'] == 'user' for m in messages)
    
    @pytest.mark.asyncio
    async def test_chat_maintains_conversation_history(self, initialized_chat_service, sample_session_id):
        """Multiple chat calls should maintain history."""
        await initialized_chat_service.chat(sample_session_id, "First message")
        await initialized_chat_service.chat(sample_session_id, "Second message")
        await initialized_chat_service.chat(sample_session_id, "Third message")
        
        messages = initialized_chat_service.get_session_messages(sample_session_id)
        user_messages = [m for m in messages if m['role'] == 'user']
        
        assert len(user_messages) == 3
    
    @pytest.mark.asyncio
    async def test_new_session_creates_conversation(self, initialized_chat_service):
        """New session ID should create new conversation."""
        response = await initialized_chat_service.chat(None, "Hello")
        
        # Should get a session ID back
        assert response.session_id is not None
        assert len(response.session_id) > 0


class TestSessionManagement:
    """Tests for session listing and management."""
    
    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, initialized_chat_service):
        """Listing sessions when none exist should return empty list."""
        sessions = initialized_chat_service.list_sessions()
        
        assert sessions == []
    
    @pytest.mark.asyncio
    async def test_list_sessions_with_data(self, initialized_chat_service):
        """Listing sessions should return summaries."""
        await initialized_chat_service.chat("session-1", "Hello 1")
        await initialized_chat_service.chat("session-2", "Hello 2")
        
        sessions = initialized_chat_service.list_sessions()
        
        assert len(sessions) == 2
        assert all('id' in s for s in sessions)
        assert all('message_count' in s for s in sessions)
    
    @pytest.mark.asyncio
    async def test_get_session_messages_empty(self, initialized_chat_service):
        """Empty session should return empty list."""
        messages = initialized_chat_service.get_session_messages("nonexistent")
        
        assert messages == []
    
    @pytest.mark.asyncio
    async def test_delete_session(self, initialized_chat_service, sample_session_id):
        """Deleting a session should remove it."""
        await initialized_chat_service.chat(sample_session_id, "Hello")
        
        result = initialized_chat_service.delete_session(sample_session_id)
        
        assert result is True
        assert len(initialized_chat_service.list_sessions()) == 0
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, initialized_chat_service):
        """Deleting a nonexistent session should return False."""
        result = initialized_chat_service.delete_session("does-not-exist")
        
        assert result is False


class TestChatWithTools:
    """Tests for chat with tool execution."""
    
    @pytest.mark.asyncio
    async def test_chat_includes_diagnostics(
        self,
        initialized_chat_service,
        sample_session_id,
    ):
        """Response should include diagnostics."""
        response = await initialized_chat_service.chat(
            sample_session_id,
            "Check my network"
        )
        
        assert response.diagnostics is not None
        assert hasattr(response.diagnostics, 'confidence_score')
        assert hasattr(response.diagnostics, 'thoughts')
        assert hasattr(response.diagnostics, 'tools_used')


class TestChatStreaming:
    """Tests for streaming chat functionality."""
    
    @pytest.mark.asyncio
    async def test_stream_calls_on_chunk(self, initialized_chat_service, sample_session_id):
        """Streaming should call the on_chunk callback."""
        chunks_received = []
        
        def on_chunk(chunk: StreamChunk):
            chunks_received.append(chunk)
        
        await initialized_chat_service.chat_stream(
            sample_session_id,
            "Hello",
            on_chunk,
        )
        
        assert len(chunks_received) > 0
    
    @pytest.mark.asyncio
    async def test_stream_sends_done_chunk(self, initialized_chat_service, sample_session_id):
        """Streaming should end with a done chunk."""
        chunks_received = []
        
        def on_chunk(chunk: StreamChunk):
            chunks_received.append(chunk)
        
        await initialized_chat_service.chat_stream(
            sample_session_id,
            "Hello",
            on_chunk,
        )
        
        assert any(c.type == 'done' for c in chunks_received)


class TestResponseDiagnostics:
    """Tests for response diagnostics tracking."""
    
    @pytest.mark.asyncio
    async def test_diagnostics_tracks_thoughts(self, initialized_chat_service, sample_session_id):
        """Diagnostics should track reasoning thoughts."""
        response = await initialized_chat_service.chat(
            sample_session_id,
            "What's wrong with my network?"
        )
        
        assert response.diagnostics.thoughts is not None
        assert isinstance(response.diagnostics.thoughts, list)
    
    @pytest.mark.asyncio
    async def test_diagnostics_has_confidence_score(self, initialized_chat_service, sample_session_id):
        """Diagnostics should include confidence score."""
        response = await initialized_chat_service.chat(
            sample_session_id,
            "Check DNS"
        )
        
        score = response.diagnostics.confidence_score
        assert 0.0 <= score <= 1.0


class TestChatServiceResponse:
    """Tests for ChatServiceResponse model."""
    
    def test_response_to_dict(self):
        """ChatServiceResponse should convert to dict correctly."""
        from backend.chat_service import ResponseDiagnosticsData
        
        diagnostics = ResponseDiagnosticsData(
            confidence_score=0.8,
            thoughts=["Thought 1", "Thought 2"],
            tools_used=[],
        )
        
        response = ChatServiceResponse(
            content="Test content",
            session_id="test-123",
            diagnostics=diagnostics,
        )
        
        result = response.to_dict()
        
        assert result['response'] == "Test content"
        assert result['conversation_id'] == "test-123"
        assert result['diagnostics']['confidence_score'] == 0.8
    
    def test_response_without_diagnostics(self):
        """ChatServiceResponse without diagnostics should serialize."""
        response = ChatServiceResponse(
            content="Test content",
            session_id="test-123",
            diagnostics=None,
        )
        
        result = response.to_dict()
        
        assert result['diagnostics'] is None


class TestChatServiceInitialization:
    """Tests for ChatService initialization."""
    
    @pytest.mark.asyncio
    async def test_initialize_sets_up_tool_registry(self, chat_service):
        """Initialize should set up the tool registry."""
        await chat_service.initialize()
        
        assert chat_service._initialized is True
    
    @pytest.mark.asyncio
    async def test_double_initialize_is_safe(self, chat_service):
        """Calling initialize twice should be safe."""
        await chat_service.initialize()
        await chat_service.initialize()
        
        assert chat_service._initialized is True
    
    @pytest.mark.asyncio
    async def test_close_cleans_up_router(self, initialized_chat_service):
        """Close should clean up the LLM router."""
        await initialized_chat_service.close()
        
        # Router close should have been called
        initialized_chat_service._llm_router.close.assert_called()

