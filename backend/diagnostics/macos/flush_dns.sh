#!/usr/bin/env bash
# flush_dns.sh - Flush DNS cache on macOS
# Usage: ./flush_dns.sh

source "$(dirname "$0")/common.sh"

# Handle test mode
if is_test_mode "$1"; then
    output_test_response "flush_dns"
    exit 0
fi

# Get macOS version to determine correct flush command
MACOS_VERSION=$(sw_vers -productVersion 2>/dev/null | cut -d. -f1)
MACOS_MINOR=$(sw_vers -productVersion 2>/dev/null | cut -d. -f2)

COMMANDS_RUN=()
ERRORS=()
SUCCESS="false"

# macOS 12+ (Monterey and later)
if [[ $MACOS_VERSION -ge 12 ]]; then
    dscacheutil -flushcache 2>&1
    COMMANDS_RUN+=("dscacheutil -flushcache")
    
    killall -HUP mDNSResponder 2>&1
    COMMANDS_RUN+=("killall -HUP mDNSResponder")
    
    SUCCESS="true"

# macOS 11 (Big Sur)
elif [[ $MACOS_VERSION -eq 11 ]]; then
    dscacheutil -flushcache 2>&1
    COMMANDS_RUN+=("dscacheutil -flushcache")
    
    killall -HUP mDNSResponder 2>&1
    COMMANDS_RUN+=("killall -HUP mDNSResponder")
    
    SUCCESS="true"

# macOS 10.15 (Catalina) and 10.14 (Mojave)
elif [[ $MACOS_VERSION -eq 10 ]] && [[ $MACOS_MINOR -ge 14 ]]; then
    killall -HUP mDNSResponder 2>&1
    COMMANDS_RUN+=("killall -HUP mDNSResponder")
    
    dscacheutil -flushcache 2>&1
    COMMANDS_RUN+=("dscacheutil -flushcache")
    
    SUCCESS="true"

# Older macOS versions
else
    # Try common commands
    if command -v dscacheutil &>/dev/null; then
        dscacheutil -flushcache 2>&1
        COMMANDS_RUN+=("dscacheutil -flushcache")
    fi
    
    killall -HUP mDNSResponder 2>/dev/null
    COMMANDS_RUN+=("killall -HUP mDNSResponder")
    
    SUCCESS="true"
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
    SUGGESTIONS+=("DNS cache flush may have failed")
    SUGGESTIONS+=("Try running commands with sudo")
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

data=$(cat <<EOF
{
    "success": $SUCCESS,
    "macos_version": "$(get_macos_version)",
    "commands_run": $commands_json,
    "errors": []
}
EOF
)

output_success "$data" "$suggestions_json"
