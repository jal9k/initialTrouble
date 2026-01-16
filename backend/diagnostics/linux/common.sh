#!/usr/bin/env bash
# Common helper functions for Linux diagnostic scripts
# Source this file in other scripts: source "$(dirname "$0")/common.sh"

set -euo pipefail

# ============================================================================
# JSON Output Helpers
# ============================================================================

# Output a success JSON response
# Usage: output_success '{"key": "value"}' '["suggestion1", "suggestion2"]'
output_success() {
    local data="${1:-\{\}}"
    local suggestions="${2:-\[\]}"
    printf '{"success":true,"data":%s,"error":null,"suggestions":%s}\n' "$data" "$suggestions"
}

# Output a failure JSON response
# Usage: output_failure "Error message" '["suggestion1"]'
output_failure() {
    local error="$1"
    local suggestions="${2:-\[\]}"
    # Escape the error message for JSON
    local escaped_error
    escaped_error=$(echo "$error" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g; s/\n/\\n/g')
    printf '{"success":false,"data":{},"error":"%s","suggestions":%s}\n' "$escaped_error" "$suggestions"
}

# Convert a simple key=value list to JSON object
# Usage: to_json_object "key1" "value1" "key2" "value2"
to_json_object() {
    local result="{"
    local first=true
    while [[ $# -ge 2 ]]; do
        local key="$1"
        local value="$2"
        shift 2
        
        if [[ "$first" != "true" ]]; then
            result+=","
        fi
        first=false
        
        # Detect if value is a number, boolean, null, or needs quotes
        if [[ "$value" =~ ^-?[0-9]+(\.[0-9]+)?$ ]] || \
           [[ "$value" == "true" ]] || \
           [[ "$value" == "false" ]] || \
           [[ "$value" == "null" ]] || \
           [[ "$value" == "["* ]] || \
           [[ "$value" == "{"* ]]; then
            result+="\"${key}\":${value}"
        else
            # Escape string value
            local escaped
            escaped=$(echo "$value" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g')
            result+="\"${key}\":\"${escaped}\""
        fi
    done
    result+="}"
    echo "$result"
}

# Convert an array of strings to JSON array
# Usage: to_json_array "item1" "item2" "item3"
to_json_array() {
    local result="["
    local first=true
    for item in "$@"; do
        if [[ "$first" != "true" ]]; then
            result+=","
        fi
        first=false
        # Escape and quote string
        local escaped
        escaped=$(echo "$item" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g')
        result+="\"${escaped}\""
    done
    result+="]"
    echo "$result"
}

# ============================================================================
# Platform Detection
# ============================================================================

# Check if running on Linux
is_linux() {
    [[ "$(uname -s)" == "Linux" ]]
}

# Get Linux distribution name
get_linux_distro() {
    if [[ -f /etc/os-release ]]; then
        grep '^ID=' /etc/os-release | cut -d= -f2 | tr -d '"'
    else
        echo "unknown"
    fi
}

# ============================================================================
# Network Helpers
# ============================================================================

# Get the default gateway IP
get_default_gateway() {
    ip route | grep default | awk '{print $3}' | head -1
}

# Get the primary network interface
get_primary_interface() {
    ip route | grep default | awk '{print $5}' | head -1
}

# Check if interface exists
interface_exists() {
    local iface="$1"
    ip link show "$iface" >/dev/null 2>&1
}

# ============================================================================
# Test Mode Support
# ============================================================================

# Check if script is running in test mode
# Usage: if is_test_mode; then output_test_response; exit 0; fi
is_test_mode() {
    [[ "${1:-}" == "--test" ]] || [[ "${TEST_MODE:-}" == "1" ]]
}

# Output a test response (valid JSON for CI validation)
output_test_response() {
    local script_name="${1:-unknown}"
    output_success "$(to_json_object "test_mode" "true" "script" "$script_name")" '["Test mode - no actual diagnostic performed"]'
}
