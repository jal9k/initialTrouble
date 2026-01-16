#!/usr/bin/env bash
# ip_renew.sh - Renew DHCP lease on Linux
# Usage: ./ip_renew.sh [interface]

source "$(dirname "$0")/common.sh"

# Handle test mode
if is_test_mode "$1"; then
    output_test_response "ip_renew"
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

# Get current IP before renew
PREV_IP=$(ip -4 addr show "$INTERFACE" 2>/dev/null | grep -oP '(?<=inet )[\d.]+' | head -1)

METHOD="unknown"
EXIT_CODE=1

# Method 1: dhclient (most common)
if command -v dhclient &>/dev/null; then
    METHOD="dhclient"
    dhclient "$INTERFACE" 2>&1
    EXIT_CODE=$?

# Method 2: dhcpcd
elif command -v dhcpcd &>/dev/null; then
    METHOD="dhcpcd"
    dhcpcd "$INTERFACE" 2>&1
    EXIT_CODE=$?

# Method 3: NetworkManager
elif command -v nmcli &>/dev/null; then
    METHOD="nmcli"
    # Get connection name
    conn_name=$(nmcli -t -f NAME,DEVICE connection show 2>/dev/null | grep "$INTERFACE" | cut -d: -f1 | head -1)
    if [[ -n "$conn_name" ]]; then
        nmcli connection up "$conn_name" 2>&1
        EXIT_CODE=$?
    fi
fi

# Wait for DHCP to complete
sleep 3

# Verify renewal
NEW_IP=$(ip -4 addr show "$INTERFACE" 2>/dev/null | grep -oP '(?<=inet )[\d.]+' | head -1)
GATEWAY=$(get_default_gateway)

SUCCESS="false"
CURRENT_STATE="unknown"

if [[ -n "$NEW_IP" ]] && [[ "$NEW_IP" != 169.254.* ]]; then
    SUCCESS="true"
    CURRENT_STATE="has_valid_ip"
elif [[ "$NEW_IP" == 169.254.* ]]; then
    CURRENT_STATE="apipa"
else
    CURRENT_STATE="no_ip"
fi

# Build suggestions
SUGGESTIONS=()
if [[ "$SUCCESS" == "true" ]]; then
    SUGGESTIONS+=("DHCP lease renewed successfully")
    [[ "$NEW_IP" != "$PREV_IP" ]] && SUGGESTIONS+=("IP changed from $PREV_IP to $NEW_IP")
    [[ "$NEW_IP" == "$PREV_IP" ]] && SUGGESTIONS+=("IP address: $NEW_IP (unchanged)")
    [[ -n "$GATEWAY" ]] && SUGGESTIONS+=("Gateway: $GATEWAY")
elif [[ "$CURRENT_STATE" == "apipa" ]]; then
    SUGGESTIONS+=("Obtained APIPA address (169.254.x.x) - DHCP server unreachable")
    SUGGESTIONS+=("Check physical network connection")
    SUGGESTIONS+=("Verify DHCP server is running on network")
else
    SUGGESTIONS+=("DHCP renewal failed")
    SUGGESTIONS+=("Check network connection")
    SUGGESTIONS+=("Try: sudo dhclient $INTERFACE")
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

data=$(cat <<EOF
{
    "interface": "$INTERFACE",
    "previous_ip": $(if [[ -n "$PREV_IP" ]]; then echo "\"$PREV_IP\""; else echo "null"; fi),
    "current_ip": $(if [[ -n "$NEW_IP" ]]; then echo "\"$NEW_IP\""; else echo "null"; fi),
    "gateway": $(if [[ -n "$GATEWAY" ]]; then echo "\"$GATEWAY\""; else echo "null"; fi),
    "current_state": "$CURRENT_STATE",
    "method": "$METHOD",
    "success": $SUCCESS
}
EOF
)

output_success "$data" "$suggestions_json"
