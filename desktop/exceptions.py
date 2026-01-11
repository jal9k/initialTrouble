"""Desktop-specific exceptions."""


class DesktopError(Exception):
    """Base exception for desktop application errors."""
    pass


class OllamaError(DesktopError):
    """Base exception for Ollama-related errors."""
    pass


class OllamaStartupError(OllamaError):
    """Raised when Ollama fails to start."""
    pass


class OllamaNotFoundError(OllamaError):
    """Raised when the Ollama binary cannot be found."""
    pass


class InitializationError(DesktopError):
    """Raised when application initialization fails."""
    pass

