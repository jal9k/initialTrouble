#!/usr/bin/env bash
# enable_wifi.sh - Enable/disable WiFi on Linux
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
    # Try to find wireless interface
    INTERFACE=$(iw dev 2>/dev/null | grep Interface | head -1 | awk '{print $2}')
    
    # Fallback: look for wlan* or wlp*
    if [[ -z "$INTERFACE" ]]; then
        INTERFACE=$(ip link show 2>/dev/null | grep -oP '(wlan|wlp)[a-z0-9]+' | head -1)
    fi
fi

if [[ -z "$INTERFACE" ]]; then
    output_failure "Could not find WiFi interface" '["WiFi hardware may not be present", "Try: nmcli device wifi list"]'
    exit 1
fi

# Get current state
CURRENT_STATE="unknown"
PREVIOUS_STATE="unknown"

if ip link show "$INTERFACE" &>/dev/null; then
    link_state=$(ip link show "$INTERFACE" | grep -oP 'state \K\w+')
    [[ "$link_state" == "UP" ]] && PREVIOUS_STATE="enabled"
    [[ "$link_state" == "DOWN" ]] && PREVIOUS_STATE="disabled"
fi

# Check rfkill status
RFKILL_BLOCKED="false"
if command -v rfkill &>/dev/null; then
    rfkill_status=$(rfkill list wifi 2>/dev/null | grep -i "soft blocked: yes")
    [[ -n "$rfkill_status" ]] && RFKILL_BLOCKED="true"
fi

METHOD="unknown"
SUCCESS="false"
TARGET_STATE=$(if [[ "$ACTION" == "on" ]]; then echo "enabled"; else echo "disabled"; fi)

# Method 1: NetworkManager (preferred)
if command -v nmcli &>/dev/null; then
    METHOD="nmcli"
    
    if [[ "$ACTION" == "on" ]]; then
        # Unblock rfkill first if needed
        [[ "$RFKILL_BLOCKED" == "true" ]] && rfkill unblock wifi 2>/dev/null
        
        nmcli radio wifi on 2>&1
        EXIT_CODE=$?
    else
        nmcli radio wifi off 2>&1
        EXIT_CODE=$?
    fi
    
# Method 2: rfkill
elif command -v rfkill &>/dev/null; then
    METHOD="rfkill"
    
    if [[ "$ACTION" == "on" ]]; then
        rfkill unblock wifi 2>&1
        EXIT_CODE=$?
    else
        rfkill block wifi 2>&1
        EXIT_CODE=$?
    fi

# Method 3: ip link
else
    METHOD="ip_link"
    
    if [[ "$ACTION" == "on" ]]; then
        ip link set "$INTERFACE" up 2>&1
        EXIT_CODE=$?
    else
        ip link set "$INTERFACE" down 2>&1
        EXIT_CODE=$?
    fi
fi

# Verify result
sleep 1

if ip link show "$INTERFACE" &>/dev/null; then
    link_state=$(ip link show "$INTERFACE" | grep -oP 'state \K\w+')
    [[ "$link_state" == "UP" ]] && CURRENT_STATE="enabled"
    [[ "$link_state" == "DOWN" ]] && CURRENT_STATE="disabled"
fi

[[ "$CURRENT_STATE" == "$TARGET_STATE" ]] && SUCCESS="true"

# Build suggestions
SUGGESTIONS=()
if [[ "$SUCCESS" == "true" ]]; then
    if [[ "$TARGET_STATE" == "enabled" ]]; then
        SUGGESTIONS+=("WiFi adapter enabled successfully")
        SUGGESTIONS+=("Device should now scan for available networks")
        SUGGESTIONS+=("Connect with: nmcli device wifi connect <SSID>")
    else
        SUGGESTIONS+=("WiFi adapter disabled successfully")
    fi
else
    SUGGESTIONS+=("Failed to change WiFi state")
    SUGGESTIONS+=("Try running with sudo")
    SUGGESTIONS+=("Check rfkill: rfkill list wifi")
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

data=$(cat <<EOF
{
    "action": "$ACTION",
    "interface": "$INTERFACE",
    "previous_state": "$PREVIOUS_STATE",
    "current_state": "$CURRENT_STATE",
    "target_state": "$TARGET_STATE",
    "method": "$METHOD",
    "success": $SUCCESS
}
EOF
)

output_success "$data" "$suggestions_json"
