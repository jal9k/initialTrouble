#!/usr/bin/env bash
# enable_wifi.sh - Enable/disable WiFi on macOS
# Usage: ./enable_wifi.sh [on|off] [interface]

source "$(dirname "$0")/common.sh"

# Handle test mode
if is_test_mode "$1"; then
    output_test_response "enable_wifi"
    exit 0
fi

ACTION="${1:-on}"
INTERFACE="${2:-}"

# Validate action
if [[ "$ACTION" != "on" ]] && [[ "$ACTION" != "off" ]]; then
    output_failure "Invalid action: $ACTION. Use 'on' or 'off'" '["Usage: enable_wifi.sh [on|off]"]'
    exit 1
fi

# Find WiFi interface if not specified
if [[ -z "$INTERFACE" ]]; then
    INTERFACE=$(networksetup -listallhardwareports 2>/dev/null | grep -A1 "Wi-Fi" | grep "Device" | awk '{print $2}')
fi

if [[ -z "$INTERFACE" ]]; then
    output_failure "Could not find WiFi interface" '["WiFi hardware may not be present or disabled"]'
    exit 1
fi

# Get WiFi service name
SERVICE_NAME=$(networksetup -listallhardwareports 2>/dev/null | grep -B1 "Device: $INTERFACE" | grep "Hardware Port" | cut -d: -f2 | xargs)

# Get current state
CURRENT_STATE=$(networksetup -getairportpower "$INTERFACE" 2>/dev/null | awk '{print $NF}')

PREVIOUS_STATE="unknown"
[[ "$CURRENT_STATE" == "On" ]] && PREVIOUS_STATE="enabled"
[[ "$CURRENT_STATE" == "Off" ]] && PREVIOUS_STATE="disabled"

# Execute action
if [[ "$ACTION" == "on" ]]; then
    networksetup -setairportpower "$INTERFACE" on 2>&1
    EXIT_CODE=$?
    TARGET_STATE="enabled"
else
    networksetup -setairportpower "$INTERFACE" off 2>&1
    EXIT_CODE=$?
    TARGET_STATE="disabled"
fi

# Verify result
sleep 1
NEW_STATE=$(networksetup -getairportpower "$INTERFACE" 2>/dev/null | awk '{print $NF}')

ACTUAL_STATE="unknown"
[[ "$NEW_STATE" == "On" ]] && ACTUAL_STATE="enabled"
[[ "$NEW_STATE" == "Off" ]] && ACTUAL_STATE="disabled"

SUCCESS="false"
[[ "$EXIT_CODE" -eq 0 ]] && [[ "$ACTUAL_STATE" == "$TARGET_STATE" ]] && SUCCESS="true"

# Build suggestions
SUGGESTIONS=()
if [[ "$SUCCESS" == "true" ]]; then
    if [[ "$TARGET_STATE" == "enabled" ]]; then
        SUGGESTIONS+=("WiFi adapter enabled successfully")
        SUGGESTIONS+=("Device should now scan for available networks")
        SUGGESTIONS+=("May need to manually connect to a network")
    else
        SUGGESTIONS+=("WiFi adapter disabled successfully")
    fi
else
    SUGGESTIONS+=("Failed to change WiFi state")
    SUGGESTIONS+=("Check if you have administrator privileges")
    SUGGESTIONS+=("Try using System Preferences > Network")
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

data=$(cat <<EOF
{
    "action": "$ACTION",
    "interface": "$INTERFACE",
    "service_name": $(if [[ -n "$SERVICE_NAME" ]]; then echo "\"$SERVICE_NAME\""; else echo "null"; fi),
    "previous_state": "$PREVIOUS_STATE",
    "current_state": "$ACTUAL_STATE",
    "target_state": "$TARGET_STATE",
    "success": $SUCCESS
}
EOF
)

output_success "$data" "$suggestions_json"
