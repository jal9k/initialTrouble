"""Prompt loading and management for different agent types."""

from enum import Enum
from pathlib import Path
from functools import lru_cache


class AgentType(Enum):
    """Available agent types with specialized prompts."""
    
    DEFAULT = "default"      # General-purpose diagnostician
    TRIAGE = "triage"        # Quick issue categorization
    DIAGNOSTIC = "diagnostic"  # Systematic OSI-layer troubleshooting
    REMEDIATION = "remediation"  # Fix suggestions
    QUICK_CHECK = "quick_check"  # Fast health check


# Prompt directory relative to this file
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


@lru_cache(maxsize=10)
def load_prompt(agent_type: AgentType | str) -> str:
    """
    Load a system prompt for the specified agent type.
    
    Args:
        agent_type: AgentType enum or string name
        
    Returns:
        System prompt content as string
        
    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    if isinstance(agent_type, str):
        agent_type = AgentType(agent_type)
    
    prompt_file = PROMPTS_DIR / f"{agent_type.value}_agent.md"
    
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_file}")
    
    return prompt_file.read_text()


def get_prompt_for_context(user_message: str) -> tuple[AgentType, str]:
    """
    Automatically select the best prompt based on user message.
    
    Args:
        user_message: The user's input message
        
    Returns:
        Tuple of (AgentType, prompt_content)
    """
    message_lower = user_message.lower()
    
    # Quick check keywords
    if any(kw in message_lower for kw in ["quick check", "health check", "is it working", "status"]):
        return AgentType.QUICK_CHECK, load_prompt(AgentType.QUICK_CHECK)
    
    # Fix/remediation keywords  
    if any(kw in message_lower for kw in ["how to fix", "how do i fix", "fix it", "solve", "repair"]):
        return AgentType.REMEDIATION, load_prompt(AgentType.REMEDIATION)
    
    # Default to diagnostic agent for troubleshooting
    return AgentType.DIAGNOSTIC, load_prompt(AgentType.DIAGNOSTIC)


def list_available_prompts() -> list[dict]:
    """List all available prompt files with metadata."""
    prompts = []
    
    for agent_type in AgentType:
        prompt_file = PROMPTS_DIR / f"{agent_type.value}_agent.md"
        prompts.append({
            "agent_type": agent_type.value,
            "file": str(prompt_file),
            "exists": prompt_file.exists(),
            "size": prompt_file.stat().st_size if prompt_file.exists() else 0,
        })
    
    return prompts

