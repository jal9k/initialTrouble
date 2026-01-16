#!/usr/bin/env bash
# check_adapter_status.sh - Check network adapter status on Linux
# Usage: ./check_adapter_status.sh [interface_name]

source "$(dirname "$0")/common.sh"

# Handle test mode
if is_test_mode "$1"; then
    output_test_response "check_adapter_status"
    exit 0
fi

INTERFACE="${1:-}"

# Get all network interfaces using ip command
IP_OUTPUT=$(ip -o link show 2>&1) || {
    output_failure "Failed to get network interfaces" '["Check if ip command is available"]'
    exit 1
}

declare -a ADAPTER_JSON=()
ACTIVE_COUNT=0
CONNECTED_COUNT=0
PRIMARY_INTERFACE=""

while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    
    # Parse: "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 ..."
    if [[ $line =~ ^[0-9]+:\ ([^:@]+)(@[^:]+)?:\ \<([^>]*)\> ]]; then
        iface_name="${BASH_REMATCH[1]}"
        flags="${BASH_REMATCH[3]}"
        
        # Skip if filtering for specific interface
        if [[ -n "$INTERFACE" ]] && [[ "$iface_name" != "$INTERFACE" ]]; then
            continue
        fi
        
        # Determine type
        iface_type="other"
        case "$iface_name" in
            lo) iface_type="loopback" ;;
            eth*|enp*|ens*) iface_type="ethernet" ;;
            wlan*|wlp*) iface_type="wireless" ;;
            docker*|br-*|veth*|virbr*) iface_type="virtual" ;;
        esac
        
        # Skip virtual and loopback for main stats
        [[ "$iface_type" == "virtual" ]] && continue
        
        # Parse status from flags
        status="down"
        is_connected="false"
        [[ "$flags" == *"UP"* ]] && status="up"
        [[ "$flags" == *"LOWER_UP"* ]] && is_connected="true"
        
        # Get MAC address
        mac_address="null"
        if [[ $line =~ link/ether\ ([0-9a-f:]+) ]]; then
            mac_address="\"${BASH_REMATCH[1]}\""
        fi
        
        # Check if interface has IP
        has_ip="false"
        ip_check=$(ip -4 addr show "$iface_name" 2>/dev/null | grep -c "inet ") || true
        [[ $ip_check -gt 0 ]] && has_ip="true"
        
        # Build adapter JSON
        adapter_json=$(cat <<EOF
{
    "name": "$iface_name",
    "display_name": "$iface_name",
    "status": "$status",
    "type": "$iface_type",
    "mac_address": $mac_address,
    "has_ip": $has_ip,
    "is_connected": $is_connected
}
EOF
)
        ADAPTER_JSON+=("$adapter_json")
        
        # Count stats (exclude loopback)
        if [[ "$iface_type" != "loopback" ]]; then
            [[ "$status" == "up" ]] && ((ACTIVE_COUNT++))
            [[ "$is_connected" == "true" ]] && ((CONNECTED_COUNT++))
            [[ "$has_ip" == "true" ]] && [[ "$is_connected" == "true" ]] && [[ -z "$PRIMARY_INTERFACE" ]] && PRIMARY_INTERFACE="$iface_name"
        fi
    fi
done <<< "$IP_OUTPUT"

# Build adapters array JSON
adapters_array="["
first=true
for adapter in "${ADAPTER_JSON[@]}"; do
    [[ "$first" != "true" ]] && adapters_array+=","
    adapters_array+="$adapter"
    first=false
done
adapters_array+="]"

# Determine network connectivity
HAS_NETWORK_CONNECTION="false"
[[ $CONNECTED_COUNT -gt 0 ]] && HAS_NETWORK_CONNECTION="true"

# Build suggestions
SUGGESTIONS=()
if [[ $ACTIVE_COUNT -eq 0 ]]; then
    SUGGESTIONS+=("All network adapters are disabled")
    SUGGESTIONS+=("ACTION: Call enable_wifi to enable the WiFi adapter")
    SUGGESTIONS+=("Enable a network adapter using: ip link set <interface> up")
elif [[ $CONNECTED_COUNT -eq 0 ]]; then
    SUGGESTIONS+=("CRITICAL: No network adapters are connected to any network")
    SUGGESTIONS+=("ACTION: Call enable_wifi to enable WiFi and attempt connection")
    SUGGESTIONS+=("Check network cable or WiFi connection")
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

# Build final data object
data=$(cat <<EOF
{
    "adapters": ${adapters_array},
    "active_count": ${ACTIVE_COUNT},
    "connected_count": ${CONNECTED_COUNT},
    "has_network_connection": ${HAS_NETWORK_CONNECTION},
    "primary_interface": $(if [[ -n "$PRIMARY_INTERFACE" ]]; then echo "\"$PRIMARY_INTERFACE\""; else echo "null"; fi)
}
EOF
)

output_success "$data" "$suggestions_json"
