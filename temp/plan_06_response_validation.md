# Plan: Add Response Validation

**Priority**: Medium  
**Effort**: Medium  
**Status**: Not Started

---

## Problem

Current implementation doesn't validate LLM responses, which can lead to:
- Hallucinated tool names being referenced
- Out-of-sequence tool calls
- Invalid JSON in tool arguments
- Responses that don't follow the expected format

## Goal

Implement response validation that catches malformed or invalid LLM outputs before they reach the user, with graceful error recovery.

---

## Implementation Steps

### Step 1: Create Response Validator Module

**File: `backend/llm/response_validator.py`**

```python
"""Response validation for LLM outputs.

This module validates LLM responses to catch:
- Hallucinated tool names
- Invalid tool arguments
- Malformed response structures
- Protocol violations
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from ..tools import ToolRegistry

logger = logging.getLogger("techtime.llm.response_validator")


@dataclass
class ValidationResult:
    """Result of response validation."""
    
    is_valid: bool
    """Whether the response passed all validations."""
    
    errors: list[str] = field(default_factory=list)
    """List of validation errors found."""
    
    warnings: list[str] = field(default_factory=list)
    """Non-critical issues found."""
    
    sanitized_response: dict | None = None
    """Cleaned/fixed response if recoverable."""
    
    @classmethod
    def valid(cls) -> "ValidationResult":
        return cls(is_valid=True)
    
    @classmethod
    def invalid(cls, errors: list[str]) -> "ValidationResult":
        return cls(is_valid=False, errors=errors)
    
    def add_error(self, error: str) -> None:
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)


class ResponseValidator:
    """
    Validate LLM responses against expected schema and tool registry.
    
    Validations performed:
    1. Tool name validation - ensures referenced tools exist
    2. Argument validation - ensures tool arguments match schema
    3. Sequence validation - checks tool call order makes sense
    4. Content validation - ensures response has required fields
    
    Example:
        validator = ResponseValidator(tool_registry)
        result = validator.validate_response(llm_response)
        if not result.is_valid:
            logger.error(f"Invalid response: {result.errors}")
    """
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        strict_mode: bool = False,
    ):
        """
        Initialize the validator.
        
        Args:
            tool_registry: Registry of valid tools
            strict_mode: If True, treat warnings as errors
        """
        self._registry = tool_registry
        self._strict = strict_mode
        
        # Cache valid tool names
        self._valid_tools = set(
            d.name for d in tool_registry.get_all_definitions()
        )
    
    def validate_response(
        self,
        response: Any,
        expected_sequence: list[str] | None = None,
    ) -> ValidationResult:
        """
        Validate a complete LLM response.
        
        Args:
            response: The LLM response object
            expected_sequence: Optional expected tool call sequence
        
        Returns:
            ValidationResult with any errors/warnings
        """
        result = ValidationResult.valid()
        
        # Validate tool calls if present
        tool_calls = self._extract_tool_calls(response)
        if tool_calls:
            self._validate_tool_calls(tool_calls, result)
            
            if expected_sequence:
                self._validate_sequence(tool_calls, expected_sequence, result)
        
        # Validate content
        content = self._extract_content(response)
        if content:
            self._validate_content(content, result)
        
        # Convert warnings to errors in strict mode
        if self._strict and result.warnings:
            result.errors.extend(result.warnings)
            result.is_valid = False
        
        return result
    
    def validate_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ValidationResult:
        """
        Validate a single tool call.
        
        Args:
            tool_name: Name of the tool being called
            arguments: Arguments being passed to the tool
        
        Returns:
            ValidationResult with any errors
        """
        result = ValidationResult.valid()
        
        # Check tool exists
        if tool_name not in self._valid_tools:
            result.add_error(
                f"Unknown tool: '{tool_name}'. "
                f"Valid tools: {sorted(self._valid_tools)[:5]}..."
            )
            return result
        
        # Get tool definition and validate args
        definition = self._registry.get_definition(tool_name)
        if definition:
            self._validate_arguments(definition, arguments, result)
        
        return result
    
    def _extract_tool_calls(self, response: Any) -> list[dict]:
        """Extract tool calls from response."""
        if hasattr(response, 'tool_calls'):
            return response.tool_calls or []
        if isinstance(response, dict):
            return response.get('tool_calls', [])
        return []
    
    def _extract_content(self, response: Any) -> str:
        """Extract text content from response."""
        if hasattr(response, 'final_response'):
            return response.final_response or ""
        if hasattr(response, 'content'):
            return response.content or ""
        if isinstance(response, dict):
            return response.get('content', '') or response.get('final_response', '')
        return ""
    
    def _validate_tool_calls(
        self,
        tool_calls: list[dict],
        result: ValidationResult,
    ) -> None:
        """Validate all tool calls in a response."""
        for i, tc in enumerate(tool_calls):
            tool_name = tc.get('name', tc.get('function', {}).get('name', ''))
            arguments = tc.get('arguments', tc.get('function', {}).get('arguments', {}))
            
            # Parse arguments if string
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError as e:
                    result.add_error(
                        f"Tool call {i}: Invalid JSON arguments for '{tool_name}': {e}"
                    )
                    continue
            
            # Validate the tool call
            tc_result = self.validate_tool_call(tool_name, arguments)
            result.errors.extend(tc_result.errors)
            result.warnings.extend(tc_result.warnings)
    
    def _validate_arguments(
        self,
        definition: Any,
        arguments: dict[str, Any],
        result: ValidationResult,
    ) -> None:
        """Validate arguments against tool definition."""
        param_names = {p.name for p in definition.parameters}
        required_params = {p.name for p in definition.parameters if p.required}
        
        # Check for unknown arguments
        unknown = set(arguments.keys()) - param_names
        if unknown:
            result.add_warning(
                f"Tool '{definition.name}' received unknown arguments: {unknown}"
            )
        
        # Check for missing required arguments
        missing = required_params - set(arguments.keys())
        if missing:
            result.add_error(
                f"Tool '{definition.name}' missing required arguments: {missing}"
            )
        
        # Type validation
        for param in definition.parameters:
            if param.name in arguments:
                value = arguments[param.name]
                expected_type = self._type_map.get(param.type)
                
                if expected_type and not isinstance(value, expected_type):
                    result.add_warning(
                        f"Tool '{definition.name}' argument '{param.name}' "
                        f"expected {param.type}, got {type(value).__name__}"
                    )
                
                # Enum validation
                if param.enum and value not in param.enum:
                    result.add_error(
                        f"Tool '{definition.name}' argument '{param.name}' "
                        f"must be one of {param.enum}, got '{value}'"
                    )
    
    _type_map = {
        "string": str,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    
    def _validate_sequence(
        self,
        tool_calls: list[dict],
        expected: list[str],
        result: ValidationResult,
    ) -> None:
        """Validate tool call sequence matches expected order."""
        actual = [
            tc.get('name', tc.get('function', {}).get('name', ''))
            for tc in tool_calls
        ]
        
        # Check if actual is a valid prefix or matches expected
        for i, (a, e) in enumerate(zip(actual, expected)):
            if a != e:
                result.add_warning(
                    f"Tool sequence mismatch at position {i}: "
                    f"expected '{e}', got '{a}'"
                )
    
    def _validate_content(
        self,
        content: str,
        result: ValidationResult,
    ) -> None:
        """Validate response content."""
        # Check for empty content
        if not content.strip():
            result.add_warning("Response content is empty")
        
        # Check for potential hallucinations (tool references in text)
        tool_mentions = re.findall(r'\b(\w+_\w+)\b', content)
        for mention in tool_mentions:
            # If it looks like a tool name but isn't valid
            if (
                mention.endswith('_status') or 
                mention.startswith('check_') or 
                mention.startswith('get_')
            ) and mention not in self._valid_tools:
                result.add_warning(
                    f"Content mentions non-existent tool-like name: '{mention}'"
                )


# Diagnostic sequence validator
EXPECTED_DIAGNOSTIC_SEQUENCE = [
    "check_adapter_status",
    "get_ip_config",
    "ping_gateway",
    "ping_dns",
    "test_dns_resolution",
]


def validate_diagnostic_sequence(tool_calls: list[dict]) -> ValidationResult:
    """
    Validate that diagnostic tool calls follow the expected sequence.
    
    The standard network diagnostic sequence is:
    1. check_adapter_status
    2. get_ip_config
    3. ping_gateway
    4. ping_dns
    5. test_dns_resolution
    """
    result = ValidationResult.valid()
    
    actual_names = [
        tc.get('name', tc.get('function', {}).get('name', ''))
        for tc in tool_calls
    ]
    
    # Filter to only diagnostic tools
    diagnostic_calls = [
        name for name in actual_names
        if name in EXPECTED_DIAGNOSTIC_SEQUENCE
    ]
    
    # Check sequence
    expected_idx = 0
    for call in diagnostic_calls:
        try:
            call_idx = EXPECTED_DIAGNOSTIC_SEQUENCE.index(call)
        except ValueError:
            continue
        
        if call_idx < expected_idx:
            result.add_warning(
                f"Out-of-order diagnostic: '{call}' called after "
                f"'{EXPECTED_DIAGNOSTIC_SEQUENCE[expected_idx]}'"
            )
        expected_idx = max(expected_idx, call_idx + 1)
    
    return result
```

