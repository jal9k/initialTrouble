#!/usr/bin/env bash
# get_ip_config.sh - Get IP configuration on macOS
# Usage: ./get_ip_config.sh [interface_name]

source "$(dirname "$0")/common.sh"

# Handle test mode
if is_test_mode "$1"; then
    output_test_response "get_ip_config"
    exit 0
fi

INTERFACE="${1:-}"

# Get interface info
IFCONFIG_OUTPUT=$(ifconfig 2>&1) || {
    output_failure "Failed to get network configuration" '["Check if ifconfig command is available"]'
    exit 1
}

# Get default gateway
GATEWAY=$(netstat -nr 2>/dev/null | grep -E "^default|^0\.0\.0\.0" | head -1 | awk '{print $2}')

# Get DNS servers
DNS_SERVERS=()
while IFS= read -r line; do
    if [[ $line =~ nameserver.*:\ ([0-9.]+) ]]; then
        DNS_SERVERS+=("${BASH_REMATCH[1]}")
    fi
done < <(scutil --dns 2>/dev/null | grep -E "nameserver\[")

# Parse interfaces
declare -a INTERFACES_JSON=()
HAS_VALID_IP="false"
HAS_GATEWAY="false"
PRIMARY_IP=""

[[ -n "$GATEWAY" ]] && HAS_GATEWAY="true"

current_iface=""
current_ip=""
current_mask=""
current_ipv6=""
is_apipa="false"

# Build DNS array JSON
dns_json="["
first=true
for dns in "${DNS_SERVERS[@]}"; do
    [[ "$first" != "true" ]] && dns_json+=","
    dns_json+="\"$dns\""
    first=false
done
dns_json+="]"

while IFS= read -r line; do
    # New interface
    if [[ $line =~ ^([a-z0-9]+): ]]; then
        # Save previous interface
        if [[ -n "$current_iface" ]] && [[ -n "$current_ip" ]]; then
            if [[ -z "$INTERFACE" ]] || [[ "$current_iface" == "$INTERFACE" ]]; then
                iface_json=$(cat <<EOF
{
    "interface": "$current_iface",
    "ip_address": "$current_ip",
    "subnet_mask": $(if [[ -n "$current_mask" ]]; then echo "\"$current_mask\""; else echo "null"; fi),
    "gateway": $(if [[ -n "$GATEWAY" ]]; then echo "\"$GATEWAY\""; else echo "null"; fi),
    "dns_servers": $dns_json,
    "dhcp_enabled": true,
    "is_apipa": $is_apipa,
    "ipv6_address": $(if [[ -n "$current_ipv6" ]]; then echo "\"$current_ipv6\""; else echo "null"; fi)
}
EOF
)
                INTERFACES_JSON+=("$iface_json")
                
                [[ "$is_apipa" == "false" ]] && HAS_VALID_IP="true" && [[ -z "$PRIMARY_IP" ]] && PRIMARY_IP="$current_ip"
            fi
        fi
        
        current_iface="${BASH_REMATCH[1]}"
        current_ip=""
        current_mask=""
        current_ipv6=""
        is_apipa="false"
    elif [[ -n "$current_iface" ]]; then
        # Parse inet line
        if [[ $line =~ inet\ ([0-9.]+) ]]; then
            current_ip="${BASH_REMATCH[1]}"
            [[ "$current_ip" == 169.254.* ]] && is_apipa="true"
            
            # Parse netmask (hex format on macOS)
            if [[ $line =~ netmask\ (0x[0-9a-f]+) ]]; then
                hex="${BASH_REMATCH[1]}"
                # Convert hex to dotted decimal
                hex="${hex#0x}"
                o1=$((16#${hex:0:2}))
                o2=$((16#${hex:2:2}))
                o3=$((16#${hex:4:2}))
                o4=$((16#${hex:6:2}))
                current_mask="$o1.$o2.$o3.$o4"
            fi
        elif [[ $line =~ inet6\ ([0-9a-f:]+) ]] && [[ ! $line =~ fe80:: ]]; then
            ipv6="${BASH_REMATCH[1]}"
            current_ipv6="${ipv6%%\%*}"
        fi
    fi
done <<< "$IFCONFIG_OUTPUT"

# Don't forget last interface
if [[ -n "$current_iface" ]] && [[ -n "$current_ip" ]]; then
    if [[ -z "$INTERFACE" ]] || [[ "$current_iface" == "$INTERFACE" ]]; then
        iface_json=$(cat <<EOF
{
    "interface": "$current_iface",
    "ip_address": "$current_ip",
    "subnet_mask": $(if [[ -n "$current_mask" ]]; then echo "\"$current_mask\""; else echo "null"; fi),
    "gateway": $(if [[ -n "$GATEWAY" ]]; then echo "\"$GATEWAY\""; else echo "null"; fi),
    "dns_servers": $dns_json,
    "dhcp_enabled": true,
    "is_apipa": $is_apipa,
    "ipv6_address": $(if [[ -n "$current_ipv6" ]]; then echo "\"$current_ipv6\""; else echo "null"; fi)
}
EOF
)
        INTERFACES_JSON+=("$iface_json")
        
        [[ "$is_apipa" == "false" ]] && HAS_VALID_IP="true" && [[ -z "$PRIMARY_IP" ]] && PRIMARY_IP="$current_ip"
    fi
fi

# Build interfaces array JSON
interfaces_array="["
first=true
for iface in "${INTERFACES_JSON[@]}"; do
    [[ "$first" != "true" ]] && interfaces_array+=","
    interfaces_array+="$iface"
    first=false
done
interfaces_array+="]"

# Build suggestions
SUGGESTIONS=()
if [[ "$HAS_VALID_IP" == "false" ]]; then
    # Check for APIPA
    has_apipa="false"
    for iface in "${INTERFACES_JSON[@]}"; do
        [[ "$iface" == *'"is_apipa": true'* ]] && has_apipa="true" && break
    done
    
    if [[ "$has_apipa" == "true" ]]; then
        SUGGESTIONS+=("APIPA address detected (169.254.x.x) - DHCP server is unreachable")
        SUGGESTIONS+=("Check physical network connection")
        SUGGESTIONS+=("Verify DHCP server is running on the network")
    else
        SUGGESTIONS+=("No IP address assigned to interface")
        SUGGESTIONS+=("Run check_adapter_status to verify adapter is connected")
    fi
elif [[ "$HAS_GATEWAY" == "false" ]]; then
    SUGGESTIONS+=("No default gateway configured")
    SUGGESTIONS+=("Check DHCP configuration or set static gateway")
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

# Build final data
data=$(cat <<EOF
{
    "interfaces": ${interfaces_array},
    "has_valid_ip": ${HAS_VALID_IP},
    "has_gateway": ${HAS_GATEWAY},
    "primary_ip": $(if [[ -n "$PRIMARY_IP" ]]; then echo "\"$PRIMARY_IP\""; else echo "null"; fi),
    "primary_gateway": $(if [[ -n "$GATEWAY" ]]; then echo "\"$GATEWAY\""; else echo "null"; fi)
}
EOF
)

output_success "$data" "$suggestions_json"
