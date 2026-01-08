"""macOS-specific diagnostic agent.

This agent specializes in troubleshooting macOS systems using
macOS-specific commands and tools.
"""

from typing import TYPE_CHECKING, Any

from .base import AgentResponse, BaseAgent
from ..diagnostics.platform import Platform
from ..llm.base import ChatMessage

if TYPE_CHECKING:
    from ..tools.registry import ToolRegistry


class MacOSAgent(BaseAgent):
    """macOS diagnostic specialist agent.
    
    This agent handles troubleshooting for Apple computers running macOS.
    It uses macOS-specific commands like ifconfig, networksetup, and
    system_profiler.
    """

    name = "macos"
    description = "macOS troubleshooting specialist"
    supported_platforms = [Platform.MACOS]

    # Tools available to macOS agent
    AVAILABLE_TOOLS = [
        # Network diagnostics
        "check_adapter_status",
        "get_ip_config",
        "ping_gateway",
        "ping_dns",
        "test_dns_resolution",
        "test_vpn_connectivity",
        # System maintenance
        "cleanup_temp_files",
        "kill_process",
        # WiFi control
        "enable_wifi",
    ]

    def __init__(
        self,
        tool_registry: "ToolRegistry | None" = None,
        platform: Platform | None = None,
    ):
        """Initialize macOS Agent.
        
        Args:
            tool_registry: Registry containing available tools
            platform: Override platform detection (useful for testing)
        """
        super().__init__(tool_registry, platform or Platform.MACOS)

    def get_system_prompt(self) -> str:
        """Get the system prompt for the macOS Agent.
        
        Returns:
            System prompt for macOS diagnostics
        """
        from ..prompts import AgentType, load_prompt
        
        try:
            return load_prompt(AgentType.MACOS)
        except FileNotFoundError:
            return self._get_fallback_prompt()

    def _get_fallback_prompt(self) -> str:
        """Get fallback prompt if prompt file is not available."""
        return """# macOS Diagnostic Agent

You are a macOS troubleshooting specialist. You diagnose and fix problems on Apple computers running macOS.

## Available Tools

- check_adapter_status: Check network interface status
- get_ip_config: Get IP configuration
- ping_gateway: Test router connectivity
- ping_dns: Test internet connectivity
- test_dns_resolution: Test DNS resolution
- cleanup_temp_files: Remove temporary files
- kill_process: Terminate problematic processes

## Diagnostic Order

1. check_adapter_status (always first)
2. get_ip_config (if adapter is connected)
3. ping_gateway (if valid IP exists)
4. ping_dns (if gateway is reachable)
5. test_dns_resolution (if DNS servers respond)

Use macOS-specific commands and reference System Settings appropriately.
"""

    def get_available_tools(self) -> list:
        """Get tools available to the macOS agent.
        
        Returns filtered list of tools appropriate for macOS.
        """
        if self._tool_registry is None:
            return []
        
        all_tools = self._tool_registry.get_all_definitions()
        return [t for t in all_tools if t.name in self.AVAILABLE_TOOLS]

    async def process_message(
        self,
        message: str,
        conversation_history: list[ChatMessage] | None = None,
    ) -> dict[str, Any]:
        """Process a user message with macOS-specific handling.
        
        Args:
            message: User's input message
            conversation_history: Previous messages in the conversation
            
        Returns:
            Dict containing response and metadata
        """
        # For now, return a structured response indicating the agent
        # The actual LLM integration happens at a higher level
        return {
            "agent": self.name,
            "platform": self._platform.value,
            "system_prompt": self.get_system_prompt(),
            "available_tools": [t.name for t in self.get_available_tools()],
            "message": message,
            "conversation_history": conversation_history,
        }

    def get_macos_specific_advice(self, issue_type: str) -> list[str]:
        """Get macOS-specific troubleshooting advice.
        
        Args:
            issue_type: Type of issue (network, performance, etc.)
            
        Returns:
            List of macOS-specific suggestions
        """
        advice = {
            "network": [
                "Open System Settings > Network to check connection status",
                "Try toggling WiFi off and on via menu bar",
                "Run 'networksetup -setairportpower en0 off && networksetup -setairportpower en0 on'",
                "Flush DNS cache: 'sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder'",
            ],
            "performance": [
                "Check Activity Monitor for high CPU/memory processes",
                "Clear user caches in ~/Library/Caches",
                "Restart in Safe Mode to diagnose startup items",
                "Reset SMC and NVRAM if hardware-related",
            ],
            "storage": [
                "Use About This Mac > Storage for space overview",
                "Empty Trash and clear Downloads folder",
                "Remove large files from ~/Library/Caches",
                "Consider using Optimized Storage features",
            ],
            "application": [
                "Check for app updates in App Store",
                "Try deleting app preferences in ~/Library/Preferences",
                "Reinstall the application",
                "Check Console.app for crash logs",
            ],
        }
        return advice.get(issue_type.lower(), [])

