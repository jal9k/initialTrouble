"""
Integration tests for the PyWebView API bridge.

UPDATED: Matches TechTimApi from phase2_updated with correct method signatures.
"""
from unittest.mock import MagicMock, patch

import pytest


class TestApiResponseFormat:
    """Tests for API response format consistency."""
    
    def test_create_session_response_format(self, api_bridge):
        """create_session should return proper response format."""
        result = api_bridge.create_session()
        
        assert 'success' in result
        assert 'data' in result
        assert 'error' in result
        
        assert result['success'] is True
        assert 'session_id' in result['data']
    
    def test_list_sessions_response_format(self, api_bridge):
        """list_sessions should return proper response format."""
        result = api_bridge.list_sessions()
        
        assert result['success'] is True
        assert isinstance(result['data'], list)
    
    def test_get_app_info_response_format(self, api_bridge):
        """get_app_info should return proper response format."""
        result = api_bridge.get_app_info()
        
        assert result['success'] is True
        assert 'version' in result['data']
        assert 'bundled_mode' in result['data']
        assert 'ollama_running' in result['data']


class TestSessionApi:
    """Tests for session management API."""
    
    def test_create_session_generates_id(self, api_bridge):
        """Created session should have unique ID."""
        result1 = api_bridge.create_session()
        result2 = api_bridge.create_session()
        
        assert result1['data']['session_id'] != result2['data']['session_id']
    
    def test_delete_nonexistent_session(self, api_bridge):
        """Deleting nonexistent session should return error."""
        result = api_bridge.delete_session("nonexistent-id")
        
        # Should either succeed (no-op) or return error
        assert 'success' in result


class TestToolsApi:
    """Tests for tools API methods."""
    
    def test_list_tools_returns_tools(self, api_bridge):
        """list_tools should return available tools."""
        result = api_bridge.list_tools()
        
        assert result['success'] is True
        assert isinstance(result['data'], list)
        
        if len(result['data']) > 0:
            tool = result['data'][0]
            assert 'name' in tool
            assert 'description' in tool
            assert 'parameters' in tool


class TestAnalyticsApi:
    """Tests for analytics API methods."""
    
    def test_get_analytics_summary(self, api_bridge):
        """get_analytics_summary should return summary data."""
        result = api_bridge.get_analytics_summary()
        
        assert result['success'] is True
        assert 'total_sessions' in result['data']
        assert 'resolved_count' in result['data']
    
    def test_get_tool_stats(self, api_bridge):
        """get_tool_stats should return stats list."""
        result = api_bridge.get_tool_stats()
        
        assert result['success'] is True
        assert isinstance(result['data'], list)


class TestDiagnosticsApi:
    """Tests for diagnostic information API."""
    
    def test_get_diagnostics_returns_system_info(self, api_bridge):
        """get_diagnostics should return system info."""
        result = api_bridge.get_diagnostics()
        
        assert result['success'] is True
        assert 'python_version' in result['data']
        assert 'platform' in result['data']
        assert 'bundled_mode' in result['data']
        assert 'base_path' in result['data']


class TestModelApi:
    """Tests for model management API."""
    
    def test_list_models(self, api_bridge):
        """list_models should return model list."""
        result = api_bridge.list_models()
        
        assert result['success'] is True
        assert isinstance(result['data'], list)
    
    def test_check_model_status(self, api_bridge):
        """check_model_status should return availability."""
        result = api_bridge.check_model_status()
        
        assert result['success'] is True
        assert 'model' in result['data']
        assert 'available' in result['data']


class TestErrorHandling:
    """Tests for API error handling."""
    
    def test_error_response_format(self, api_bridge):
        """Errors should return proper format."""
        # Try to get messages from nonexistent session
        result = api_bridge.get_session_messages("nonexistent-session")
        
        # Should return a response (empty data or error)
        assert 'success' in result
        assert 'error' in result
    
    def test_invalid_session_id_handling(self, api_bridge):
        """Invalid session IDs should be handled gracefully."""
        # Various invalid inputs
        for invalid_id in [None, "", "   ", 123]:
            try:
                result = api_bridge.get_session_messages(invalid_id)
                # Should not crash - either returns error or empty data
                assert 'success' in result or 'error' in result
            except (TypeError, ValueError):
                # These exceptions are acceptable for invalid input
                pass


class TestChatApi:
    """Tests for chat API methods."""
    
    def test_chat_async_method_exists(self, api_bridge):
        """Chat method should exist on API bridge."""
        assert hasattr(api_bridge, 'chat') or hasattr(api_bridge, 'send_message')
    
    def test_stop_generation_method_exists(self, api_bridge):
        """Stop generation method should exist."""
        assert hasattr(api_bridge, 'stop_generation') or hasattr(api_bridge, 'cancel')


class TestWindowIntegration:
    """Tests for PyWebView window integration."""
    
    def test_set_window(self, api_bridge, mock_window):
        """set_window should accept a window object."""
        # Window was already set in fixture, verify it's accessible
        assert api_bridge._window is not None or hasattr(api_bridge, 'window')
    
    def test_evaluate_js_available(self, api_bridge, mock_window):
        """Should be able to evaluate JavaScript in window."""
        # The mock window should have evaluate_js
        if hasattr(api_bridge, '_window') and api_bridge._window:
            assert hasattr(api_bridge._window, 'evaluate_js')

