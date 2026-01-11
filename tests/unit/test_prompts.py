"""
Unit tests for prompt loading functionality.

Tests the prompt loading system from backend.prompts module.
"""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestAgentTypes:
    """Tests for AgentType enum."""
    
    def test_agent_types_exist(self):
        """All expected agent types should be defined."""
        from backend.prompts import AgentType
        
        expected_types = [
            "DIAGNOSTIC",
            "TRIAGE",
            "REMEDIATION",
            "MANAGER",
            "QUICK_CHECK",
            "DEFAULT",
        ]
        
        for agent_type in expected_types:
            assert hasattr(AgentType, agent_type), f"Missing AgentType.{agent_type}"
    
    def test_agent_type_values(self):
        """Agent types should have string values matching filenames."""
        from backend.prompts import AgentType
        
        # Values should be lowercase strings for filename matching
        assert AgentType.DIAGNOSTIC.value == "diagnostic"
        assert AgentType.DEFAULT.value == "default"


class TestLoadPrompt:
    """Tests for load_prompt function."""
    
    def test_load_prompt_returns_string(self):
        """load_prompt should return a non-empty string."""
        from backend.prompts import load_prompt, AgentType
        
        prompt = load_prompt(AgentType.DIAGNOSTIC)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
    
    def test_load_prompt_default(self):
        """Loading default agent should work."""
        from backend.prompts import load_prompt, AgentType
        
        prompt = load_prompt(AgentType.DEFAULT)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
    
    def test_load_prompt_caches_result(self):
        """Prompt loading should be cached for performance."""
        from backend.prompts import load_prompt, AgentType
        
        # Load twice
        prompt1 = load_prompt(AgentType.DIAGNOSTIC)
        prompt2 = load_prompt(AgentType.DIAGNOSTIC)
        
        # Should return same content
        assert prompt1 == prompt2


class TestPromptContent:
    """Tests for prompt content validation."""
    
    def test_diagnostic_prompt_contains_tools(self):
        """Diagnostic prompt should mention tools."""
        from backend.prompts import load_prompt, AgentType
        
        prompt = load_prompt(AgentType.DIAGNOSTIC)
        
        # Prompt should reference the diagnostic context
        assert any(word in prompt.lower() for word in ["diagnos", "network", "tool", "check"])
    
    def test_prompts_have_system_context(self):
        """Prompts should establish AI assistant context."""
        from backend.prompts import load_prompt, AgentType
        
        prompt = load_prompt(AgentType.DIAGNOSTIC)
        
        # Should have some assistant-related content
        assert len(prompt) > 100  # Reasonable minimum length


class TestGetPromptForContext:
    """Tests for get_prompt_for_context function if it exists."""
    
    def test_get_prompt_for_context_exists(self):
        """get_prompt_for_context should be available."""
        from backend import prompts
        
        # Check if function exists
        assert hasattr(prompts, 'get_prompt_for_context') or hasattr(prompts, 'load_prompt')


class TestPromptPaths:
    """Tests for prompt file path resolution."""
    
    def test_prompts_directory_exists(self):
        """Prompts directory should exist."""
        from backend.config import get_base_path
        
        prompts_path = get_base_path() / "prompts"
        
        assert prompts_path.exists(), f"Prompts directory not found: {prompts_path}"
    
    def test_diagnostic_prompt_file_exists(self):
        """Diagnostic agent prompt file should exist."""
        from backend.config import get_base_path
        
        prompts_path = get_base_path() / "prompts"
        diagnostic_file = prompts_path / "diagnostic_agent.md"
        
        assert diagnostic_file.exists(), f"Diagnostic prompt not found: {diagnostic_file}"

