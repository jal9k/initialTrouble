"""Agent module for hierarchical diagnostic routing.

This module provides the multi-agent architecture where:
- Manager Agent handles initial triage and OS detection
- OS-specific agents (macOS, Windows, Linux) handle specialized diagnostics

Usage:
    from backend.agents import get_agent, ManagerAgent
    
    # Get manager agent for routing
    manager = get_agent("manager")
    
    # Or get OS-specific agent directly
    macos_agent = get_agent("macos")
"""

from .base import AgentResponse, BaseAgent, IssueCategory

__all__ = [
    "BaseAgent",
    "AgentResponse",
    "IssueCategory",
    "get_agent",
    "get_manager_agent",
    "get_os_agent",
]


def get_agent(agent_type: str, **kwargs) -> BaseAgent:
    """Factory function to get an agent by type.
    
    Args:
        agent_type: Type of agent ("manager", "macos", "windows", "linux")
        **kwargs: Additional arguments passed to agent constructor
        
    Returns:
        Initialized agent instance
        
    Raises:
        ValueError: If agent_type is not recognized
    """
    agent_type = agent_type.lower()
    
    if agent_type == "manager":
        from .manager import ManagerAgent
        return ManagerAgent(**kwargs)
    elif agent_type == "macos":
        from .macos import MacOSAgent
        return MacOSAgent(**kwargs)
    elif agent_type == "windows":
        from .windows import WindowsAgent
        return WindowsAgent(**kwargs)
    elif agent_type == "linux":
        from .linux import LinuxAgent
        return LinuxAgent(**kwargs)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


def get_manager_agent(**kwargs) -> "BaseAgent":
    """Get the Manager Agent for triage and routing.
    
    Returns:
        ManagerAgent instance
    """
    return get_agent("manager", **kwargs)


def get_os_agent(**kwargs) -> "BaseAgent":
    """Get the appropriate OS-specific agent for the current platform.
    
    Returns:
        OS-specific agent instance (MacOSAgent, WindowsAgent, or LinuxAgent)
    """
    from ..diagnostics.platform import Platform, get_platform
    
    platform = get_platform()
    
    if platform == Platform.MACOS:
        return get_agent("macos", **kwargs)
    elif platform == Platform.WINDOWS:
        return get_agent("windows", **kwargs)
    elif platform == Platform.LINUX:
        return get_agent("linux", **kwargs)
    else:
        # Default to Linux for unknown platforms
        return get_agent("linux", **kwargs)

