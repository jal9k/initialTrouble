#!/usr/bin/env bash
# test_dns_resolution.sh - Test DNS resolution on Linux
# Usage: ./test_dns_resolution.sh [hostnames_comma_separated] [dns_server]

source "$(dirname "$0")/common.sh"

# Handle test mode
if is_test_mode "$1"; then
    output_test_response "test_dns_resolution"
    exit 0
fi

HOSTNAMES="${1:-google.com,cloudflare.com}"
DNS_SERVER="${2:-}"

# Split hostnames by comma
IFS=',' read -ra HOSTS <<< "$HOSTNAMES"

declare -a RESULTS=()
RESOLVED_COUNT=0
TOTAL_TIME=0
DNS_USED=""

for hostname in "${HOSTS[@]}"; do
    start_time=$(date +%s%3N 2>/dev/null || python3 -c 'import time; print(int(time.time() * 1000))')
    
    # Build nslookup command
    if [[ -n "$DNS_SERVER" ]]; then
        NSLOOKUP_OUTPUT=$(nslookup "$hostname" "$DNS_SERVER" 2>&1) || true
    else
        NSLOOKUP_OUTPUT=$(nslookup "$hostname" 2>&1) || true
    fi
    
    end_time=$(date +%s%3N 2>/dev/null || python3 -c 'import time; print(int(time.time() * 1000))')
    resolution_time=$((end_time - start_time))
    
    # Parse results
    resolved="false"
    error_msg=""
    declare -a ip_addresses=()
    dns_server_used=""
    
    # Check for errors
    if [[ "$NSLOOKUP_OUTPUT" == *"server can't find"* ]] || [[ "$NSLOOKUP_OUTPUT" == *"NXDOMAIN"* ]]; then
        error_msg="NXDOMAIN - domain not found"
    elif [[ "$NSLOOKUP_OUTPUT" == *"timed out"* ]] || [[ "$NSLOOKUP_OUTPUT" == *"no response"* ]]; then
        error_msg="DNS request timed out"
    else
        # Parse server
        if [[ "$NSLOOKUP_OUTPUT" =~ Server:\ *([^ ]+) ]]; then
            dns_server_used="${BASH_REMATCH[1]}"
            [[ -z "$DNS_USED" ]] && DNS_USED="$dns_server_used"
        fi
        
        # Parse addresses (after Non-authoritative answer)
        in_answer="false"
        while IFS= read -r line; do
            [[ "$line" == *"Non-authoritative answer"* ]] && in_answer="true" && continue
            [[ "$line" == *"Name:"* ]] && in_answer="true" && continue
            
            if [[ "$in_answer" == "true" ]]; then
                if [[ "$line" =~ Address:\ *([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+) ]]; then
                    ip="${BASH_REMATCH[1]}"
                    # Skip DNS server address
                    if [[ "$ip" != "$dns_server_used" ]]; then
                        ip_addresses+=("$ip")
                        resolved="true"
                    fi
                fi
            fi
        done <<< "$NSLOOKUP_OUTPUT"
    fi
    
    # Build IP array
    ips_json="["
    first=true
    for ip in "${ip_addresses[@]}"; do
        [[ "$first" != "true" ]] && ips_json+=","
        ips_json+="\"$ip\""
        first=false
    done
    ips_json+="]"
    
    # Track stats
    if [[ "$resolved" == "true" ]]; then
        ((RESOLVED_COUNT++))
        TOTAL_TIME=$((TOTAL_TIME + resolution_time))
    fi
    
    result=$(cat <<EOF
{
    "hostname": "$hostname",
    "resolved": $resolved,
    "ip_addresses": $ips_json,
    "dns_server_used": $(if [[ -n "$dns_server_used" ]]; then echo "\"$dns_server_used\""; else echo "null"; fi),
    "record_type": $(if [[ "$resolved" == "true" ]]; then echo "\"A\""; else echo "null"; fi),
    "resolution_time_ms": $(if [[ "$resolved" == "true" ]]; then echo "$resolution_time"; else echo "null"; fi),
    "error": $(if [[ -n "$error_msg" ]]; then echo "\"$error_msg\""; else echo "null"; fi)
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

DNS_WORKING="false"
[[ $RESOLVED_COUNT -gt 0 ]] && DNS_WORKING="true"

# Calculate average time
AVG_TIME="null"
if [[ $RESOLVED_COUNT -gt 0 ]]; then
    AVG_TIME=$(awk "BEGIN {printf \"%.1f\", $TOTAL_TIME / $RESOLVED_COUNT}")
fi

# Build suggestions
SUGGESTIONS=()
if [[ "$DNS_WORKING" == "false" ]]; then
    SUGGESTIONS+=("DNS resolution is not working")
    SUGGESTIONS+=("If ping_dns succeeded, this is a DNS-specific issue")
    SUGGESTIONS+=("Try changing DNS server to 8.8.8.8 or 1.1.1.1")
    SUGGESTIONS+=("Edit /etc/resolv.conf or use NetworkManager to change DNS")
elif [[ $RESOLVED_COUNT -lt ${#HOSTS[@]} ]]; then
    failed_hosts=()
    for r in "${RESULTS[@]}"; do
        if [[ "$r" == *'"resolved": false'* ]]; then
            hostname=$(echo "$r" | grep -o '"hostname": "[^"]*"' | cut -d'"' -f4)
            failed_hosts+=("$hostname")
        fi
    done
    failed_list=$(IFS=','; echo "${failed_hosts[*]}")
    SUGGESTIONS+=("DNS works but some domains failed: $failed_list")
    SUGGESTIONS+=("These domains may not exist or may be blocked")
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

# Build final data
data=$(cat <<EOF
{
    "hosts_tested": ${#HOSTS[@]},
    "hosts_resolved": $RESOLVED_COUNT,
    "dns_working": $DNS_WORKING,
    "results": $results_json,
    "avg_resolution_time_ms": $AVG_TIME,
    "dns_server": $(if [[ -n "$DNS_USED" ]]; then echo "\"$DNS_USED\""; else echo "null"; fi)
}
EOF
)

output_success "$data" "$suggestions_json"
