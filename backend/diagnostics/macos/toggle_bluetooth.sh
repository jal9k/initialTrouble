#!/usr/bin/env bash
# toggle_bluetooth.sh - Enable/disable Bluetooth on macOS
# Usage: ./toggle_bluetooth.sh [on|off]

source "$(dirname "$0")/common.sh"

# Handle test mode
if is_test_mode "$1"; then
    output_test_response "toggle_bluetooth"
    exit 0
fi

ACTION="${1:-on}"

# Validate action
if [[ "$ACTION" != "on" ]] && [[ "$ACTION" != "off" ]]; then
    output_failure "Invalid action: $ACTION. Use 'on' or 'off'" '["Usage: toggle_bluetooth.sh [on|off]"]'
    exit 1
fi

# Check for blueutil (best option)
if command -v blueutil &>/dev/null; then
    # Get current state
    CURRENT=$(blueutil -p 2>/dev/null)
    PREVIOUS_STATE="unknown"
    [[ "$CURRENT" == "1" ]] && PREVIOUS_STATE="enabled"
    [[ "$CURRENT" == "0" ]] && PREVIOUS_STATE="disabled"
    
    # Execute action
    if [[ "$ACTION" == "on" ]]; then
        blueutil -p 1 2>&1
        EXIT_CODE=$?
        TARGET_STATE="enabled"
    else
        blueutil -p 0 2>&1
        EXIT_CODE=$?
        TARGET_STATE="disabled"
    fi
    
    # Verify
    sleep 1
    NEW=$(blueutil -p 2>/dev/null)
    ACTUAL_STATE="unknown"
    [[ "$NEW" == "1" ]] && ACTUAL_STATE="enabled"
    [[ "$NEW" == "0" ]] && ACTUAL_STATE="disabled"
    
    SUCCESS="false"
    [[ "$EXIT_CODE" -eq 0 ]] && [[ "$ACTUAL_STATE" == "$TARGET_STATE" ]] && SUCCESS="true"
    
    METHOD="blueutil"
else
    # Fallback: Use system commands (requires Bluetooth framework)
    # Note: This may not work on all macOS versions
    METHOD="system_framework"
    
    # Get current state via system_profiler
    CURRENT=$(system_profiler SPBluetoothDataType 2>/dev/null | grep "State:" | head -1 | awk '{print $2}')
    PREVIOUS_STATE="unknown"
    [[ "$CURRENT" == "On" ]] && PREVIOUS_STATE="enabled"
    [[ "$CURRENT" == "Off" ]] && PREVIOUS_STATE="disabled"
    
    # Try AppleScript method
    if [[ "$ACTION" == "on" ]]; then
        TARGET_STATE="enabled"
        osascript -e 'tell application "System Events" to tell process "ControlCenter" to click menu bar item "Bluetooth"' 2>/dev/null
    else
        TARGET_STATE="disabled"
        osascript -e 'tell application "System Events" to tell process "ControlCenter" to click menu bar item "Bluetooth"' 2>/dev/null
    fi
    
    EXIT_CODE=$?
    ACTUAL_STATE="unknown"
    SUCCESS="false"
    
    if [[ $EXIT_CODE -eq 0 ]]; then
        SUGGESTIONS+=("Bluetooth toggle attempted via AppleScript")
        SUGGESTIONS+=("Manual verification recommended")
    fi
fi

# Build suggestions
SUGGESTIONS=()
if [[ "$SUCCESS" == "true" ]]; then
    if [[ "$TARGET_STATE" == "enabled" ]]; then
        SUGGESTIONS+=("Bluetooth enabled successfully")
        SUGGESTIONS+=("Device is now discoverable")
    else
        SUGGESTIONS+=("Bluetooth disabled successfully")
    fi
elif [[ "$METHOD" != "blueutil" ]]; then
    SUGGESTIONS+=("blueutil not installed - limited Bluetooth control")
    SUGGESTIONS+=("Install via: brew install blueutil")
    SUGGESTIONS+=("Or toggle manually in System Preferences > Bluetooth")
else
    SUGGESTIONS+=("Failed to toggle Bluetooth")
    SUGGESTIONS+=("Check System Preferences > Bluetooth")
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

data=$(cat <<EOF
{
    "action": "$ACTION",
    "previous_state": "$PREVIOUS_STATE",
    "current_state": "$ACTUAL_STATE",
    "target_state": "$TARGET_STATE",
    "success": $SUCCESS,
    "method": "$METHOD"
}
EOF
)

output_success "$data" "$suggestions_json"
