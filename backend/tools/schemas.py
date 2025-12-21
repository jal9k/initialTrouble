"""Pydantic schemas for LLM tool definitions."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Definition of a tool parameter."""

    name: str = Field(description="Parameter name")
    type: Literal["string", "number", "boolean", "array", "object"] = Field(
        description="Parameter type"
    )
    description: str = Field(description="Parameter description")
    required: bool = Field(default=True, description="Whether parameter is required")
    default: Any = Field(default=None, description="Default value if not required")
    enum: list[str] | None = Field(default=None, description="Allowed values for string type")


class ToolDefinition(BaseModel):
    """Definition of a tool for LLM function calling."""

    name: str = Field(description="Tool name (function name)")
    description: str = Field(description="Tool description for LLM")
    parameters: list[ToolParameter] = Field(
        default_factory=list,
        description="List of parameters",
    )

    def to_openai_schema(self) -> dict[str, Any]:
        """Convert to OpenAI function calling schema."""
        properties = {}
        required = []

        for param in self.parameters:
            prop: dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_ollama_schema(self) -> dict[str, Any]:
        """Convert to Ollama tool schema (same as OpenAI)."""
        return self.to_openai_schema()


class ToolCall(BaseModel):
    """Represents a tool call from the LLM."""

    id: str = Field(description="Unique ID for this tool call")
    name: str = Field(description="Name of the tool to call")
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments to pass to the tool",
    )


class ToolResult(BaseModel):
    """Result of executing a tool."""

    tool_call_id: str = Field(description="ID of the tool call this responds to")
    name: str = Field(description="Name of the tool that was called")
    content: str = Field(description="Result content as string")
    success: bool = Field(default=True, description="Whether tool execution succeeded")

