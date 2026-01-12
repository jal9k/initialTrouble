"""Convert ToolRegistry tools to GlueLLM-compatible callables.

GlueLLM auto-generates tool schemas from function signatures and docstrings,
so this module wraps each registered tool with proper typing and timing.
"""

import asyncio
import inspect
import logging
import time
from functools import wraps
from typing import Any, Callable

from ..tools import ToolRegistry
from ..tools.schemas import ToolDefinition

logger = logging.getLogger("techtime.llm.tool_adapter")


def registry_to_callables(
    registry: ToolRegistry,
    timing_callback: Callable[[str, int, bool], None] | None = None,
) -> list[Callable]:
    """
    Convert all tools in a ToolRegistry to callable functions.
    
    GlueLLM auto-generates tool schemas from function signatures
    and docstrings, so we wrap each tool with proper typing.
    
    Args:
        registry: The ToolRegistry containing registered tools
        timing_callback: Optional callback for timing tracking.
                        Called with (tool_name, duration_ms, success)
    
    Returns:
        List of callable functions ready for GlueLLM
    """
    callables = []
    
    for definition in registry.get_all_definitions():
        tool_func = registry.get_tool(definition.name)
        if tool_func:
            wrapped = _wrap_tool(definition, tool_func, timing_callback)
            callables.append(wrapped)
            logger.debug(f"Converted tool '{definition.name}' to callable")
    
    logger.info(f"Converted {len(callables)} tools to GlueLLM callables")
    return callables


def _wrap_tool(
    definition: ToolDefinition,
    func: Callable,
    timing_callback: Callable[[str, int, bool], None] | None,
) -> Callable:
    """
    Wrap a tool function with timing and proper docstring.
    
    The wrapper:
    1. Tracks execution time
    2. Handles both sync and async functions
    3. Converts results to strings for LLM consumption
    4. Reports timing via callback if provided
    
    Args:
        definition: Tool definition with name and description
        func: The actual tool function to wrap
        timing_callback: Optional callback for timing
    
    Returns:
        Wrapped async function suitable for GlueLLM
    """
    is_async = asyncio.iscoroutinefunction(func)
    
    @wraps(func)
    async def wrapper(**kwargs: Any) -> str:
        """Wrapped tool function with timing."""
        start = time.perf_counter()
        success = True
        result_str = ""
        
        try:
            # Handle both sync and async functions
            if is_async:
                result = await func(**kwargs)
            else:
                result = func(**kwargs)
            
            # Convert result to string for LLM
            if hasattr(result, 'to_llm_response'):
                result_str = result.to_llm_response()
            elif hasattr(result, 'model_dump_json'):
                result_str = result.model_dump_json(indent=2)
            else:
                result_str = str(result)
                
        except Exception as e:
            success = False
            result_str = f"Error executing {definition.name}: {e}"
            logger.exception(f"Tool {definition.name} failed: {e}")
            
        finally:
            # Report timing
            if timing_callback:
                duration_ms = int((time.perf_counter() - start) * 1000)
                timing_callback(definition.name, duration_ms, success)
        
        return result_str
    
    # Set metadata for GlueLLM schema generation
    wrapper.__doc__ = _build_docstring(definition)
    wrapper.__name__ = definition.name
    
    # Add type hints from definition parameters
    # GlueLLM uses these to generate the schema
    _add_type_hints(wrapper, definition)
    
    return wrapper


def _build_docstring(definition: ToolDefinition) -> str:
    """
    Build a comprehensive docstring for GlueLLM schema generation.
    
    GlueLLM parses docstrings to extract parameter descriptions,
    so we format them in Google-style docstring format.
    """
    lines = [definition.description, ""]
    
    if definition.parameters:
        lines.append("Args:")
        for param in definition.parameters:
            required = "(required)" if param.required else "(optional)"
            default = f", default={param.default}" if param.default is not None else ""
            lines.append(f"    {param.name}: {param.description} {required}{default}")
        lines.append("")
    
    lines.append("Returns:")
    lines.append("    str: Result of the tool execution")
    
    return "\n".join(lines)


def _add_type_hints(wrapper: Callable, definition: ToolDefinition) -> None:
    """
    Add type annotations to the wrapper function.
    
    GlueLLM may use these for schema generation.
    Maps our parameter types to Python types.
    """
    type_map = {
        "string": str,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    
    annotations = {"return": str}
    
    for param in definition.parameters:
        param_type = type_map.get(param.type, str)
        if not param.required:
            # Optional parameters
            annotations[param.name] = param_type | None
        else:
            annotations[param.name] = param_type
    
    wrapper.__annotations__ = annotations
