"""Base diagnostic class and result schema."""

from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, Field

from .platform import CommandExecutor, Platform, get_executor, get_platform


class DiagnosticResult(BaseModel):
    """Standardized result from any diagnostic function."""

    success: bool = Field(description="Whether the diagnostic completed successfully")
    function_name: str = Field(description="Name of the diagnostic function")
    platform: Literal["macos", "windows", "linux", "unknown"] = Field(
        description="Platform where diagnostic was run"
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Function-specific result data",
    )
    raw_output: str = Field(
        default="",
        description="Raw command output for debugging",
    )
    error: str | None = Field(
        default=None,
        description="Error message if diagnostic failed",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Suggested next steps based on results",
    )

    def to_llm_response(self) -> str:
        """Format result for LLM consumption."""
        lines = [f"## {self.function_name} Results"]

        if self.success:
            lines.append("**Status**: Success")
        else:
            lines.append(f"**Status**: Failed - {self.error}")

        lines.append(f"**Platform**: {self.platform}")

        if self.data:
            lines.append("\n### Data")
            for key, value in self.data.items():
                lines.append(f"- **{key}**: {value}")

        if self.suggestions:
            lines.append("\n### Suggestions")
            for suggestion in self.suggestions:
                lines.append(f"- {suggestion}")

        return "\n".join(lines)


class BaseDiagnostic(ABC):
    """Base class for all diagnostic functions."""

    # Override in subclass
    name: str = "base_diagnostic"
    description: str = "Base diagnostic function"
    osi_layer: str = "Unknown"

    def __init__(self, executor: CommandExecutor | None = None):
        """Initialize diagnostic with command executor."""
        self.executor = executor or get_executor()
        self.platform = get_platform()

    @abstractmethod
    async def run(self, **kwargs: Any) -> DiagnosticResult:
        """
        Execute the diagnostic.

        Args:
            **kwargs: Function-specific parameters

        Returns:
            DiagnosticResult with findings
        """
        pass

    def _create_result(
        self,
        success: bool,
        data: dict[str, Any] | None = None,
        raw_output: str = "",
        error: str | None = None,
        suggestions: list[str] | None = None,
    ) -> DiagnosticResult:
        """Helper to create a standardized result."""
        return DiagnosticResult(
            success=success,
            function_name=self.name,
            platform=self.platform.value,
            data=data or {},
            raw_output=raw_output,
            error=error,
            suggestions=suggestions or [],
        )

    def _success(
        self,
        data: dict[str, Any],
        raw_output: str = "",
        suggestions: list[str] | None = None,
    ) -> DiagnosticResult:
        """Create a successful result."""
        return self._create_result(
            success=True,
            data=data,
            raw_output=raw_output,
            suggestions=suggestions,
        )

    def _failure(
        self,
        error: str,
        data: dict[str, Any] | None = None,
        raw_output: str = "",
        suggestions: list[str] | None = None,
    ) -> DiagnosticResult:
        """Create a failed result."""
        return self._create_result(
            success=False,
            data=data,
            raw_output=raw_output,
            error=error,
            suggestions=suggestions,
        )

