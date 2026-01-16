#!/usr/bin/env bash
# test_vpn_connectivity.sh - Test VPN connection status on Linux
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

# Method 1: Check for VPN interfaces (tun, tap, wg)
for pattern in tun tap wg ppp; do
    iface=$(ip link show 2>/dev/null | grep -oP "(?<=: )${pattern}[0-9]+(?=:)" | head -1)
    if [[ -n "$iface" ]]; then
        # Check if interface has IP
        iface_ip=$(ip -4 addr show "$iface" 2>/dev/null | grep -oP '(?<=inet )[\d.]+')
        if [[ -n "$iface_ip" ]]; then
            VPN_CONNECTED="true"
            VPN_INTERFACE="$iface"
            
            # Guess type from interface
            case "$pattern" in
                tun) DETECTED_TYPE="openvpn" ;;
                tap) DETECTED_TYPE="openvpn_tap" ;;
                wg) DETECTED_TYPE="wireguard" ;;
                ppp) DETECTED_TYPE="pptp_or_l2tp" ;;
            esac
            break
        fi
    fi
done

# Method 2: Check for WireGuard using wg tool
if [[ "$VPN_CONNECTED" == "false" ]] && command -v wg &>/dev/null; then
    wg_interfaces=$(wg show interfaces 2>/dev/null)
    if [[ -n "$wg_interfaces" ]]; then
        for iface in $wg_interfaces; do
            iface_ip=$(ip -4 addr show "$iface" 2>/dev/null | grep -oP '(?<=inet )[\d.]+')
            if [[ -n "$iface_ip" ]]; then
                VPN_CONNECTED="true"
                VPN_INTERFACE="$iface"
                DETECTED_TYPE="wireguard"
                DETECTION_METHOD="wg_tool"
                break
            fi
        done
    fi
fi

# Method 3: Check NetworkManager for VPN
if [[ "$VPN_CONNECTED" == "false" ]] && command -v nmcli &>/dev/null; then
    nm_vpn=$(nmcli -t -f NAME,TYPE,STATE connection show --active 2>/dev/null | grep "vpn.*activated")
    if [[ -n "$nm_vpn" ]]; then
        VPN_CONNECTED="true"
        VPN_INTERFACE=$(echo "$nm_vpn" | cut -d: -f1)
        DETECTED_TYPE="networkmanager_vpn"
        DETECTION_METHOD="nmcli"
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
if [[ -n "$VPN_INTERFACE" ]]; then
    VPN_IP=$(ip -4 addr show "$VPN_INTERFACE" 2>/dev/null | grep -oP '(?<=inet )[\d.]+' | head -1)
fi

# Check VPN routes
ROUTES_ACTIVE="false"
route_output=$(ip route 2>/dev/null)
if [[ "$route_output" =~ (10\.|172\.1[6-9]\.|172\.2[0-9]\.|172\.3[01]\.|192\.168\.|0\.0\.0\.0/1|128\.0\.0\.0/1) ]]; then
    ROUTES_ACTIVE="true"
fi

# Check DNS via VPN
DNS_VIA_VPN="false"
if [[ -f /etc/resolv.conf ]]; then
    dns_servers=$(grep "^nameserver" /etc/resolv.conf | awk '{print $2}')
    for dns in $dns_servers; do
        if [[ "$dns" =~ ^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.) ]]; then
            DNS_VIA_VPN="true"
            break
        fi
    done
fi

# Test internal endpoint if provided
INTERNAL_REACHABLE="null"
if [[ -n "$TEST_ENDPOINT" ]]; then
    if ping -c 1 -W 3 "$TEST_ENDPOINT" &>/dev/null; then
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
