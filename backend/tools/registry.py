"""Tool registry for managing diagnostic functions."""

import inspect
import logging
import time
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from .schemas import ToolCall, ToolDefinition, ToolParameter, ToolResult

if TYPE_CHECKING:
    from analytics import AnalyticsCollector

logger = logging.getLogger("network_diag.tools.registry")
F = TypeVar("F", bound=Callable[..., Any])


class ToolRegistry:
    """Registry for managing diagnostic tools."""

    def __init__(self):
        """Initialize empty registry."""
        self._tools: dict[str, Callable[..., Any]] = {}
        self._definitions: dict[str, ToolDefinition] = {}
        self._analytics: "AnalyticsCollector | None" = None

    def set_analytics(self, collector: "AnalyticsCollector") -> None:
        """Set the analytics collector for tracking tool execution."""
        self._analytics = collector

    def register(
        self,
        name: str,
        description: str,
        parameters: list[ToolParameter] | None = None,
    ) -> Callable[[F], F]:
        """
        Decorator to register a function as a tool.

        Args:
            name: Tool name
            description: Tool description for LLM
            parameters: List of parameter definitions

        Returns:
            Decorator function
        """

        def decorator(func: F) -> F:
            self._tools[name] = func
            self._definitions[name] = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters or [],
            )
            logger.debug(f"Registered tool: {name}")
            return func

        return decorator

    def get_tool(self, name: str) -> Callable[..., Any] | None:
        """Get a registered tool by name."""
        return self._tools.get(name)

    def get_definition(self, name: str) -> ToolDefinition | None:
        """Get a tool definition by name."""
        return self._definitions.get(name)

    def get_all_definitions(self) -> list[ToolDefinition]:
        """Get all registered tool definitions."""
        return list(self._definitions.values())

    def get_openai_tools(self) -> list[dict[str, Any]]:
        """Get all tools in OpenAI schema format."""
        return [d.to_openai_schema() for d in self._definitions.values()]

    def get_ollama_tools(self) -> list[dict[str, Any]]:
        """Get all tools in Ollama schema format."""
        return [d.to_ollama_schema() for d in self._definitions.values()]

    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a tool call.

        Args:
            tool_call: The tool call to execute

        Returns:
            ToolResult with execution result
        """
        # #region debug
        from ..logging_config import debug_log
        debug_log("ToolRegistry", f"Executing tool: {tool_call.name}", {
            "arguments": tool_call.arguments,
            "tool_call_id": tool_call.id,
        })
        # #endregion
        
        tool = self.get_tool(tool_call.name)
        logger.info(f"Executing tool: {tool_call.name} with args: {tool_call.arguments}")

        if tool is None:
            logger.error(f"Unknown tool requested: {tool_call.name}")
            # Record failed tool call in analytics
            if self._analytics:
                self._analytics.record_tool_call(
                    tool_name=tool_call.name,
                    duration_ms=0,
                    success=False,
                    error_message=f"Unknown tool '{tool_call.name}'",
                    arguments=tool_call.arguments,
                )
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                content=f"Error: Unknown tool '{tool_call.name}'",
                success=False,
            )

        # Track execution time
        start_time = time.perf_counter()
        error_message: str | None = None
        success = True
        content = ""

        try:
            # Call the tool (support both sync and async)
            if inspect.iscoroutinefunction(tool):
                result = await tool(**tool_call.arguments)
            else:
                result = tool(**tool_call.arguments)

            # Convert result to string if needed
            if hasattr(result, "to_llm_response"):
                content = result.to_llm_response()
            elif hasattr(result, "model_dump_json"):
                content = result.model_dump_json(indent=2)
            else:
                content = str(result)

        except Exception as e:
            success = False
            error_message = str(e)
            content = f"Error executing tool: {error_message}"
            logger.exception(f"Tool {tool_call.name} failed with error: {e}")

        # Calculate duration
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(f"Tool {tool_call.name} completed in {duration_ms}ms, success={success}")
        
        # #region debug
        from ..logging_config import debug_log
        debug_log("ToolRegistry", f"Tool completed: {tool_call.name}", {
            "success": success,
            "duration_ms": duration_ms,
            "content_length": len(content),
            "error": error_message,
        })
        # #endregion

        # Record in analytics
        if self._analytics:
            # Truncate result summary for storage
            result_summary = content[:200] if len(content) > 200 else content
            self._analytics.record_tool_call(
                tool_name=tool_call.name,
                duration_ms=duration_ms,
                success=success,
                error_message=error_message,
                arguments=tool_call.arguments,
                result_summary=result_summary,
            )

        return ToolResult(
            tool_call_id=tool_call.id,
            name=tool_call.name,
            content=content,
            success=success,
        )

    def __contains__(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)


# Global registry instance
_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    """Get or create global tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def tool(
    name: str,
    description: str,
    parameters: list[ToolParameter] | None = None,
) -> Callable[[F], F]:
    """
    Decorator to register a function as a tool in the global registry.

    Args:
        name: Tool name
        description: Tool description for LLM
        parameters: List of parameter definitions

    Returns:
        Decorator function

    Example:
        @tool(
            name="check_adapter_status",
            description="Check if network adapters are enabled",
        )
        async def check_adapter_status():
            ...
    """
    registry = get_registry()
    return registry.register(name, description, parameters)

