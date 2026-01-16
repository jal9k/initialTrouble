#!/usr/bin/env bash
# test_vpn_connectivity.sh - Test VPN connection status on macOS
# Usage: ./test_vpn_connectivity.sh [vpn_type] [test_endpoint]

source "$(dirname "$0")/common.sh"

# Handle test mode
if is_test_mode "$1"; then
    output_test_response "test_vpn_connectivity"
    exit 0
fi

VPN_TYPE="${1:-}"
TEST_ENDPOINT="${2:-}"

# Detect VPN connection
VPN_CONNECTED="false"
VPN_INTERFACE=""
DETECTED_TYPE="unknown"
DETECTION_METHOD="interface_scan"

# Method 1: Check for VPN interfaces (utun, ipsec, ppp)
interfaces=$(ifconfig -l 2>/dev/null)
for iface in $interfaces; do
    if [[ "$iface" =~ ^(utun|ipsec|ppp)[0-9]+ ]]; then
        # Check if interface has IP
        iface_info=$(ifconfig "$iface" 2>/dev/null)
        if [[ "$iface_info" == *"inet "* ]]; then
            VPN_CONNECTED="true"
            VPN_INTERFACE="$iface"
            
            # Guess type from interface
            if [[ "$iface" == utun* ]]; then
                DETECTED_TYPE="wireguard_or_openvpn"
            elif [[ "$iface" == ipsec* ]]; then
                DETECTED_TYPE="ipsec"
            elif [[ "$iface" == ppp* ]]; then
                DETECTED_TYPE="pptp_or_l2tp"
            fi
            break
        fi
    fi
done

# Method 2: Check scutil for VPN connections
if [[ "$VPN_CONNECTED" == "false" ]]; then
    scutil_output=$(scutil --nc list 2>/dev/null)
    if [[ "$scutil_output" == *"Connected"* ]]; then
        VPN_CONNECTED="true"
        VPN_INTERFACE="scutil_vpn"
        DETECTED_TYPE="system_vpn"
        DETECTION_METHOD="scutil"
    fi
fi

# If no VPN detected
if [[ "$VPN_CONNECTED" == "false" ]]; then
    data=$(cat <<EOF
{
    "vpn_connected": false,
    "vpn_type": null,
    "vpn_interface": null,
    "vpn_ip": null,
    "routes_active": false,
    "dns_via_vpn": false,
    "internal_reachable": null,
    "detection_method": "$DETECTION_METHOD"
}
EOF
)
    suggestions=$(to_json_array "No active VPN connection detected" "Connect to your VPN and try again" "Check VPN client application is running")
    output_success "$data" "$suggestions"
    exit 0
fi

# Get VPN IP address
VPN_IP=""
if [[ -n "$VPN_INTERFACE" ]] && [[ "$VPN_INTERFACE" != "scutil_vpn" ]]; then
    VPN_IP=$(ifconfig "$VPN_INTERFACE" 2>/dev/null | grep "inet " | awk '{print $2}')
fi

# Check VPN routes
ROUTES_ACTIVE="false"
route_output=$(netstat -rn 2>/dev/null)
if [[ "$route_output" =~ (10\.|172\.1[6-9]\.|172\.2[0-9]\.|172\.3[01]\.|192\.168\.|0\.0\.0\.0/1|128\.0\.0\.0/1) ]]; then
    ROUTES_ACTIVE="true"
fi

# Check DNS via VPN
DNS_VIA_VPN="false"
dns_output=$(scutil --dns 2>/dev/null)
if [[ "$dns_output" =~ (10\.[0-9]+\.[0-9]+\.[0-9]+|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]+\.[0-9]+|192\.168\.[0-9]+\.[0-9]+) ]]; then
    DNS_VIA_VPN="true"
fi

# Test internal endpoint if provided
INTERNAL_REACHABLE="null"
if [[ -n "$TEST_ENDPOINT" ]]; then
    ping_result=$(ping -c 1 -W 3 "$TEST_ENDPOINT" 2>&1)
    if [[ "$ping_result" == *"1 packets received"* ]] || [[ "$ping_result" == *"1 received"* ]]; then
        INTERNAL_REACHABLE="true"
    else
        INTERNAL_REACHABLE="false"
    fi
fi

# Use provided VPN type if given
[[ -n "$VPN_TYPE" ]] && DETECTED_TYPE="$VPN_TYPE"

# Build suggestions
SUGGESTIONS=()
[[ -n "$VPN_IP" ]] && SUGGESTIONS+=("VPN connected with IP: $VPN_IP")
[[ "$ROUTES_ACTIVE" == "false" ]] && SUGGESTIONS+=("VPN routes may not be configured. Check VPN client settings.")
[[ "$DNS_VIA_VPN" == "false" ]] && SUGGESTIONS+=("DNS does not appear to go through VPN. This may cause DNS leaks.")
if [[ "$INTERNAL_REACHABLE" == "false" ]]; then
    SUGGESTIONS+=("Cannot reach internal endpoint $TEST_ENDPOINT. Check VPN routing.")
elif [[ "$INTERNAL_REACHABLE" == "true" ]]; then
    SUGGESTIONS+=("Successfully reached internal endpoint: $TEST_ENDPOINT")
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

data=$(cat <<EOF
{
    "vpn_connected": true,
    "vpn_type": "$DETECTED_TYPE",
    "vpn_interface": "$VPN_INTERFACE",
    "vpn_ip": $(if [[ -n "$VPN_IP" ]]; then echo "\"$VPN_IP\""; else echo "null"; fi),
    "routes_active": $ROUTES_ACTIVE,
    "dns_via_vpn": $DNS_VIA_VPN,
    "internal_reachable": $INTERNAL_REACHABLE,
    "detection_method": "$DETECTION_METHOD"
}
EOF
)

output_success "$data" "$suggestions_json"
