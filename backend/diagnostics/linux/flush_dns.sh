#!/usr/bin/env bash
# flush_dns.sh - Flush DNS cache on Linux
# Usage: ./flush_dns.sh

source "$(dirname "$0")/common.sh"

# Handle test mode
if is_test_mode "$1"; then
    output_test_response "flush_dns"
    exit 0
fi

COMMANDS_RUN=()
ERRORS=()
SUCCESS="false"
DISTRO=$(get_linux_distro)

# Method 1: systemd-resolved (Ubuntu 17+, Fedora, etc.)
if systemctl is-active --quiet systemd-resolved 2>/dev/null; then
    resolvectl flush-caches 2>&1
    COMMANDS_RUN+=("resolvectl flush-caches")
    SUCCESS="true"
fi

# Method 2: nscd (Name Service Cache Daemon)
if systemctl is-active --quiet nscd 2>/dev/null || pgrep nscd &>/dev/null; then
    nscd -i hosts 2>&1
    COMMANDS_RUN+=("nscd -i hosts")
    SUCCESS="true"
fi

# Method 3: dnsmasq
if systemctl is-active --quiet dnsmasq 2>/dev/null || pgrep dnsmasq &>/dev/null; then
    killall -HUP dnsmasq 2>&1
    COMMANDS_RUN+=("killall -HUP dnsmasq")
    SUCCESS="true"
fi

# Method 4: NetworkManager
if systemctl is-active --quiet NetworkManager 2>/dev/null; then
    nmcli general reload dns 2>&1
    COMMANDS_RUN+=("nmcli general reload dns")
    SUCCESS="true"
fi

# If no specific service found, try common commands anyway
if [[ ${#COMMANDS_RUN[@]} -eq 0 ]]; then
    # Try resolvectl
    if command -v resolvectl &>/dev/null; then
        resolvectl flush-caches 2>&1
        COMMANDS_RUN+=("resolvectl flush-caches")
        SUCCESS="true"
    fi
    
    # Try systemd-resolve
    if command -v systemd-resolve &>/dev/null; then
        systemd-resolve --flush-caches 2>&1
        COMMANDS_RUN+=("systemd-resolve --flush-caches")
        SUCCESS="true"
    fi
fi

# Build commands array JSON
commands_json="["
first=true
for cmd in "${COMMANDS_RUN[@]}"; do
    [[ "$first" != "true" ]] && commands_json+=","
    commands_json+="\"$cmd\""
    first=false
done
commands_json+="]"

# Build suggestions
SUGGESTIONS=()
if [[ "$SUCCESS" == "true" ]]; then
    SUGGESTIONS+=("DNS cache flushed successfully")
    SUGGESTIONS+=("Cached DNS entries have been cleared")
    SUGGESTIONS+=("New DNS lookups will query DNS servers directly")
else
    SUGGESTIONS+=("Could not find DNS caching service to flush")
    SUGGESTIONS+=("Linux may not be running a local DNS cache")
    SUGGESTIONS+=("Check for: systemd-resolved, nscd, or dnsmasq")
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

data=$(cat <<EOF
{
    "success": $SUCCESS,
    "distro": "$DISTRO",
    "commands_run": $commands_json,
    "errors": []
}
EOF
)

output_success "$data" "$suggestions_json"
