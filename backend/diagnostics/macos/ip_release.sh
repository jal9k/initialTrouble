#!/usr/bin/env bash
# ip_release.sh - Release DHCP lease on macOS
# Usage: ./ip_release.sh [interface]

source "$(dirname "$0")/common.sh"

# Handle test mode
if is_test_mode "$1"; then
    output_test_response "ip_release"
    exit 0
fi

INTERFACE="${1:-}"

# Auto-detect primary interface
if [[ -z "$INTERFACE" ]]; then
    INTERFACE=$(get_primary_interface)
fi

if [[ -z "$INTERFACE" ]]; then
    output_failure "Could not determine network interface" '["Specify an interface name, e.g. en0"]'
    exit 1
fi

# Get current IP before release
PREV_IP=$(ifconfig "$INTERFACE" 2>/dev/null | grep "inet " | awk '{print $2}')
PREV_STATE="has_ip"
[[ -z "$PREV_IP" ]] && PREV_STATE="no_ip"

# Get network service name for interface
SERVICE_NAME=$(networksetup -listallhardwareports 2>/dev/null | grep -B1 "Device: $INTERFACE" | grep "Hardware Port" | cut -d: -f2 | xargs)

# Release DHCP
# Method 1: Using ipconfig (preferred)
ipconfig set "$INTERFACE" NONE 2>&1
EXIT_CODE=$?

# Verify release
sleep 1
NEW_IP=$(ifconfig "$INTERFACE" 2>/dev/null | grep "inet " | awk '{print $2}')

SUCCESS="false"
CURRENT_STATE="unknown"

if [[ -z "$NEW_IP" ]] || [[ "$NEW_IP" != "$PREV_IP" ]]; then
    SUCCESS="true"
    CURRENT_STATE="released"
else
    CURRENT_STATE="still_has_ip"
fi

# Build suggestions
SUGGESTIONS=()
if [[ "$SUCCESS" == "true" ]]; then
    SUGGESTIONS+=("DHCP lease released successfully")
    SUGGESTIONS+=("Previous IP: $PREV_IP")
    SUGGESTIONS+=("Run ip_renew to obtain a new lease")
else
    SUGGESTIONS+=("DHCP release may not have completed")
    SUGGESTIONS+=("Try: sudo ipconfig set $INTERFACE NONE")
    SUGGESTIONS+=("Or restart networking: networksetup -setnetworkserviceenabled '$SERVICE_NAME' off && sleep 2 && networksetup -setnetworkserviceenabled '$SERVICE_NAME' on")
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

data=$(cat <<EOF
{
    "interface": "$INTERFACE",
    "service_name": $(if [[ -n "$SERVICE_NAME" ]]; then echo "\"$SERVICE_NAME\""; else echo "null"; fi),
    "previous_ip": $(if [[ -n "$PREV_IP" ]]; then echo "\"$PREV_IP\""; else echo "null"; fi),
    "current_ip": $(if [[ -n "$NEW_IP" ]]; then echo "\"$NEW_IP\""; else echo "null"; fi),
    "previous_state": "$PREV_STATE",
    "current_state": "$CURRENT_STATE",
    "success": $SUCCESS
}
EOF
)

output_success "$data" "$suggestions_json"
