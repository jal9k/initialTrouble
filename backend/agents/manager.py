"""Manager Agent for triage and OS-specific routing.

The Manager Agent is the entry point for all user interactions. It:
1. Detects the operating system
2. Categorizes the issue type
3. Routes to the appropriate OS-specific agent
"""

from typing import TYPE_CHECKING, Any

from .base import AgentResponse, BaseAgent, IssueCategory
from ..diagnostics.platform import Platform, get_platform
from ..llm.base import ChatMessage

if TYPE_CHECKING:
    from ..tools.registry import ToolRegistry


class ManagerAgent(BaseAgent):
    """Manager Agent for triage and routing.
    
    The Manager Agent serves as the first point of contact for user queries.
    It performs initial triage, detects the operating system, and delegates
    to the appropriate OS-specific agent for specialized diagnostics.
    """

    name = "manager"
    description = "Triage coordinator for system troubleshooting"
    supported_platforms = [Platform.MACOS, Platform.WINDOWS, Platform.LINUX]

    def __init__(
        self,
        tool_registry: "ToolRegistry | None" = None,
        platform: Platform | None = None,
    ):
        """Initialize Manager Agent.
        
        Args:
            tool_registry: Registry containing available tools
            platform: Override platform detection (useful for testing)
        """
        super().__init__(tool_registry, platform)
        self._os_agents: dict[Platform, BaseAgent] = {}

    def get_system_prompt(self) -> str:
        """Get the system prompt for the Manager Agent.
        
        Returns:
            System prompt for triage and routing
        """
        from ..prompts import AgentType, load_prompt
        
        try:
            return load_prompt(AgentType.MANAGER)
        except FileNotFoundError:
            # Fallback prompt if file not found
            return self._get_fallback_prompt()

    def _get_fallback_prompt(self) -> str:
        """Get fallback prompt if prompt file is not available."""
        detected_os = self._platform.value
        return f"""# Manager Agent

You are a triage coordinator for system troubleshooting. Your job is to understand the user's problem and route it to the correct specialist agent.

## Operating System Detection

The current operating system is: {detected_os}

## Issue Categories

| Category | Keywords | Route To |
|----------|----------|----------|
| NETWORK | internet, wifi, ethernet, connection, DNS, IP | {detected_os}_agent |
| PERFORMANCE | slow, freeze, hang, crash, memory, CPU | {detected_os}_agent |
| APPLICATION | app, program, software, Office, browser | {detected_os}_agent |
| SYSTEM | boot, startup, driver, update, repair | {detected_os}_agent |
| STORAGE | disk, space, files, delete, cleanup | {detected_os}_agent |

## Rules

1. Always confirm the operating system
2. Categorize the issue before routing
3. Provide a brief initial assessment
4. Route to the appropriate OS-specific agent
"""

    def _get_os_agent(self, platform: Platform) -> BaseAgent:
        """Get or create the OS-specific agent for a platform.
        
        Args:
            platform: Target platform
            
        Returns:
            OS-specific agent instance
        """
        if platform not in self._os_agents:
            from . import get_agent
            
            agent_type = platform.value  # "macos", "windows", "linux"
            self._os_agents[platform] = get_agent(
                agent_type,
                tool_registry=self._tool_registry,
                platform=platform,
            )
        
        return self._os_agents[platform]

    def detect_os(self) -> Platform:
        """Detect the current operating system.
        
        Returns:
            Detected Platform enum value
        """
        return self._platform

    def categorize_issue(self, message: str) -> str:
        """Categorize the user's issue based on message content.
        
        Args:
            message: User's input message
            
        Returns:
            Issue category string
        """
        return IssueCategory.categorize(message)

    def get_routing_target(self, platform: Platform, category: str) -> str:
        """Determine which agent to route to.
        
        Args:
            platform: Target platform
            category: Issue category
            
        Returns:
            Agent name to route to
        """
        # For now, route to the OS-specific agent
        # Future: could have category-specific sub-agents
        return f"{platform.value}_agent"

    async def process_message(
        self,
        message: str,
        conversation_history: list[ChatMessage] | None = None,
    ) -> dict[str, Any]:
        """Process a user message and route to appropriate agent.
        
        The Manager Agent performs triage and then delegates to the
        appropriate OS-specific agent for actual diagnostics.
        
        Args:
            message: User's input message
            conversation_history: Previous messages in the conversation
            
        Returns:
            Dict containing response, routing info, and metadata
        """
        # Step 1: Detect OS
        detected_os = self.detect_os()
        
        # Step 2: Categorize the issue
        issue_category = self.categorize_issue(message)
        
        # Step 3: Determine routing target
        route_to = self.get_routing_target(detected_os, issue_category)
        
        # Step 4: Get the OS-specific agent
        os_agent = self._get_os_agent(detected_os)
        
        # Step 5: Delegate to OS-specific agent
        result = await os_agent.process_message(message, conversation_history)
        
        # Add routing metadata
        result["routing"] = {
            "manager_agent": self.name,
            "detected_os": detected_os.value,
            "issue_category": issue_category,
            "routed_to": route_to,
        }
        
        return result

    def create_triage_response(
        self,
        message: str,
        detected_os: Platform,
        issue_category: str,
        route_to: str,
    ) -> AgentResponse:
        """Create a triage response without delegating yet.
        
        Useful for showing the user what the Manager determined
        before handing off to a specialist.
        
        Args:
            message: Original user message
            detected_os: Detected platform
            issue_category: Determined issue category
            route_to: Target agent for routing
            
        Returns:
            AgentResponse with triage information
        """
        content = f"""**Operating System**: {detected_os.value}
**Issue Category**: {issue_category}
**Routing To**: {route_to}
**Initial Assessment**: Analyzing your {issue_category.lower()} issue on {detected_os.value}..."""

        return AgentResponse(
            content=content,
            agent_name=self.name,
            route_to=route_to,
            issue_category=issue_category,
            platform=detected_os.value,
        )

