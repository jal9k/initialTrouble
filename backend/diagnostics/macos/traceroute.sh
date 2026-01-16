#!/usr/bin/env bash
# traceroute.sh - Trace route to destination on macOS
# Usage: ./traceroute.sh <host> [max_hops]

source "$(dirname "$0")/common.sh"

# Handle test mode
if is_test_mode "$1"; then
    output_test_response "traceroute"
    exit 0
fi

HOST="${1:-}"
MAX_HOPS="${2:-30}"

if [[ -z "$HOST" ]]; then
    output_failure "Destination host is required" '["Provide an IP address or hostname to trace"]'
    exit 1
fi

# Run traceroute
TIMEOUT=$((MAX_HOPS * 4))
TRACE_OUTPUT=$(traceroute -m "$MAX_HOPS" -w 3 "$HOST" 2>&1) || true

declare -a HOPS=()
DESTINATION_REACHED="false"

while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    [[ "$line" == traceroute* ]] && continue
    
    # Parse hop number
    if [[ $line =~ ^\ *([0-9]+) ]]; then
        hop_number="${BASH_REMATCH[1]}"
        
        # Check for timeout (all asterisks)
        if [[ "$line" =~ \*\ +\*\ +\* ]]; then
            hop_json=$(cat <<EOF
{
    "hop_number": $hop_number,
    "timed_out": true,
    "address": null,
    "hostname": null,
    "times_ms": [],
    "avg_time_ms": null
}
EOF
)
            HOPS+=("$hop_json")
            continue
        fi
        
        # Extract IP address
        address=""
        hostname=""
        if [[ $line =~ ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+) ]]; then
            address="${BASH_REMATCH[1]}"
        fi
        
        # Extract hostname (before IP in parentheses)
        if [[ $line =~ ([a-zA-Z0-9.-]+)\ +\($address\) ]]; then
            hostname="${BASH_REMATCH[1]}"
        fi
        
        # Extract times
        declare -a times=()
        while [[ $line =~ ([0-9]+\.?[0-9]*)\ ms ]]; do
            times+=("${BASH_REMATCH[1]}")
            line="${line/${BASH_REMATCH[0]}/}"
        done
        
        # Calculate average
        avg_time="null"
        if [[ ${#times[@]} -gt 0 ]]; then
            sum=0
            for t in "${times[@]}"; do
                sum=$(echo "$sum + $t" | bc)
            done
            avg_time=$(echo "scale=1; $sum / ${#times[@]}" | bc)
        fi
        
        # Build times array
        times_json="["
        first=true
        for t in "${times[@]}"; do
            [[ "$first" != "true" ]] && times_json+=","
            times_json+="$t"
            first=false
        done
        times_json+="]"
        
        hop_json=$(cat <<EOF
{
    "hop_number": $hop_number,
    "timed_out": false,
    "address": $(if [[ -n "$address" ]]; then echo "\"$address\""; else echo "null"; fi),
    "hostname": $(if [[ -n "$hostname" ]]; then echo "\"$hostname\""; else echo "null"; fi),
    "times_ms": $times_json,
    "avg_time_ms": $avg_time
}
EOF
)
        HOPS+=("$hop_json")
    fi
done <<< "$TRACE_OUTPUT"

# Check if destination reached
if [[ ${#HOPS[@]} -gt 0 ]]; then
    last_hop="${HOPS[-1]}"
    if [[ "$last_hop" != *'"timed_out": true'* ]] && [[ "$last_hop" == *'"address":'* ]]; then
        DESTINATION_REACHED="true"
    fi
fi

# Build hops array
hops_json="["
first=true
for hop in "${HOPS[@]}"; do
    [[ "$first" != "true" ]] && hops_json+=","
    hops_json+="$hop"
    first=false
done
hops_json+="]"

SUGGESTIONS=()
if [[ "$DESTINATION_REACHED" == "false" ]]; then
    SUGGESTIONS+=("Could not reach destination '$HOST'")
    SUGGESTIONS+=("Check where the trace stops to identify the problem")
    if [[ ${#HOPS[@]} -gt 0 ]] && [[ "${HOPS[-1]}" == *'"timed_out": true'* ]]; then
        SUGGESTIONS+=("The last hop timed out - may indicate firewall blocking")
    fi
elif [[ ${#HOPS[@]} -gt 15 ]]; then
    SUGGESTIONS+=("Route has many hops (${#HOPS[@]}) - may affect latency")
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

data=$(cat <<EOF
{
    "destination": "$HOST",
    "destination_reached": $DESTINATION_REACHED,
    "total_hops": ${#HOPS[@]},
    "max_hops_setting": $MAX_HOPS,
    "hops": $hops_json
}
EOF
)

output_success "$data" "$suggestions_json"