### Step 2: Integrate with GlueLLMWrapper

**Modify: `backend/llm/gluellm_wrapper.py`**

```python
from .response_validator import ResponseValidator, validate_diagnostic_sequence

class GlueLLMWrapper:
    def __init__(self, ...):
        # ... existing init ...
        self._response_validator: ResponseValidator | None = None
    
    def _get_validator(self) -> ResponseValidator:
        """Lazy-initialize the response validator."""
        if self._response_validator is None:
            self._response_validator = ResponseValidator(
                tool_registry=self._tool_registry,
                strict_mode=False,  # Warn but allow
            )
        return self._response_validator
    
    async def chat(self, ...):
        # ... existing code up to LLM call ...
        
        result = await self._call_with_retry(...)
        
        # Validate response
        validator = self._get_validator()
        validation = validator.validate_response(result)
        
        if not validation.is_valid:
            logger.error(f"Response validation failed: {validation.errors}")
            # Could return error response or attempt recovery
        
        if validation.warnings:
            logger.warning(f"Response validation warnings: {validation.warnings}")
        
        # Also validate diagnostic sequence
        if hasattr(result, 'tool_calls') and result.tool_calls:
            seq_validation = validate_diagnostic_sequence(result.tool_calls)
            if seq_validation.warnings:
                logger.warning(f"Sequence warnings: {seq_validation.warnings}")
        
        # ... rest of existing method ...
```

