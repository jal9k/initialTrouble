"""
PyWebView API bridge for the TechTim(e) desktop application.

This class is exposed to JavaScript as window.pywebview.api.
All public methods can be called from the frontend.

Threading note: PyWebView calls these methods from a background thread,
not the main thread. We use asyncio.new_event_loop() to run async code.

Example usage from JavaScript:
    const result = await window.pywebview.api.send_message('session-123', 'Hello');
    console.log(result.data.content);
"""
import asyncio
import uuid
import json
import logging
from typing import Any
from concurrent.futures import ThreadPoolExecutor

from backend.config import get_settings
from backend.chat_service import ChatService, StreamChunk
from backend.tools import get_registry
from backend.tools.schemas import ToolCall as ToolCallSchema

# Import from top-level analytics module (NOT backend.analytics)
from analytics import AnalyticsCollector, AnalyticsStorage

from .ollama_manager import OllamaManager

logger = logging.getLogger("techtime.desktop.api")


def api_response(success: bool, data: Any = None, error: str = None) -> dict:
    """Helper to create API response dictionaries."""
    return {
        'success': success,
        'data': data,
        'error': error,
    }


class TechTimApi:
    """
    API exposed to the PyWebView frontend.
    
    Every public method (not starting with _) is callable from JavaScript:
        window.pywebview.api.method_name(args...)
    
    Methods should return dictionaries that will be JSON-serialized.
    Use the api_response helper for consistent response format.
    
    Threading: Methods are called from PyWebView's background thread.
    Use _run_async() to execute async code.
    """
    
    def __init__(self, ollama_manager: OllamaManager):
        """
        Initialize the API bridge.
        
        Args:
            ollama_manager: The Ollama sidecar manager instance
        """
        self._settings = get_settings()
        self.ollama = ollama_manager
        
        # Initialize analytics (matching main.py pattern)
        db_path = self._settings.database_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._analytics_storage = AnalyticsStorage(db_path)
        self._analytics_collector = AnalyticsCollector(storage=self._analytics_storage)
        
        # Initialize chat service with analytics
        self.chat_service = ChatService(
            analytics_collector=self._analytics_collector,
            analytics_storage=self._analytics_storage,
        )
        
        # Tool registry
        self.tool_registry = get_registry()
        
        self._window = None  # Set after window creation
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._initialized = False
        
        logger.info("TechTimApi created")
    
    async def _initialize(self) -> None:
        """Initialize the chat service and tools."""
        if self._initialized:
            return
        
        await self.chat_service.initialize()
        self._initialized = True
        logger.info("TechTimApi initialized")
    
    def set_window(self, window) -> None:
        """
        Set the PyWebView window reference.
        
        This is called after window creation to enable JavaScript callbacks.
        
        Args:
            window: The pywebview.Window instance
        """
        self._window = window
        logger.debug("Window reference set")
    
    def _run_async(self, coro):
        """
        Run an async coroutine from synchronous context.
        
        PyWebView calls methods synchronously, but our backend uses async.
        This helper bridges the gap by creating a new event loop.
        
        Args:
            coro: The coroutine to run
        
        Returns:
            The coroutine's result
        """
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    def _call_js(self, js_code: str) -> None:
        """
        Execute JavaScript in the webview.
        
        Args:
            js_code: JavaScript code to execute
        """
        if self._window:
            self._window.evaluate_js(js_code)
    
    # =========================================================================
    # Session Management
    # =========================================================================
    
    def create_session(self) -> dict:
        """
        Create a new chat session.
        
        Returns:
            API response with session_id in data
        """
        try:
            session_id = str(uuid.uuid4())
            return api_response(True, {'session_id': session_id})
        except Exception as e:
            logger.exception("Error creating session")
            return api_response(False, error=str(e))
    
    def list_sessions(self) -> dict:
        """
        Get all sessions from the database.
        
        Returns:
            API response with list of session summaries
        """
        try:
            # Use analytics storage to get persisted sessions
            sessions = self._analytics_storage.get_sessions(limit=50)
            
            session_list = [
                {
                    "id": s.session_id,
                    "startTime": s.started_at.isoformat(),
                    "outcome": s.outcome.value,
                    "issueCategory": s.issue_category.value if s.issue_category.value != "unknown" else None,
                    "preview": s.preview or "New conversation...",
                    "message_count": s.message_count,
                }
                for s in sessions
            ]
            
            return api_response(True, session_list)
        except Exception as e:
            logger.exception("Error listing sessions")
            return api_response(False, error=str(e))
    
    def get_session_messages(self, session_id: str) -> dict:
        """
        Get message history for a session from the database.
        
        Args:
            session_id: The session to retrieve
        
        Returns:
            API response with list of messages
        """
        try:
            # Get persisted messages from database
            db_messages = self._analytics_storage.get_messages(session_id)
            
            messages = []
            for msg in db_messages:
                if msg.role == "system":
                    continue  # Skip system messages
                messages.append({
                    "id": msg.message_id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                })
            
            return api_response(True, messages)
        except Exception as e:
            logger.exception(f"Error getting messages for session {session_id}")
            return api_response(False, error=str(e))
    
    def delete_session(self, session_id: str) -> dict:
        """
        Delete a chat session from the database.
        
        Args:
            session_id: The session to delete
        
        Returns:
            API response indicating success/failure
        """
        try:
            # Delete from database
            success = self._analytics_storage.delete_session(session_id)
            
            # Also delete from in-memory chat service
            self.chat_service.delete_session(session_id)
            
            if success:
                return api_response(True)
            return api_response(False, error='Session not found')
        except Exception as e:
            logger.exception(f"Error deleting session {session_id}")
            return api_response(False, error=str(e))
    
    # =========================================================================
    # Chat Operations
    # =========================================================================
    
    def send_message(self, session_id: str, message: str) -> dict:
        """
        Send a message and get the complete response.
        
        This is the non-streaming version. It blocks until the LLM
        finishes and all tools have executed.
        
        Args:
            session_id: The conversation session
            message: User's input message
        
        Returns:
            API response with content and tool_results
        """
        async def _send():
            await self._initialize()
            response = await self.chat_service.chat(session_id, message)
            return response.to_dict()
        
        try:
            result = self._run_async(_send())
            return api_response(True, result)
        except Exception as e:
            logger.exception("Error in send_message")
            return api_response(False, error=str(e))
    
    def send_message_streaming(self, session_id: str, message: str) -> dict:
        """
        Send a message with streaming response.
        
        Returns immediately and sends chunks to frontend via callbacks.
        
        The frontend should set up these listeners before calling:
            window.onStreamChunk = (chunk) => { ... };
            window.onStreamDone = () => { ... };
            window.onStreamError = (error) => { ... };
        
        Args:
            session_id: The conversation session
            message: User's input message
        
        Returns:
            API response indicating stream has started
        """
        def on_chunk(chunk: StreamChunk):
            """Send each chunk to the frontend."""
            if self._window:
                chunk_json = json.dumps({
                    'type': chunk.type,
                    'data': chunk.data,
                })
                self._call_js(f'window.onStreamChunk && window.onStreamChunk({chunk_json})')
        
        def run_stream():
            """Background task for streaming."""
            async def _stream():
                try:
                    await self._initialize()
                    await self.chat_service.chat_stream(
                        session_id,
                        message,
                        on_chunk=on_chunk,
                    )
                except Exception as e:
                    logger.exception("Stream error")
                    if self._window:
                        error_json = json.dumps(str(e))
                        self._call_js(f'window.onStreamError && window.onStreamError({error_json})')
                finally:
                    if self._window:
                        self._call_js('window.onStreamDone && window.onStreamDone()')
            
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_stream())
            finally:
                loop.close()
        
        # Run in background thread
        self._executor.submit(run_stream)
        
        return api_response(True, {'status': 'streaming_started'})
    
    # =========================================================================
    # Tool Operations
    # =========================================================================
    
    def list_tools(self) -> dict:
        """
        Get available diagnostic tools.
        
        Returns:
            API response with list of tool definitions
        """
        try:
            tools = self.tool_registry.get_all_definitions()
            tool_list = [
                {
                    'name': t.name,
                    'description': t.description,
                    'parameters': [
                        {
                            'name': p.name,
                            'type': p.type,
                            'description': p.description,
                            'required': p.required,
                        }
                        for p in t.parameters
                    ],
                }
                for t in tools
            ]
            return api_response(True, tool_list)
        except Exception as e:
            logger.exception("Error listing tools")
            return api_response(False, error=str(e))
    
    def execute_tool(self, name: str, arguments: dict) -> dict:
        """
        Manually execute a diagnostic tool.
        
        Args:
            name: Tool name (e.g., 'ping_gateway')
            arguments: Tool parameters as dictionary
        
        Returns:
            API response with tool result
        """
        async def _execute():
            # Create a ToolCall object (matching actual ToolRegistry.execute signature)
            tool_call = ToolCallSchema(
                id=f"manual-{uuid.uuid4().hex[:8]}",
                name=name,
                arguments=arguments,
            )
            
            result = await self.tool_registry.execute(tool_call)
            return {
                'success': result.success,
                'content': result.content,
            }
        
        try:
            result = self._run_async(_execute())
            return api_response(True, result)
        except Exception as e:
            logger.exception(f"Error executing tool {name}")
            return api_response(False, error=str(e))
    
    # =========================================================================
    # Model Management
    # =========================================================================
    
    def list_models(self) -> dict:
        """
        Get downloaded Ollama models.
        
        Returns:
            API response with list of model info
        """
        try:
            models = self._run_async(self.ollama.list_models())
            return api_response(True, models)
        except Exception as e:
            logger.exception("Error listing models")
            return api_response(False, error=str(e))
    
    def check_model_status(self) -> dict:
        """
        Check if the configured model is available.
        
        Returns:
            API response with model availability status
        """
        try:
            has_model = self._run_async(
                self.ollama.has_model(self._settings.ollama_model)
            )
            return api_response(True, {
                'model': self._settings.ollama_model,
                'available': has_model,
            })
        except Exception as e:
            logger.exception("Error checking model status")
            return api_response(False, error=str(e))
    
    def download_model(self, model_name: str) -> dict:
        """
        Start downloading a model.
        
        Progress is sent via window.onModelProgress callback.
        Completion is signaled via window.onModelDownloadComplete callback.
        
        Args:
            model_name: Model to download (e.g., 'mistral:7b-instruct')
        
        Returns:
            API response indicating download started
        """
        def on_progress(progress: dict):
            """Send progress to frontend."""
            if self._window:
                progress_json = json.dumps(progress)
                self._call_js(f'window.onModelProgress && window.onModelProgress({progress_json})')
        
        def run_download():
            """Background download task."""
            try:
                self._run_async(self.ollama.pull_model(model_name, on_progress))
                if self._window:
                    self._call_js(f'window.onModelDownloadComplete && window.onModelDownloadComplete("{model_name}")')
            except Exception as e:
                logger.exception(f"Error downloading model {model_name}")
                if self._window:
                    error_json = json.dumps(str(e))
                    self._call_js(f'window.onModelDownloadError && window.onModelDownloadError({error_json})')
        
        self._executor.submit(run_download)
        
        return api_response(True, {
            'status': 'download_started',
            'model': model_name,
        })
    
    # =========================================================================
    # System Information
    # =========================================================================
    
    def get_app_info(self) -> dict:
        """
        Get application information.
        
        Returns:
            API response with version, paths, and status
        """
        try:
            return api_response(True, {
                'version': '1.0.0',
                'bundled_mode': self._settings.bundled_mode,
                'ollama_host': self._settings.ollama_host,
                'configured_model': self._settings.ollama_model,
                'user_data_path': str(self._settings.user_data_path),
                'ollama_running': self.ollama.is_running(),
            })
        except Exception as e:
            logger.exception("Error getting app info")
            return api_response(False, error=str(e))
    
    def get_diagnostics(self) -> dict:
        """
        Get diagnostic information for troubleshooting.
        
        Returns:
            API response with system diagnostics
        """
        import sys
        import platform
        
        try:
            return api_response(True, {
                'python_version': sys.version,
                'platform': platform.platform(),
                'machine': platform.machine(),
                'bundled_mode': self._settings.bundled_mode,
                'base_path': str(self._settings.base_path),
                'user_data_path': str(self._settings.user_data_path),
                'database_path': str(self._settings.database_path),
                'models_path': str(self._settings.models_path),
                'ollama_host': self._settings.ollama_host,
                'ollama_running': self.ollama.is_running(),
                'tools_count': len(self.tool_registry),
            })
        except Exception as e:
            logger.exception("Error getting diagnostics")
            return api_response(False, error=str(e))
    
    # =========================================================================
    # Analytics (matching existing API)
    # =========================================================================
    
    def get_analytics_summary(self) -> dict:
        """
        Get session analytics summary.
        
        Returns:
            API response with analytics summary
        """
        try:
            summary = self._analytics_storage.get_session_summary()
            return api_response(True, {
                'total_sessions': summary.total_sessions,
                'resolved_count': summary.resolved_count,
                'unresolved_count': summary.unresolved_count,
                'abandoned_count': summary.abandoned_count,
                'in_progress_count': summary.in_progress_count,
                'avg_messages_per_session': summary.avg_messages_per_session,
                'total_cost_usd': summary.total_cost_usd,
            })
        except Exception as e:
            logger.exception("Error getting analytics summary")
            return api_response(False, error=str(e))
    
    def get_tool_stats(self) -> dict:
        """
        Get tool usage statistics.
        
        Returns:
            API response with tool stats
        """
        try:
            stats = self._analytics_storage.get_tool_stats()
            return api_response(True, [
                {
                    'tool_name': s.tool_name,
                    'total_calls': s.total_calls,
                    'success_count': s.success_count,
                    'failure_count': s.failure_count,
                    'avg_execution_time_ms': s.avg_execution_time_ms,
                }
                for s in stats
            ])
        except Exception as e:
            logger.exception("Error getting tool stats")
            return api_response(False, error=str(e))

