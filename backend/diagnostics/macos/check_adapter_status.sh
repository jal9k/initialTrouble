#!/usr/bin/env bash
# check_adapter_status.sh - Check network adapter status on macOS
# Usage: ./check_adapter_status.sh [interface_name]

source "$(dirname "$0")/common.sh"

# Handle test mode
if is_test_mode "$1"; then
    output_test_response "check_adapter_status"
    exit 0
fi

INTERFACE="${1:-}"

# Get all network interfaces
IFCONFIG_OUTPUT=$(ifconfig -a 2>&1) || {
    output_failure "Failed to get network interfaces" '["Check if ifconfig command is available"]'
    exit 1
}

# Parse adapters
declare -a ADAPTERS=()
declare -a ADAPTER_JSON=()
ACTIVE_COUNT=0
CONNECTED_COUNT=0
PRIMARY_INTERFACE=""

current_name=""
current_status="down"
current_type="other"
current_mac=""
current_has_ip="false"
current_is_connected="false"

while IFS= read -r line; do
    # New interface starts with name at beginning of line
    if [[ $line =~ ^([a-z0-9]+): ]]; then
        # Save previous interface if exists and not filtered out
        if [[ -n "$current_name" ]] && [[ "$current_type" != "virtual" ]] && [[ "$current_type" != "loopback" || "$current_has_ip" == "true" ]]; then
            if [[ -z "$INTERFACE" ]] || [[ "$current_name" == "$INTERFACE" ]]; then
                adapter_json=$(to_json_object \
                    "name" "$current_name" \
                    "status" "$current_status" \
                    "type" "$current_type" \
                    "mac_address" "${current_mac:-null}" \
                    "has_ip" "$current_has_ip" \
                    "is_connected" "$current_is_connected")
                ADAPTER_JSON+=("$adapter_json")
                
                # Count stats (exclude loopback)
                if [[ "$current_type" != "loopback" ]]; then
                    [[ "$current_status" == "up" ]] && ((ACTIVE_COUNT++))
                    [[ "$current_is_connected" == "true" ]] && ((CONNECTED_COUNT++))
                    [[ "$current_has_ip" == "true" ]] && [[ "$current_is_connected" == "true" ]] && [[ -z "$PRIMARY_INTERFACE" ]] && PRIMARY_INTERFACE="$current_name"
                fi
            fi
        fi
        
        # Start new interface
        current_name="${BASH_REMATCH[1]}"
        current_status="down"
        current_type="other"
        current_mac=""
        current_has_ip="false"
        current_is_connected="false"
        
        # Parse flags
        if [[ $line =~ \<([^>]+)\> ]]; then
            flags="${BASH_REMATCH[1]}"
            [[ $flags == *"UP"* ]] && current_status="up"
            [[ $flags == *"RUNNING"* ]] && current_is_connected="true"
        fi
        
        # Determine type
        case "$current_name" in
            lo0) current_type="loopback" ;;
            en*) current_type="ethernet" ;;
            utun*|bridge*|awdl*|llw*) current_type="virtual" ;;
        esac
    elif [[ -n "$current_name" ]]; then
        # Parse interface details
        if [[ $line =~ ether\ ([0-9a-f:]+) ]]; then
            current_mac="${BASH_REMATCH[1]}"
        elif [[ $line =~ inet\ ([0-9.]+) ]]; then
            current_has_ip="true"
        elif [[ $line =~ status:\ (.+) ]]; then
            [[ "${BASH_REMATCH[1]}" == "active" ]] && current_is_connected="true"
        fi
    fi
done <<< "$IFCONFIG_OUTPUT"

# Don't forget last interface
if [[ -n "$current_name" ]] && [[ "$current_type" != "virtual" ]] && [[ "$current_type" != "loopback" || "$current_has_ip" == "true" ]]; then
    if [[ -z "$INTERFACE" ]] || [[ "$current_name" == "$INTERFACE" ]]; then
        adapter_json=$(to_json_object \
            "name" "$current_name" \
            "status" "$current_status" \
            "type" "$current_type" \
            "mac_address" "${current_mac:-null}" \
            "has_ip" "$current_has_ip" \
            "is_connected" "$current_is_connected")
        ADAPTER_JSON+=("$adapter_json")
        
        if [[ "$current_type" != "loopback" ]]; then
            [[ "$current_status" == "up" ]] && ((ACTIVE_COUNT++))
            [[ "$current_is_connected" == "true" ]] && ((CONNECTED_COUNT++))
            [[ "$current_has_ip" == "true" ]] && [[ "$current_is_connected" == "true" ]] && [[ -z "$PRIMARY_INTERFACE" ]] && PRIMARY_INTERFACE="$current_name"
        fi
    fi
fi

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
    SUGGESTIONS+=("Enable a network adapter in System Preferences > Network")
elif [[ $CONNECTED_COUNT -eq 0 ]]; then
    SUGGESTIONS+=("CRITICAL: No network adapters are connected to any network")
    SUGGESTIONS+=("ACTION: Call enable_wifi to enable WiFi and attempt connection")
    SUGGESTIONS+=("WiFi may be turned off or not connected to a network")
    SUGGESTIONS+=("If WiFi is already on, user needs to manually select a network")
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