### Step 3: Add Recovery Logic

**Add to: `backend/llm/response_validator.py`**

```python
class ResponseRecovery:
    """
    Attempt to recover from validation errors.
    
    Recovery strategies:
    1. Unknown tool → suggest closest valid tool
    2. Invalid arguments → use defaults
    3. Malformed JSON → attempt repair
    """
    
    @staticmethod
    def suggest_tool(
        invalid_name: str,
        valid_tools: set[str],
    ) -> str | None:
        """Find the closest matching valid tool name."""
        from difflib import get_close_matches
        
        matches = get_close_matches(invalid_name, valid_tools, n=1, cutoff=0.6)
        return matches[0] if matches else None
    
    @staticmethod
    def repair_json_arguments(malformed: str) -> dict | None:
        """Attempt to repair malformed JSON arguments."""
        import json
        
        # Common fixes
        repairs = [
            # Try as-is first
            lambda s: json.loads(s),
            # Fix single quotes
            lambda s: json.loads(s.replace("'", '"')),
            # Fix trailing commas
            lambda s: json.loads(re.sub(r',\s*}', '}', s)),
            # Fix trailing commas in arrays
            lambda s: json.loads(re.sub(r',\s*]', ']', s)),
            # Wrap bare values
            lambda s: json.loads(f'{{{s}}}') if ':' in s and not s.startswith('{') else None,
        ]
        
        for repair in repairs:
            try:
                result = repair(malformed)
                if result is not None:
                    return result
            except (json.JSONDecodeError, Exception):
                continue
        
        return None
```

### Step 4: Add Tests

**File: `backend/tests/test_response_validator.py`**

