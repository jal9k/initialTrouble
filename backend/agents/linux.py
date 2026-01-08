"""Linux-specific diagnostic agent.

This agent specializes in troubleshooting Linux systems using
standard Linux commands and tools.
"""

from typing import TYPE_CHECKING, Any

from .base import AgentResponse, BaseAgent
from ..diagnostics.platform import Platform
from ..llm.base import ChatMessage

if TYPE_CHECKING:
    from ..tools.registry import ToolRegistry


class LinuxAgent(BaseAgent):
    """Linux diagnostic specialist agent.
    
    This agent handles troubleshooting for computers running Linux distributions.
    It uses standard Linux commands like ip, nmcli, systemctl, and journalctl.
    """

    name = "linux"
    description = "Linux troubleshooting specialist"
    supported_platforms = [Platform.LINUX]

    # Tools available to Linux agent
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
    ]

    def __init__(
        self,
        tool_registry: "ToolRegistry | None" = None,
        platform: Platform | None = None,
    ):
        """Initialize Linux Agent.
        
        Args:
            tool_registry: Registry containing available tools
            platform: Override platform detection (useful for testing)
        """
        super().__init__(tool_registry, platform or Platform.LINUX)

    def get_system_prompt(self) -> str:
        """Get the system prompt for the Linux Agent.
        
        Returns:
            System prompt for Linux diagnostics
        """
        from ..prompts import AgentType, load_prompt
        
        try:
            return load_prompt(AgentType.LINUX)
        except FileNotFoundError:
            return self._get_fallback_prompt()

    def _get_fallback_prompt(self) -> str:
        """Get fallback prompt if prompt file is not available."""
        return """# Linux Diagnostic Agent

You are a Linux troubleshooting specialist. You diagnose and fix problems on computers running Linux distributions.

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

Use Linux commands (ip, nmcli, systemctl) and be aware of distribution differences.
"""

    def get_available_tools(self) -> list:
        """Get tools available to the Linux agent.
        
        Returns filtered list of tools appropriate for Linux.
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
        """Process a user message with Linux-specific handling.
        
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

    def get_linux_specific_advice(self, issue_type: str) -> list[str]:
        """Get Linux-specific troubleshooting advice.
        
        Args:
            issue_type: Type of issue (network, performance, etc.)
            
        Returns:
            List of Linux-specific suggestions
        """
        advice = {
            "network": [
                "Check interface status: 'ip link show'",
                "Restart NetworkManager: 'sudo systemctl restart NetworkManager'",
                "View connection info: 'nmcli connection show'",
                "Flush DNS: 'sudo systemd-resolve --flush-caches'",
                "Check logs: 'journalctl -u NetworkManager'",
            ],
            "performance": [
                "Check processes: 'top' or 'htop'",
                "View memory usage: 'free -h'",
                "Check disk I/O: 'iotop'",
                "View system load: 'uptime'",
                "Check for OOM events: 'dmesg | grep -i oom'",
            ],
            "storage": [
                "Check disk usage: 'df -h'",
                "Find large files: 'du -sh /* 2>/dev/null | sort -h'",
                "Clear package cache (apt): 'sudo apt clean'",
                "Clear user cache: 'rm -rf ~/.cache/*'",
                "Check for old kernels: 'dpkg -l linux-image-*'",
            ],
            "application": [
                "Check if running: 'pgrep -a appname'",
                "View app logs: 'journalctl -u servicename'",
                "Reinstall package: 'sudo apt install --reinstall package'",
                "Check dependencies: 'ldd /path/to/binary'",
                "Run with debug: 'appname --verbose'",
            ],
            "system": [
                "View system logs: 'journalctl -xe'",
                "Check boot issues: 'journalctl -b'",
                "View failed services: 'systemctl --failed'",
                "Check disk health: 'sudo smartctl -a /dev/sda'",
                "Run filesystem check: 'sudo fsck -n /dev/sda1'",
            ],
        }
        return advice.get(issue_type.lower(), [])

    def detect_distribution(self) -> dict[str, str]:
        """Detect the Linux distribution.
        
        Returns:
            Dict with distribution info (name, version, etc.)
        """
        # This would read /etc/os-release
        # For now, return a placeholder
        return {
            "id": "unknown",
            "name": "Linux",
            "version": "unknown",
        }

    def get_package_manager(self) -> str:
        """Get the package manager for this distribution.
        
        Returns:
            Package manager command (apt, dnf, pacman, etc.)
        """
        distro = self.detect_distribution()
        distro_id = distro.get("id", "").lower()
        
        package_managers = {
            "ubuntu": "apt",
            "debian": "apt",
            "fedora": "dnf",
            "centos": "dnf",
            "rhel": "dnf",
            "arch": "pacman",
            "manjaro": "pacman",
            "opensuse": "zypper",
            "suse": "zypper",
        }
        
        return package_managers.get(distro_id, "apt")

