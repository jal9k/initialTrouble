#!/usr/bin/env bash
# toggle_bluetooth.sh - Enable/disable Bluetooth on Linux
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

# Get current state
PREVIOUS_STATE="unknown"
METHOD="unknown"
TARGET_STATE=$(if [[ "$ACTION" == "on" ]]; then echo "enabled"; else echo "disabled"; fi)

# Check if Bluetooth is available
if ! command -v rfkill &>/dev/null && ! command -v bluetoothctl &>/dev/null; then
    output_failure "No Bluetooth control tools found" '["Install: apt-get install rfkill bluez"]'
    exit 1
fi

# Check rfkill status
if command -v rfkill &>/dev/null; then
    rfkill_status=$(rfkill list bluetooth 2>/dev/null | grep -i "soft blocked")
    if [[ "$rfkill_status" == *"yes"* ]]; then
        PREVIOUS_STATE="disabled"
    elif [[ "$rfkill_status" == *"no"* ]]; then
        PREVIOUS_STATE="enabled"
    fi
fi

# Check bluetoothctl status as backup
if [[ "$PREVIOUS_STATE" == "unknown" ]] && command -v bluetoothctl &>/dev/null; then
    bt_status=$(bluetoothctl show 2>/dev/null | grep "Powered:" | awk '{print $2}')
    [[ "$bt_status" == "yes" ]] && PREVIOUS_STATE="enabled"
    [[ "$bt_status" == "no" ]] && PREVIOUS_STATE="disabled"
fi

SUCCESS="false"
CURRENT_STATE="unknown"

# Method 1: rfkill (preferred)
if command -v rfkill &>/dev/null; then
    METHOD="rfkill"
    
    if [[ "$ACTION" == "on" ]]; then
        rfkill unblock bluetooth 2>&1
        EXIT_CODE=$?
    else
        rfkill block bluetooth 2>&1
        EXIT_CODE=$?
    fi
    
    # May need to also use bluetoothctl to power on/off
    if command -v bluetoothctl &>/dev/null; then
        if [[ "$ACTION" == "on" ]]; then
            echo "power on" | bluetoothctl 2>/dev/null
        else
            echo "power off" | bluetoothctl 2>/dev/null
        fi
    fi

# Method 2: bluetoothctl only
elif command -v bluetoothctl &>/dev/null; then
    METHOD="bluetoothctl"
    
    if [[ "$ACTION" == "on" ]]; then
        echo "power on" | bluetoothctl 2>&1
        EXIT_CODE=$?
    else
        echo "power off" | bluetoothctl 2>&1
        EXIT_CODE=$?
    fi
fi

# Verify result
sleep 1

if command -v rfkill &>/dev/null; then
    rfkill_status=$(rfkill list bluetooth 2>/dev/null | grep -i "soft blocked")
    if [[ "$rfkill_status" == *"yes"* ]]; then
        CURRENT_STATE="disabled"
    elif [[ "$rfkill_status" == *"no"* ]]; then
        CURRENT_STATE="enabled"
    fi
fi

if [[ "$CURRENT_STATE" == "unknown" ]] && command -v bluetoothctl &>/dev/null; then
    bt_status=$(bluetoothctl show 2>/dev/null | grep "Powered:" | awk '{print $2}')
    [[ "$bt_status" == "yes" ]] && CURRENT_STATE="enabled"
    [[ "$bt_status" == "no" ]] && CURRENT_STATE="disabled"
fi

[[ "$CURRENT_STATE" == "$TARGET_STATE" ]] && SUCCESS="true"

# Build suggestions
SUGGESTIONS=()
if [[ "$SUCCESS" == "true" ]]; then
    if [[ "$TARGET_STATE" == "enabled" ]]; then
        SUGGESTIONS+=("Bluetooth enabled successfully")
        SUGGESTIONS+=("Device is now discoverable")
    else
        SUGGESTIONS+=("Bluetooth disabled successfully")
    fi
else
    SUGGESTIONS+=("Failed to toggle Bluetooth")
    SUGGESTIONS+=("Try running with sudo")
    SUGGESTIONS+=("Check: rfkill list bluetooth")
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

data=$(cat <<EOF
{
    "action": "$ACTION",
    "previous_state": "$PREVIOUS_STATE",
    "current_state": "$CURRENT_STATE",
    "target_state": "$TARGET_STATE",
    "method": "$METHOD",
    "success": $SUCCESS
}
EOF
)

output_success "$data" "$suggestions_json"
