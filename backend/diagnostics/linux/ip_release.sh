#!/usr/bin/env bash
# ip_release.sh - Release DHCP lease on Linux
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
    output_failure "Could not determine network interface" '["Specify an interface name, e.g. eth0 or wlan0"]'
    exit 1
fi

# Get current IP before release
PREV_IP=$(ip -4 addr show "$INTERFACE" 2>/dev/null | grep -oP '(?<=inet )[\d.]+' | head -1)
PREV_STATE="has_ip"
[[ -z "$PREV_IP" ]] && PREV_STATE="no_ip"

METHOD="unknown"
EXIT_CODE=1

# Method 1: dhclient (most common)
if command -v dhclient &>/dev/null; then
    METHOD="dhclient"
    dhclient -r "$INTERFACE" 2>&1
    EXIT_CODE=$?

# Method 2: dhcpcd
elif command -v dhcpcd &>/dev/null; then
    METHOD="dhcpcd"
    dhcpcd -k "$INTERFACE" 2>&1
    EXIT_CODE=$?

# Method 3: NetworkManager
elif command -v nmcli &>/dev/null; then
    METHOD="nmcli"
    # Get connection name
    conn_name=$(nmcli -t -f NAME,DEVICE connection show --active 2>/dev/null | grep "$INTERFACE" | cut -d: -f1)
    if [[ -n "$conn_name" ]]; then
        nmcli connection down "$conn_name" 2>&1
        EXIT_CODE=$?
    fi

# Method 4: ip command (flush addresses)
else
    METHOD="ip_flush"
    ip addr flush dev "$INTERFACE" 2>&1
    EXIT_CODE=$?
fi

# Verify release
sleep 1
NEW_IP=$(ip -4 addr show "$INTERFACE" 2>/dev/null | grep -oP '(?<=inet )[\d.]+' | head -1)

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
    [[ -n "$PREV_IP" ]] && SUGGESTIONS+=("Previous IP: $PREV_IP")
    SUGGESTIONS+=("Run ip_renew to obtain a new lease")
else
    SUGGESTIONS+=("DHCP release may not have completed")
    SUGGESTIONS+=("Try: sudo dhclient -r $INTERFACE")
    SUGGESTIONS+=("Or: sudo ip addr flush dev $INTERFACE")
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

data=$(cat <<EOF
{
    "interface": "$INTERFACE",
    "previous_ip": $(if [[ -n "$PREV_IP" ]]; then echo "\"$PREV_IP\""; else echo "null"; fi),
    "current_ip": $(if [[ -n "$NEW_IP" ]]; then echo "\"$NEW_IP\""; else echo "null"; fi),
    "previous_state": "$PREV_STATE",
    "current_state": "$CURRENT_STATE",
    "method": "$METHOD",
    "success": $SUCCESS
}
EOF
)

output_success "$data" "$suggestions_json"
