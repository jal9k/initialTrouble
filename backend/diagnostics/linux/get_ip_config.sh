#!/usr/bin/env bash
# get_ip_config.sh - Get IP configuration on Linux
# Usage: ./get_ip_config.sh [interface_name]

source "$(dirname "$0")/common.sh"

# Handle test mode
if is_test_mode "$1"; then
    output_test_response "get_ip_config"
    exit 0
fi

INTERFACE="${1:-}"

# Get default gateway
GATEWAY=$(get_default_gateway)

# Get DNS servers from /etc/resolv.conf
DNS_SERVERS=()
if [[ -f /etc/resolv.conf ]]; then
    while IFS= read -r line; do
        if [[ $line =~ ^nameserver\ +([0-9.]+) ]]; then
            DNS_SERVERS+=("${BASH_REMATCH[1]}")
        fi
    done < /etc/resolv.conf
fi

# Build DNS array JSON
dns_json="["
first=true
for dns in "${DNS_SERVERS[@]}"; do
    [[ "$first" != "true" ]] && dns_json+=","
    dns_json+="\"$dns\""
    first=false
done
dns_json+="]"

# Get interfaces with IP addresses
declare -a INTERFACES_JSON=()
HAS_VALID_IP="false"
HAS_GATEWAY="false"
PRIMARY_IP=""

[[ -n "$GATEWAY" ]] && HAS_GATEWAY="true"

# Get all interfaces with addresses
while IFS= read -r iface_name; do
    [[ -z "$iface_name" ]] && continue
    [[ "$iface_name" == "lo" ]] && continue  # Skip loopback
    
    # Filter if specific interface requested
    if [[ -n "$INTERFACE" ]] && [[ "$iface_name" != "$INTERFACE" ]]; then
        continue
    fi
    
    # Get IP address
    ip_info=$(ip -4 addr show "$iface_name" 2>/dev/null | grep "inet ")
    [[ -z "$ip_info" ]] && continue
    
    # Parse IP and subnet
    if [[ $ip_info =~ inet\ ([0-9.]+)/([0-9]+) ]]; then
        ip_address="${BASH_REMATCH[1]}"
        prefix="${BASH_REMATCH[2]}"
        
        # Convert prefix to subnet mask
        subnet_mask=$(python3 -c "import ipaddress; print(ipaddress.IPv4Network('0.0.0.0/$prefix', strict=False).netmask)" 2>/dev/null || echo "")
        
        # Check for APIPA
        is_apipa="false"
        [[ "$ip_address" == 169.254.* ]] && is_apipa="true"
        
        # Get IPv6 address
        ipv6_address=""
        ipv6_info=$(ip -6 addr show "$iface_name" 2>/dev/null | grep "inet6 " | grep -v "fe80::" | head -1)
        if [[ $ipv6_info =~ inet6\ ([0-9a-f:]+) ]]; then
            ipv6_address="${BASH_REMATCH[1]}"
        fi
        
        # Build interface JSON
        iface_json=$(cat <<EOF
{
    "interface": "$iface_name",
    "ip_address": "$ip_address",
    "subnet_mask": $(if [[ -n "$subnet_mask" ]]; then echo "\"$subnet_mask\""; else echo "null"; fi),
    "gateway": $(if [[ -n "$GATEWAY" ]]; then echo "\"$GATEWAY\""; else echo "null"; fi),
    "dns_servers": $dns_json,
    "dhcp_enabled": true,
    "is_apipa": $is_apipa,
    "ipv6_address": $(if [[ -n "$ipv6_address" ]]; then echo "\"$ipv6_address\""; else echo "null"; fi)
}
EOF
)
        INTERFACES_JSON+=("$iface_json")
        
        [[ "$is_apipa" == "false" ]] && HAS_VALID_IP="true" && [[ -z "$PRIMARY_IP" ]] && PRIMARY_IP="$ip_address"
    fi
done < <(ip -o link show | awk -F': ' '{print $2}' | cut -d'@' -f1)

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
