#!/usr/bin/env bash
# ping_gateway.sh - Ping the default gateway on macOS
# Usage: ./ping_gateway.sh [gateway_ip] [count]

source "$(dirname "$0")/common.sh"

# Handle test mode
if is_test_mode "$1"; then
    output_test_response "ping_gateway"
    exit 0
fi

GATEWAY="${1:-}"
COUNT="${2:-4}"

# Auto-detect gateway if not provided
if [[ -z "$GATEWAY" ]]; then
    GATEWAY=$(get_default_gateway)
fi

if [[ -z "$GATEWAY" ]]; then
    output_failure "Could not determine default gateway" '["Run get_ip_config to check network configuration", "Verify network cable or WiFi connection"]'
    exit 1
fi

# Run ping
PING_OUTPUT=$(ping -c "$COUNT" -W 5 "$GATEWAY" 2>&1) || true

# Parse ping results
PACKETS_SENT=0
PACKETS_RECEIVED=0
MIN_TIME=""
AVG_TIME=""
MAX_TIME=""
declare -a RESULTS=()

while IFS= read -r line; do
    # Parse individual ping responses
    if [[ $line =~ ([0-9]+)\ bytes\ from.*icmp_seq=([0-9]+).*time=([0-9.]+) ]]; then
        seq="${BASH_REMATCH[2]}"
        time="${BASH_REMATCH[3]}"
        RESULTS+=("{\"sequence\":$seq,\"success\":true,\"time_ms\":$time}")
    elif [[ $line =~ "Request timeout" ]] || [[ $line =~ "request timed out" ]]; then
        seq=${#RESULTS[@]}
        RESULTS+=("{\"sequence\":$seq,\"success\":false,\"time_ms\":null}")
    # Parse summary line
    elif [[ $line =~ ([0-9]+)\ packets\ transmitted,\ ([0-9]+)\ .*received ]]; then
        PACKETS_SENT="${BASH_REMATCH[1]}"
        PACKETS_RECEIVED="${BASH_REMATCH[2]}"
    # Parse statistics
    elif [[ $line =~ min/avg/max.*=\ ([0-9.]+)/([0-9.]+)/([0-9.]+) ]]; then
        MIN_TIME="${BASH_REMATCH[1]}"
        AVG_TIME="${BASH_REMATCH[2]}"
        MAX_TIME="${BASH_REMATCH[3]}"
    fi
done <<< "$PING_OUTPUT"

# Calculate packet loss
if [[ $PACKETS_SENT -eq 0 ]]; then
    PACKETS_SENT=${#RESULTS[@]}
    PACKETS_RECEIVED=0
    for r in "${RESULTS[@]}"; do
        [[ "$r" == *'"success":true'* ]] && ((PACKETS_RECEIVED++))
    done
fi

if [[ $PACKETS_SENT -gt 0 ]]; then
    PACKET_LOSS=$(awk "BEGIN {printf \"%.1f\", (($PACKETS_SENT - $PACKETS_RECEIVED) / $PACKETS_SENT) * 100}")
else
    PACKET_LOSS="100.0"
fi

REACHABLE="false"
[[ $PACKETS_RECEIVED -gt 0 ]] && REACHABLE="true"

# Build results array
results_json="["
first=true
for r in "${RESULTS[@]}"; do
    [[ "$first" != "true" ]] && results_json+=","
    results_json+="$r"
    first=false
done
results_json+="]"

# Build suggestions
SUGGESTIONS=()
if [[ "$REACHABLE" == "false" ]]; then
    SUGGESTIONS+=("Gateway is not responding")
    SUGGESTIONS+=("Check if router/modem is powered on")
    SUGGESTIONS+=("Verify Ethernet cable is connected or WiFi is associated")
    SUGGESTIONS+=("Try restarting the router")
    SUGGESTIONS+=("Check if gateway IP is correct: $GATEWAY")
elif [[ $(echo "$PACKET_LOSS > 0" | bc -l) -eq 1 ]]; then
    SUGGESTIONS+=("Intermittent connectivity (${PACKET_LOSS}% packet loss)")
    SUGGESTIONS+=("Check WiFi signal strength if on wireless")
    SUGGESTIONS+=("Try a different Ethernet cable if wired")
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

# Build final data
data=$(cat <<EOF
{
    "gateway_ip": "$GATEWAY",
    "reachable": $REACHABLE,
    "packets_sent": $PACKETS_SENT,
    "packets_received": $PACKETS_RECEIVED,
    "packet_loss_percent": $PACKET_LOSS,
    "min_time_ms": $(if [[ -n "$MIN_TIME" ]]; then echo "$MIN_TIME"; else echo "null"; fi),
    "avg_time_ms": $(if [[ -n "$AVG_TIME" ]]; then echo "$AVG_TIME"; else echo "null"; fi),
    "max_time_ms": $(if [[ -n "$MAX_TIME" ]]; then echo "$MAX_TIME"; else echo "null"; fi),
    "results": $results_json
}
EOF
)

output_success "$data" "$suggestions_json"
