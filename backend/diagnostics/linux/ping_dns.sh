#!/usr/bin/env bash
# ping_dns.sh - Ping external DNS servers on Linux
# Usage: ./ping_dns.sh [count]

source "$(dirname "$0")/common.sh"

# Handle test mode
if is_test_mode "$1"; then
    output_test_response "ping_dns"
    exit 0
fi

COUNT="${1:-4}"

# DNS servers to test
declare -a DNS_SERVERS=("8.8.8.8:Google Public DNS" "1.1.1.1:Cloudflare DNS")

declare -a RESULTS=()
SERVERS_REACHABLE=0
BEST_SERVER=""
BEST_LATENCY="999999"

for server_entry in "${DNS_SERVERS[@]}"; do
    IFS=':' read -r ip name <<< "$server_entry"
    
    # Run ping
    PING_OUTPUT=$(ping -c "$COUNT" -W 5 "$ip" 2>&1) || true
    
    # Parse results
    packets_sent=0
    packets_received=0
    avg_time=""
    
    while IFS= read -r line; do
        if [[ $line =~ ([0-9]+)\ packets\ transmitted,\ ([0-9]+)\ received ]]; then
            packets_sent="${BASH_REMATCH[1]}"
            packets_received="${BASH_REMATCH[2]}"
        elif [[ $line =~ rtt\ min/avg/max/mdev\ =\ [0-9.]+/([0-9.]+)/ ]]; then
            avg_time="${BASH_REMATCH[1]}"
        fi
    done <<< "$PING_OUTPUT"
    
    # Calculate packet loss
    if [[ $packets_sent -gt 0 ]]; then
        packet_loss=$(awk "BEGIN {printf \"%.1f\", (($packets_sent - $packets_received) / $packets_sent) * 100}")
    else
        packet_loss="100.0"
    fi
    
    reachable="false"
    [[ $packets_received -gt 0 ]] && reachable="true" && ((SERVERS_REACHABLE++))
    
    # Track best server
    if [[ "$reachable" == "true" ]] && [[ -n "$avg_time" ]]; then
        if (( $(echo "$avg_time < $BEST_LATENCY" | bc -l 2>/dev/null || echo "0") )); then
            BEST_LATENCY="$avg_time"
            BEST_SERVER="$ip"
        fi
    fi
    
    result=$(cat <<EOF
{
    "server": "$ip",
    "name": "$name",
    "reachable": $reachable,
    "packets_sent": $packets_sent,
    "packets_received": $packets_received,
    "packet_loss_percent": $packet_loss,
    "avg_time_ms": $(if [[ -n "$avg_time" ]]; then echo "$avg_time"; else echo "null"; fi)
}
EOF
)
    RESULTS+=("$result")
done

# Build results array
results_json="["
first=true
for r in "${RESULTS[@]}"; do
    [[ "$first" != "true" ]] && results_json+=","
    results_json+="$r"
    first=false
done
results_json+="]"

INTERNET_ACCESSIBLE="false"
[[ $SERVERS_REACHABLE -gt 0 ]] && INTERNET_ACCESSIBLE="true"

# Build suggestions
SUGGESTIONS=()
if [[ "$INTERNET_ACCESSIBLE" == "false" ]]; then
    SUGGESTIONS+=("Cannot reach external DNS servers - no internet connectivity")
    SUGGESTIONS+=("If gateway ping succeeded, this is a WAN issue")
    SUGGESTIONS+=("Check if modem is connected to ISP")
    SUGGESTIONS+=("Contact ISP if modem shows connected but no internet")
elif [[ $SERVERS_REACHABLE -lt ${#DNS_SERVERS[@]} ]]; then
    SUGGESTIONS+=("Internet is accessible but some DNS servers are unreachable")
    [[ -n "$BEST_SERVER" ]] && SUGGESTIONS+=("Consider using the reachable DNS server ($BEST_SERVER)")
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

# Build final data
data=$(cat <<EOF
{
    "servers_tested": ${#DNS_SERVERS[@]},
    "servers_reachable": $SERVERS_REACHABLE,
    "internet_accessible": $INTERNET_ACCESSIBLE,
    "results": $results_json,
    "best_server": $(if [[ -n "$BEST_SERVER" ]]; then echo "\"$BEST_SERVER\""; else echo "null"; fi),
    "best_latency_ms": $(if [[ "$BEST_LATENCY" != "999999" ]]; then echo "$BEST_LATENCY"; else echo "null"; fi)
}
EOF
)

output_success "$data" "$suggestions_json"
