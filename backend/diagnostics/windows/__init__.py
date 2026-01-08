"""Windows-specific diagnostic tools.

This module contains diagnostic tools that are only available on Windows,
including advanced troubleshooting capabilities for Dell hardware,
Microsoft 365, system file repair, and log analysis.

These tools leverage PowerShell and Windows-specific APIs for deep
system integration.
"""

from ..platform import Platform, get_platform

# Only export tools if running on Windows
# This prevents import errors on other platforms
_current_platform = get_platform()

__all__ = []

if _current_platform == Platform.WINDOWS:
    from .dell_audio import fix_dell_audio
    from .office_repair import repair_office365
    from .system_repair import run_dism_sfc
    from .log_analysis import review_system_logs
    
    __all__ = [
        "fix_dell_audio",
        "repair_office365",
        "run_dism_sfc",
        "review_system_logs",
    ]

