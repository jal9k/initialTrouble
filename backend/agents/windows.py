"""Windows-specific diagnostic agent.

This agent specializes in troubleshooting Windows systems using
PowerShell commands and Windows-specific tools.
"""

from typing import TYPE_CHECKING, Any

from .base import AgentResponse, BaseAgent
from ..diagnostics.platform import Platform
from ..llm.base import ChatMessage

if TYPE_CHECKING:
    from ..tools.registry import ToolRegistry


class WindowsAgent(BaseAgent):
    """Windows diagnostic specialist agent.
    
    This agent handles troubleshooting for computers running Microsoft Windows.
    It uses PowerShell commands and Windows-specific tools like Device Manager,
    Event Viewer, and system repair utilities.
    """

    name = "windows"
    description = "Windows troubleshooting specialist"
    supported_platforms = [Platform.WINDOWS]

    # Tools available to Windows agent (includes Windows-specific tools)
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
        # Windows-specific tools
        "fix_dell_audio",
        "repair_office365",
        "run_dism_sfc",
        "review_system_logs",
    ]

    def __init__(
        self,
        tool_registry: "ToolRegistry | None" = None,
        platform: Platform | None = None,
    ):
        """Initialize Windows Agent.
        
        Args:
            tool_registry: Registry containing available tools
            platform: Override platform detection (useful for testing)
        """
        super().__init__(tool_registry, platform or Platform.WINDOWS)

    def get_system_prompt(self) -> str:
        """Get the system prompt for the Windows Agent.
        
        Returns:
            System prompt for Windows diagnostics
        """
        from ..prompts import AgentType, load_prompt
        
        try:
            return load_prompt(AgentType.WINDOWS)
        except FileNotFoundError:
            return self._get_fallback_prompt()

    def _get_fallback_prompt(self) -> str:
        """Get fallback prompt if prompt file is not available."""
        return """# Windows Diagnostic Agent

You are a Windows troubleshooting specialist. You diagnose and fix problems on computers running Microsoft Windows.

## Available Tools

### Network Diagnostics
- check_adapter_status: Check network adapter status
- get_ip_config: Get IP configuration
- ping_gateway: Test router connectivity
- ping_dns: Test internet connectivity
- test_dns_resolution: Test DNS resolution

### System Maintenance
- cleanup_temp_files: Remove temporary files
- kill_process: Terminate problematic processes

### Windows-Specific Tools
- fix_dell_audio: Remove and reinstall Dell audio drivers
- repair_office365: Run Microsoft 365 repair
- run_dism_sfc: Run DISM and SFC system file repair
- review_system_logs: Analyze Event Viewer and crash dumps

## Diagnostic Order

1. check_adapter_status (always first)
2. get_ip_config (if adapter is connected)
3. ping_gateway (if valid IP exists)
4. ping_dns (if gateway is reachable)
5. test_dns_resolution (if DNS servers respond)

Use PowerShell commands and reference Windows Settings appropriately.
"""

    def get_available_tools(self) -> list:
        """Get tools available to the Windows agent.
        
        Returns filtered list of tools appropriate for Windows,
        including Windows-specific advanced tools.
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
        """Process a user message with Windows-specific handling.
        
        Args:
            message: User's input message
            conversation_history: Previous messages in the conversation
            
        Returns:
            Dict containing response and metadata
        """
        return {
            "agent": self.name,
            "platform": self._platform.value,
            "system_prompt": self.get_system_prompt(),
            "available_tools": [t.name for t in self.get_available_tools()],
            "message": message,
            "conversation_history": conversation_history,
        }

    def get_windows_specific_advice(self, issue_type: str) -> list[str]:
        """Get Windows-specific troubleshooting advice.
        
        Args:
            issue_type: Type of issue (network, performance, etc.)
            
        Returns:
            List of Windows-specific suggestions
        """
        advice = {
            "network": [
                "Open Settings > Network & Internet to check connection status",
                "Run 'ipconfig /release' then 'ipconfig /renew'",
                "Flush DNS: 'ipconfig /flushdns'",
                "Reset network stack: 'netsh winsock reset' (requires reboot)",
                "Check Device Manager for adapter issues",
            ],
            "performance": [
                "Open Task Manager (Ctrl+Shift+Esc) to check CPU/memory",
                "Run Disk Cleanup to free space",
                "Disable unnecessary startup programs",
                "Check for Windows updates",
                "Run 'sfc /scannow' to check system files",
            ],
            "storage": [
                "Use Settings > Storage for space overview",
                "Run Disk Cleanup with system files option",
                "Empty Recycle Bin",
                "Uninstall unused programs via Settings > Apps",
                "Use Storage Sense for automatic cleanup",
            ],
            "application": [
                "Check for app updates",
                "Run app repair via Settings > Apps > [App] > Modify",
                "For Office: Use 'repair_office365' tool",
                "Check Event Viewer for error details",
                "Try running as Administrator",
            ],
            "system": [
                "Run 'run_dism_sfc' to repair system files",
                "Check 'review_system_logs' for errors",
                "Boot into Safe Mode for troubleshooting",
                "Check Windows Update for pending updates",
                "Use System Restore if issues started recently",
            ],
            "audio": [
                "Check volume mixer (right-click speaker icon)",
                "Run audio troubleshooter",
                "For Dell: Use 'fix_dell_audio' tool",
                "Update audio drivers via Device Manager",
                "Set correct default audio device",
            ],
        }
        return advice.get(issue_type.lower(), [])

    def detect_dell_system(self) -> bool:
        """Check if this is a Dell system.
        
        Returns:
            True if running on Dell hardware
        """
        # This would be implemented to check BIOS/system info
        # For now, return False as a placeholder
        return False