```python
"""Tests for LLM response validation."""

import pytest
from unittest.mock import MagicMock

from backend.llm.response_validator import (
    ResponseValidator,
    ValidationResult,
    validate_diagnostic_sequence,
    ResponseRecovery,
)


class TestResponseValidator:
    """Test suite for ResponseValidator."""
    
    @pytest.fixture
    def mock_registry(self):
        registry = MagicMock()
        registry.get_all_definitions.return_value = [
            MagicMock(name="check_adapter_status", parameters=[]),
            MagicMock(name="get_ip_config", parameters=[]),
            MagicMock(name="ping_gateway", parameters=[]),
            MagicMock(name="test_dns_resolution", parameters=[
                MagicMock(name="hostnames", type="string", required=False, enum=None),
            ]),
        ]
        registry.get_definition.return_value = MagicMock(
            parameters=[],
        )
        return registry
    
    @pytest.fixture
    def validator(self, mock_registry):
        return ResponseValidator(mock_registry)
    
    def test_valid_tool_call(self, validator):
        """Should accept valid tool calls."""
        result = validator.validate_tool_call("check_adapter_status", {})
        assert result.is_valid
    
    def test_invalid_tool_name(self, validator):
        """Should reject unknown tool names."""
        result = validator.validate_tool_call("nonexistent_tool", {})
        assert not result.is_valid
        assert "Unknown tool" in result.errors[0]
    
    def test_hallucinated_tool_warning(self, validator):
        """Should warn about tool-like names in content."""
        response = MagicMock()
        response.tool_calls = []
        response.final_response = "I ran check_network_status to diagnose"
        
        result = validator.validate_response(response)
        # Should warn about check_network_status (doesn't exist)
        assert any("check_network_status" in w for w in result.warnings)
    
    def test_empty_content_warning(self, validator):
        """Should warn about empty response content."""
        response = MagicMock()
        response.tool_calls = []
        response.final_response = ""
        
        result = validator.validate_response(response)
        assert any("empty" in w.lower() for w in result.warnings)


class TestDiagnosticSequence:
    """Test diagnostic sequence validation."""
    
    def test_correct_sequence(self):
        """Should accept correct sequence."""
        tool_calls = [
            {"name": "check_adapter_status"},
            {"name": "get_ip_config"},
            {"name": "ping_gateway"},
        ]
        result = validate_diagnostic_sequence(tool_calls)
        assert result.is_valid
        assert not result.warnings
    
    def test_out_of_order_warning(self):
        """Should warn about out-of-order calls."""
        tool_calls = [
            {"name": "ping_gateway"},  # Should be after check_adapter_status
            {"name": "check_adapter_status"},
        ]
        result = validate_diagnostic_sequence(tool_calls)
        assert result.warnings  # Should have warning


class TestResponseRecovery:
    """Test error recovery."""
    
    def test_suggest_tool_close_match(self):
        """Should suggest close matches."""
        valid = {"check_adapter_status", "get_ip_config"}
        suggestion = ResponseRecovery.suggest_tool("check_adaptor_status", valid)
        assert suggestion == "check_adapter_status"
    
    def test_suggest_tool_no_match(self):
        """Should return None for no close match."""
        valid = {"check_adapter_status"}
        suggestion = ResponseRecovery.suggest_tool("completely_different", valid)
        assert suggestion is None
    
    def test_repair_single_quotes(self):
        """Should fix single-quoted JSON."""
        malformed = "{'key': 'value'}"
        result = ResponseRecovery.repair_json_arguments(malformed)
        assert result == {"key": "value"}
    
    def test_repair_trailing_comma(self):
        """Should fix trailing commas."""
        malformed = '{"key": "value",}'
        result = ResponseRecovery.repair_json_arguments(malformed)
        assert result == {"key": "value"}
```

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/llm/response_validator.py` | Create | Validation logic |
| `backend/llm/gluellm_wrapper.py` | Modify | Integrate validation |
| `backend/tests/test_response_validator.py` | Create | Unit tests |
| `backend/config.py` | Modify | Add validation settings |

---

## Testing Plan

1. **Unit Tests**
   - Valid tool calls accepted
   - Invalid tool names rejected
   - Hallucinated tools detected
   - Sequence validation works
   - JSON repair strategies

2. **Integration Tests**
   - Validation runs on real responses
   - Recovery suggestions are useful
   - Warnings logged appropriately

3. **Manual Testing**
   - Inject invalid responses and verify handling
   - Check logs for validation warnings

---

## Success Criteria

- [ ] Invalid tool names are caught
- [ ] Invalid arguments are detected
- [ ] Out-of-sequence calls generate warnings
- [ ] Hallucinated tool names in content are flagged
- [ ] JSON repair attempts work for common issues
- [ ] Tool suggestions are accurate
- [ ] All tests pass
