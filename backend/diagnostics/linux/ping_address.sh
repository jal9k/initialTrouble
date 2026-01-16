#!/usr/bin/env bash
# ping_address.sh - Ping any specified address on Linux
# Usage: ./ping_address.sh <host> [count]

source "$(dirname "$0")/common.sh"

# Handle test mode
if is_test_mode "$1"; then
    output_test_response "ping_address"
    exit 0
fi

HOST="${1:-}"
COUNT="${2:-4}"

if [[ -z "$HOST" ]]; then
    output_failure "Host address is required" '["Provide an IP address or hostname to ping"]'
    exit 1
fi

# Run ping
PING_OUTPUT=$(ping -c "$COUNT" -W 5 "$HOST" 2>&1) || true

# Parse ping results
PACKETS_SENT=0
PACKETS_RECEIVED=0
MIN_TIME=""
AVG_TIME=""
MAX_TIME=""
declare -a RESULTS=()

while IFS= read -r line; do
    if [[ $line =~ ([0-9]+)\ bytes\ from.*icmp_seq=([0-9]+).*time=([0-9.]+) ]]; then
        seq="${BASH_REMATCH[2]}"
        time="${BASH_REMATCH[3]}"
        RESULTS+=("{\"sequence\":$seq,\"success\":true,\"time_ms\":$time}")
    elif [[ $line =~ "Request timeout" ]] || [[ $line =~ "request timed out" ]]; then
        seq=${#RESULTS[@]}
        RESULTS+=("{\"sequence\":$seq,\"success\":false,\"time_ms\":null}")
    elif [[ $line =~ ([0-9]+)\ packets\ transmitted,\ ([0-9]+)\ received ]]; then
        PACKETS_SENT="${BASH_REMATCH[1]}"
        PACKETS_RECEIVED="${BASH_REMATCH[2]}"
    elif [[ $line =~ rtt\ min/avg/max/mdev\ =\ ([0-9.]+)/([0-9.]+)/([0-9.]+) ]]; then
        MIN_TIME="${BASH_REMATCH[1]}"
        AVG_TIME="${BASH_REMATCH[2]}"
        MAX_TIME="${BASH_REMATCH[3]}"
    fi
done <<< "$PING_OUTPUT"

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

results_json="["
first=true
for r in "${RESULTS[@]}"; do
    [[ "$first" != "true" ]] && results_json+=","
    results_json+="$r"
    first=false
done
results_json+="]"

SUGGESTIONS=()
if [[ "$REACHABLE" == "false" ]]; then
    SUGGESTIONS+=("Host '$HOST' is not responding to ping")
    SUGGESTIONS+=("Verify the hostname or IP address is correct")
    SUGGESTIONS+=("The host may be blocking ICMP ping requests")
    SUGGESTIONS+=("Check if you have internet connectivity (run ping_dns)")
    SUGGESTIONS+=("If this is a website, try test_dns_resolution instead")
elif [[ $(echo "$PACKET_LOSS > 0" | bc -l 2>/dev/null || echo "0") -eq 1 ]]; then
    SUGGESTIONS+=("Intermittent connectivity to $HOST (${PACKET_LOSS}% packet loss)")
    SUGGESTIONS+=("Network congestion or unstable connection detected")
    SUGGESTIONS+=("Consider running traceroute to identify the problem hop")
elif [[ -n "$AVG_TIME" ]] && [[ $(echo "$AVG_TIME > 200" | bc -l 2>/dev/null || echo "0") -eq 1 ]]; then
    SUGGESTIONS+=("High latency detected (${AVG_TIME}ms average)")
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

data=$(cat <<EOF
{
    "host": "$HOST",
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
