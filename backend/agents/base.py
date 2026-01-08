"""Base agent class for OS-specific diagnostic agents.

This module provides the foundation for the hierarchical agent architecture,
where a Manager Agent routes requests to OS-specific specialists.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from ..diagnostics.platform import Platform, get_platform
from ..llm.base import ChatMessage, ChatResponse

if TYPE_CHECKING:
    from ..tools.registry import ToolRegistry
    from ..tools.schemas import ToolDefinition


class BaseAgent(ABC):
    """Abstract base class for all diagnostic agents.
    
    Each agent specializes in a particular operating system or role
    (e.g., Manager, macOS, Windows, Linux) and has access to a
    filtered set of tools appropriate for its domain.
    """

    # Override in subclass
    name: str = "base_agent"
    description: str = "Base diagnostic agent"
    supported_platforms: list[Platform] = [Platform.MACOS, Platform.WINDOWS, Platform.LINUX]

    def __init__(
        self,
        tool_registry: "ToolRegistry | None" = None,
        platform: Platform | None = None,
    ):
        """Initialize agent with tool registry and platform context.
        
        Args:
            tool_registry: Registry containing available tools
            platform: Override platform detection (useful for testing)
        """
        self._tool_registry = tool_registry
        self._platform = platform or get_platform()

    @property
    def platform(self) -> Platform:
        """Get the current platform."""
        return self._platform

    @property
    def tool_registry(self) -> "ToolRegistry | None":
        """Get the tool registry."""
        return self._tool_registry

    def set_tool_registry(self, registry: "ToolRegistry") -> None:
        """Set the tool registry for this agent."""
        self._tool_registry = registry

    def get_available_tools(self) -> list["ToolDefinition"]:
        """Get tools available for this agent's domain.
        
        Subclasses can override this to filter tools based on
        platform or agent specialization.
        
        Returns:
            List of tool definitions available to this agent
        """
        if self._tool_registry is None:
            return []
        return self._tool_registry.get_all_definitions()

    def is_platform_supported(self) -> bool:
        """Check if current platform is supported by this agent."""
        return self._platform in self.supported_platforms

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent.
        
        Returns:
            System prompt string tailored to this agent's role
        """
        pass

    @abstractmethod
    async def process_message(
        self,
        message: str,
        conversation_history: list[ChatMessage] | None = None,
    ) -> dict[str, Any]:
        """Process a user message and generate a response.
        
        Args:
            message: User's input message
            conversation_history: Previous messages in the conversation
            
        Returns:
            Dict containing response and any metadata (tool calls, routing, etc.)
        """
        pass


class IssueCategory:
    """Categories for issue triage by the Manager Agent."""
    
    NETWORK = "NETWORK"
    PERFORMANCE = "PERFORMANCE"
    APPLICATION = "APPLICATION"
    SYSTEM = "SYSTEM"
    STORAGE = "STORAGE"
    UNKNOWN = "UNKNOWN"

    # Keywords that indicate each category
    KEYWORDS = {
        NETWORK: [
            "internet", "wifi", "wi-fi", "ethernet", "connection", "dns",
            "ip", "network", "offline", "online", "vpn", "router", "modem",
            "lan", "wan", "ping", "bandwidth", "speed", "download", "upload",
        ],
        PERFORMANCE: [
            "slow", "freeze", "freezing", "hang", "hanging", "crash",
            "crashing", "memory", "cpu", "fan", "hot", "overheating",
            "unresponsive", "lag", "lagging", "performance", "speed",
        ],
        APPLICATION: [
            "app", "application", "program", "software", "office", "word",
            "excel", "outlook", "browser", "chrome", "firefox", "teams",
            "zoom", "install", "uninstall", "update", "open", "launch",
            "won't start", "doesn't work", "error message",
        ],
        SYSTEM: [
            "boot", "startup", "shutdown", "restart", "reboot", "driver",
            "update", "repair", "blue screen", "bsod", "kernel", "system",
            "windows update", "macos update", "login", "password", "account",
        ],
        STORAGE: [
            "disk", "space", "storage", "files", "delete", "cleanup",
            "full", "drive", "ssd", "hdd", "external", "usb", "backup",
            "restore", "partition", "format",
        ],
    }

    @classmethod
    def categorize(cls, message: str) -> str:
        """Categorize a user message based on keywords.
        
        Args:
            message: User's input message
            
        Returns:
            Issue category string
        """
        message_lower = message.lower()
        
        # Count keyword matches for each category
        scores = {}
        for category, keywords in cls.KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            if score > 0:
                scores[category] = score
        
        if not scores:
            return cls.UNKNOWN
        
        # Return category with highest score
        return max(scores, key=scores.get)


class AgentResponse:
    """Structured response from an agent."""
    
    def __init__(
        self,
        content: str,
        agent_name: str,
        tool_calls: list[dict[str, Any]] | None = None,
        route_to: str | None = None,
        issue_category: str | None = None,
        platform: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Initialize agent response.
        
        Args:
            content: Response text content
            agent_name: Name of the agent that generated this response
            tool_calls: List of tool calls made during processing
            route_to: Agent to route to (for Manager Agent handoffs)
            issue_category: Categorized issue type
            platform: Detected platform
            metadata: Additional metadata
        """
        self.content = content
        self.agent_name = agent_name
        self.tool_calls = tool_calls or []
        self.route_to = route_to
        self.issue_category = issue_category
        self.platform = platform
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "content": self.content,
            "agent_name": self.agent_name,
            "tool_calls": self.tool_calls,
            "route_to": self.route_to,
            "issue_category": self.issue_category,
            "platform": self.platform,
            "metadata": self.metadata,
        }

