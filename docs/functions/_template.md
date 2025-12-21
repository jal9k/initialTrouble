# Function: {function_name}

## Purpose

{One-line description of what this diagnostic function does}

## OSI Layer

{Which OSI layer this function diagnoses: Physical / Link / Network / Transport / Application}

## When to Use

{Describe the scenarios when this diagnostic should be called}

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| example | string | No | None | Example parameter |

## Output Schema

```python
class {FunctionName}Result(BaseModel):
    """Result data specific to this diagnostic."""
    
    # Add function-specific fields here
    field_name: str = Field(description="Description of this field")
```

## Platform Commands

### macOS

```bash
# Command(s) to run on macOS
example_command --flag
```

**Parsing Logic:**
- How to parse the command output
- What patterns to look for

### Windows

```powershell
# PowerShell command(s) to run on Windows
Get-ExampleCommand -Parameter Value
```

**Parsing Logic:**
- How to parse the PowerShell output
- What patterns to look for

## Error Handling

| Error Condition | Detection | Suggested Action |
|-----------------|-----------|------------------|
| Command timeout | Timeout exception | Suggest checking if system is responsive |
| Command not found | Non-zero exit + specific error | Suggest installing required tools |

## Example Output

### Success Case

```json
{
    "success": true,
    "function_name": "{function_name}",
    "platform": "macos",
    "data": {
        "field_name": "example_value"
    },
    "raw_output": "...",
    "error": null,
    "suggestions": []
}
```

### Failure Case

```json
{
    "success": false,
    "function_name": "{function_name}",
    "platform": "macos",
    "data": {},
    "raw_output": "...",
    "error": "Description of what failed",
    "suggestions": [
        "Suggested fix or next diagnostic to run"
    ]
}
```

## Test Cases

### Manual Testing

1. **Happy Path**: Run on a healthy system, verify expected output
2. **Failure Path**: Simulate failure condition (e.g., disable adapter), verify error handling
3. **Cross-Platform**: Run on both macOS and Windows, verify consistent behavior

### Automated Tests

```python
import pytest
from backend.diagnostics.{module} import {ClassName}

@pytest.mark.asyncio
async def test_{function_name}_success():
    """Test successful execution."""
    diag = {ClassName}()
    result = await diag.run()
    assert result.success
    # Add specific assertions

@pytest.mark.asyncio
async def test_{function_name}_failure():
    """Test failure handling."""
    # Mock failure condition
    pass
```

## Implementation Notes

- {Any special considerations for implementation}
- {Performance notes}
- {Security considerations}

## Related Functions

- `{related_function_1}`: {Brief description of relationship}
- `{related_function_2}`: {Brief description of relationship}

