"""Logging configuration for TechTime."""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_dir: Path | None = None,
) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Whether to also log to a file
        log_dir: Directory for log files (default: data/logs/)

    Returns:
        Configured root logger
    """
    # Create logger
    logger = logging.getLogger("techtime")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (stderr to not interfere with Rich output)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)  # Only warnings+ to console
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    if log_to_file:
        # Use provided log_dir, or get from settings, or fallback
        if log_dir is None:
            try:
                from .config import get_settings
                log_dir = get_settings().log_path
            except Exception:
                log_dir = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        # Daily log file
        log_file = log_dir / f"techtime_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # All levels to file
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        logger.info(f"Logging to file: {log_file}")

    return logger


def get_logger(name: str = "techtime") -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


# #region debug
import json
from typing import Any


def debug_log(prefix: str, message: str, data: Any = None) -> None:
    """Structured debug logging with timestamp and prefix.
    
    Usage:
        debug_log("AgentExecutor", "Processing user query", {"query": user_input})
        debug_log("ToolRegistry", "Executing tool", {"name": tool_name})
    
    To remove all debug logging, search for '#region debug' and delete to '#endregion'.
    """
    logger = get_logger("techtime.debug")
    ts = datetime.now().strftime("%H:%M:%S")
    
    if data is not None:
        data_str = json.dumps(data, default=str)
        if len(data_str) > 300:
            data_str = data_str[:300] + "..."
        logger.info(f"[{ts}] [{prefix}] {message}: {data_str}")
    else:
        logger.info(f"[{ts}] [{prefix}] {message}")


def format_tool_output(tool_name: str, result: dict) -> str:
    """Format tool output for display panel."""
    return f"• {tool_name} Output:\n\n```json\n{json.dumps(result, indent=2)}\n```"


class ResponseDiagnostics:
    """Tracks response quality metrics for debug display.
    
    Collects confidence scores, thoughts, and tool results during
    a chat turn for display in a Response Diagnostics panel.
    """
    
    def __init__(self):
        self.confidence_score: float = 0.5
        self.thoughts: list[str] = []
        self.tools_used: list[dict] = []
    
    def add_thought(self, thought: str) -> None:
        """Add a reasoning observation."""
        self.thoughts.append(thought)
    
    def add_tool_result(self, name: str, result: dict) -> None:
        """Record tool execution result and adjust confidence."""
        self.tools_used.append({"name": name, "result": result})
        # Adjust confidence based on tool success
        if result.get("success", True):
            self.confidence_score = min(1.0, self.confidence_score + 0.1)
        else:
            self.confidence_score = max(0.0, self.confidence_score - 0.2)
    
    def set_confidence(self, score: float) -> None:
        """Manually set confidence score."""
        self.confidence_score = max(0.0, min(1.0, score))
    
    def to_panel_content(self) -> str:
        """Format diagnostics for Rich Panel display."""
        lines = [
            f"Confidence Score: {self.confidence_score:.2f}",
            "",
            "Thoughts:",
        ]
        for thought in self.thoughts:
            lines.append(f" • {thought}")
        
        if self.tools_used:
            lines.extend(["", "Tools Used:"])
            for tool in self.tools_used:
                result_preview = str(tool.get("result", {}))[:50]
                lines.append(f" • {tool['name']}: {result_preview}")
        
        return "\n".join(lines)
# #endregion


