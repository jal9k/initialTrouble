# TechTim(e) Test Suite

## Quick Start

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=backend --cov=desktop --cov=analytics --cov-report=html
```

Run specific test file:
```bash
pytest tests/unit/test_chat_service.py
```

Run tests matching a pattern:
```bash
pytest -k "test_session"
```

Run only unit tests:
```bash
pytest tests/unit/ -v
```

Run only integration tests:
```bash
pytest tests/integration/ -v
```

## Test Organization

```
tests/
├── conftest.py          # Shared fixtures
├── unit/                # Unit tests (isolated components)
│   ├── test_config.py
│   ├── test_prompts.py
│   ├── test_chat_service.py
│   └── test_ollama_manager.py
├── integration/         # Integration tests
│   ├── test_api_bridge.py
│   └── test_full_chat.py
└── fixtures/            # Test data and mocks
    ├── mock_ollama.py
    └── sample_data.py
```

## Writing Tests

### Async Tests

Use `@pytest.mark.asyncio` for async tests:

```python
@pytest.mark.asyncio
async def test_something_async():
    result = await some_async_function()
    assert result is not None
```

### Using Markers

Mark slow tests:
```python
@pytest.mark.slow
def test_slow_operation():
    ...
```

Mark integration tests:
```python
@pytest.mark.integration
def test_integration():
    ...
```

Mark tests requiring Ollama:
```python
@pytest.mark.requires_ollama
def test_with_ollama():
    ...
```

Run tests excluding slow ones:
```bash
pytest -m "not slow"
```

## Common Fixtures

### Temporary Directories

- `temp_dir`: Creates a temporary directory, cleaned up after test
- `temp_user_data`: Creates TechTime-like user data directory structure

### Configuration

- `mock_settings`: Settings with temporary paths, patches `get_settings()`

### LLM Mocks

- `mock_chat_message`: Factory for creating ChatMessage objects
- `mock_chat_response`: Factory for creating ChatResponse objects
- `mock_llm_router`: Mock LLM router returning predictable responses

### Tool Mocks

- `mock_tool_result`: Factory for creating ToolResult objects
- `mock_tool_registry`: Mock tool registry with sample tool definitions

### Analytics

- `mock_analytics_storage`: Real AnalyticsStorage with temp database
- `mock_analytics_collector`: Real AnalyticsCollector with test storage

### Services

- `chat_service`: ChatService with mocked dependencies
- `initialized_chat_service`: ChatService ready for use (call `close()` after)

### Desktop

- `mock_window`: Mock PyWebView window
- `mock_ollama_manager`: Mock OllamaManager
- `api_bridge`: TechTimApi instance with mocks

### Sample Data

- `sample_messages`: List of sample ChatMessage objects
- `sample_session_id`: Standard test session ID

## Testing ChatService

```python
@pytest.mark.asyncio
async def test_chat(initialized_chat_service):
    response = await initialized_chat_service.chat(
        "session-id",
        "Hello"
    )
    assert response.content is not None
    assert isinstance(response, ChatServiceResponse)
```

## Testing API Bridge

```python
def test_api_method(api_bridge):
    result = api_bridge.some_method()
    assert result['success'] is True
    assert 'data' in result
```

## Coverage Reports

Generate HTML coverage report:
```bash
pytest --cov=backend --cov=desktop --cov=analytics --cov-report=html
open htmlcov/index.html
```

Generate terminal coverage summary:
```bash
pytest --cov=backend --cov=desktop --cov=analytics --cov-report=term-missing
```

## Debugging Tests

Run with verbose output:
```bash
pytest -vvv tests/unit/test_chat_service.py::TestChatBasic::test_chat_returns_response
```

Show print statements:
```bash
pytest -s tests/unit/test_config.py
```

Stop on first failure:
```bash
pytest -x
```

Run last failed tests:
```bash
pytest --lf
```

## Notes

- All tests use mocks - no real Ollama instance required
- Fixtures automatically clean up temporary files
- The `initialized_chat_service` fixture handles setup/teardown
- Use `get_settings.cache_clear()` when testing configuration

