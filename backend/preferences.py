"""
User preferences management for TechTim(e).

Stores user preferences in a JSON file in the user data directory.
Preferences include:
- UI theme (light/dark/system)
- Selected model
- Window position and size
- Other user settings
"""
import json
import logging
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict

from .config import get_settings

logger = logging.getLogger("techtime.preferences")


@dataclass
class WindowState:
    """Window position and size."""
    x: int = 100
    y: int = 100
    width: int = 1200
    height: int = 800
    maximized: bool = False


@dataclass
class UserPreferences:
    """User preferences data structure."""
    
    # UI Settings
    theme: str = "system"  # "light", "dark", "system"
    
    # Model Settings
    preferred_model: str = ""  # Empty = use default from config
    
    # Window State
    window: WindowState = field(default_factory=WindowState)
    
    # Session Settings
    auto_save_sessions: bool = True
    confirm_delete_session: bool = True
    
    # Advanced
    debug_mode: bool = False
    show_tool_details: bool = True
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserPreferences":
        """Create from dictionary."""
        # Make a copy to avoid modifying the input
        data = data.copy()
        window_data = data.pop("window", {})
        window = WindowState(**window_data)
        return cls(window=window, **data)


class PreferencesManager:
    """
    Manages loading and saving user preferences.
    
    Usage:
        prefs = PreferencesManager()
        
        # Get current preferences
        theme = prefs.get("theme")
        
        # Update a preference
        prefs.set("theme", "dark")
        
        # Save to disk
        prefs.save()
    """
    
    def __init__(self, preferences_file: Optional[Path] = None):
        """
        Initialize the preferences manager.
        
        Args:
            preferences_file: Path to preferences file (default: user_data/preferences.json)
        """
        settings = get_settings()
        
        if preferences_file:
            self._file = preferences_file
        else:
            self._file = settings.user_data_path / "preferences.json"
        
        self._preferences = self._load()
    
    def _load(self) -> UserPreferences:
        """Load preferences from disk."""
        if not self._file.exists():
            logger.info(f"No preferences file found, using defaults")
            return UserPreferences()
        
        try:
            with open(self._file, "r") as f:
                data = json.load(f)
            
            logger.debug(f"Loaded preferences from {self._file}")
            return UserPreferences.from_dict(data)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid preferences file, using defaults: {e}")
            return UserPreferences()
        except Exception as e:
            logger.warning(f"Failed to load preferences: {e}")
            return UserPreferences()
    
    def save(self) -> bool:
        """
        Save preferences to disk.
        
        Returns:
            True if save succeeded
        """
        try:
            # Ensure directory exists
            self._file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self._file, "w") as f:
                json.dump(self._preferences.to_dict(), f, indent=2)
            
            logger.debug(f"Saved preferences to {self._file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a preference value.
        
        Args:
            key: Preference key (e.g., "theme", "window.width")
            default: Default value if not found
        
        Returns:
            Preference value
        """
        try:
            # Handle nested keys (e.g., "window.width")
            parts = key.split(".")
            value = self._preferences
            
            for part in parts:
                if hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return default
            
            return value
            
        except Exception:
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a preference value.
        
        Args:
            key: Preference key (e.g., "theme", "window.width")
            value: Value to set
        """
        try:
            parts = key.split(".")
            
            if len(parts) == 1:
                setattr(self._preferences, key, value)
            else:
                # Navigate to parent object
                obj = self._preferences
                for part in parts[:-1]:
                    obj = getattr(obj, part)
                setattr(obj, parts[-1], value)
            
            logger.debug(f"Set preference {key} = {value}")
            
        except Exception as e:
            logger.warning(f"Failed to set preference {key}: {e}")
    
    @property
    def all(self) -> UserPreferences:
        """Get all preferences."""
        return self._preferences
    
    def reset(self) -> None:
        """Reset all preferences to defaults."""
        self._preferences = UserPreferences()
        logger.info("Reset preferences to defaults")
    
    def update_window_state(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        maximized: Optional[bool] = None,
    ) -> None:
        """
        Update window state preferences.
        
        Args:
            x: Window x position
            y: Window y position
            width: Window width
            height: Window height
            maximized: Whether window is maximized
        """
        if x is not None:
            self._preferences.window.x = x
        if y is not None:
            self._preferences.window.y = y
        if width is not None:
            self._preferences.window.width = width
        if height is not None:
            self._preferences.window.height = height
        if maximized is not None:
            self._preferences.window.maximized = maximized


# Global instance
_preferences_manager: Optional[PreferencesManager] = None


def get_preferences() -> PreferencesManager:
    """Get the global preferences manager instance."""
    global _preferences_manager
    
    if _preferences_manager is None:
        _preferences_manager = PreferencesManager()
    
    return _preferences_manager
