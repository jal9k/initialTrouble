"""FastAPI router for tools API endpoints."""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .registry import ToolRegistry
from .schemas import ToolCall, ToolDefinition, ToolParameter


# Request/Response Models

class ToolResponse(BaseModel):
    """Response for a single tool."""
    
    name: str
    displayName: str
    description: str
    category: str
    parameters: list[dict[str, Any]]
    osiLayer: int


class ToolListResponse(BaseModel):
    """Response for tool list."""
    
    tools: list[ToolResponse]


class ExecuteToolRequest(BaseModel):
    """Request body for executing a tool."""
    
    # Parameters are passed directly in the body
    pass


class ExecuteToolResponse(BaseModel):
    """Response from tool execution."""
    
    toolCallId: str = Field(description="Unique ID for this tool call")
    name: str = Field(description="Name of the tool")
    result: Any = Field(description="Tool execution result")
    error: str | None = Field(default=None, description="Error message if failed")
    duration: int | None = Field(default=None, description="Execution time in ms")


# OSI layer mapping based on tool category
CATEGORY_OSI_MAP = {
    "connectivity": 1,
    "ip_config": 2,
    "dns": 4,
    "wifi": 1,
    "system": 7,
}


def tool_definition_to_response(tool_def: ToolDefinition) -> ToolResponse:
    """Convert a ToolDefinition to a ToolResponse."""
    # Infer category from tool name
    category = "system"
    name_lower = tool_def.name.lower()
    if "dns" in name_lower:
        category = "dns"
    elif "wifi" in name_lower or "adapter" in name_lower:
        category = "wifi"
    elif "ip" in name_lower or "config" in name_lower:
        category = "ip_config"
    elif "ping" in name_lower or "gateway" in name_lower:
        category = "connectivity"
    
    # Convert parameters
    params = []
    for param in tool_def.parameters:
        params.append({
            "name": param.name,
            "type": param.type,
            "description": param.description,
            "required": param.required,
            "default": param.default,
        })
    
    # Generate display name from tool name
    display_name = tool_def.name.replace("_", " ").title()
    
    return ToolResponse(
        name=tool_def.name,
        displayName=display_name,
        description=tool_def.description,
        category=category,
        parameters=params,
        osiLayer=CATEGORY_OSI_MAP.get(category, 7),
    )


def create_tools_router(registry: ToolRegistry) -> APIRouter:
    """Create the tools API router.
    
    Args:
        registry: The tool registry instance to use
        
    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/api/tools", tags=["tools"])

    @router.get("", response_model=list[ToolResponse])
    async def list_tools() -> list[ToolResponse]:
        """List all available diagnostic tools."""
        definitions = registry.get_all_definitions()
        return [tool_definition_to_response(d) for d in definitions]

    @router.post("/{tool_name}/execute", response_model=ExecuteToolResponse)
    async def execute_tool(
        tool_name: str,
        params: dict[str, Any] | None = None,
    ) -> ExecuteToolResponse:
        """Execute a specific tool with the given parameters."""
        import time
        
        # Check if tool exists
        tool_def = registry.get_definition(tool_name)
        if tool_def is None:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found"
            )
        
        # Create a tool call
        tool_call = ToolCall(
            id=str(uuid.uuid4()),
            name=tool_name,
            arguments=params or {},
        )
        
        # Execute the tool
        start_time = time.perf_counter()
        result = await registry.execute(tool_call)
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Parse result content if it looks like JSON
        parsed_result: Any = result.content
        if result.content.startswith("{") or result.content.startswith("["):
            try:
                import json
                parsed_result = json.loads(result.content)
            except json.JSONDecodeError:
                pass
        
        return ExecuteToolResponse(
            toolCallId=result.tool_call_id,
            name=result.name,
            result=parsed_result if result.success else None,
            error=result.content if not result.success else None,
            duration=duration_ms,
        )

    return router


