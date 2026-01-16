#!/usr/bin/env bash
# kill_process.sh - Kill a process by name or PID on macOS
# Usage: ./kill_process.sh <process_name_or_pid> [force]

source "$(dirname "$0")/common.sh"

# Handle test mode
if is_test_mode "$1"; then
    output_test_response "kill_process"
    exit 0
fi

PROCESS="${1:-}"
FORCE="${2:-false}"

if [[ -z "$PROCESS" ]]; then
    output_failure "Process name or PID is required" '["Usage: kill_process.sh <process_name_or_pid> [force]"]'
    exit 1
fi

[[ "$FORCE" == "true" ]] && FORCE="true" || FORCE="false"

# Determine if input is PID or name
IS_PID="false"
[[ "$PROCESS" =~ ^[0-9]+$ ]] && IS_PID="true"

declare -a KILLED_PROCESSES=()
KILL_COUNT=0
FAIL_COUNT=0

if [[ "$IS_PID" == "true" ]]; then
    # Kill by PID
    PID="$PROCESS"
    
    # Get process name
    PROC_NAME=$(ps -p "$PID" -o comm= 2>/dev/null)
    
    if [[ -z "$PROC_NAME" ]]; then
        output_failure "Process with PID $PID not found" '["The process may have already terminated"]'
        exit 1
    fi
    
    # Kill the process
    if [[ "$FORCE" == "true" ]]; then
        kill -9 "$PID" 2>/dev/null
    else
        kill "$PID" 2>/dev/null
    fi
    
    EXIT_CODE=$?
    sleep 1
    
    # Verify kill
    if ps -p "$PID" >/dev/null 2>&1; then
        ((FAIL_COUNT++))
        KILLED_PROCESSES+=("{\"pid\":$PID,\"name\":\"$PROC_NAME\",\"killed\":false,\"error\":\"Process still running\"}")
    else
        ((KILL_COUNT++))
        KILLED_PROCESSES+=("{\"pid\":$PID,\"name\":\"$PROC_NAME\",\"killed\":true,\"error\":null}")
    fi
else
    # Kill by name
    PROC_NAME="$PROCESS"
    
    # Find all matching PIDs
    PIDS=$(pgrep -x "$PROC_NAME" 2>/dev/null || pgrep -f "$PROC_NAME" 2>/dev/null)
    
    if [[ -z "$PIDS" ]]; then
        output_failure "No processes found matching '$PROC_NAME'" '["Check the process name and try again", "Use ps aux | grep <name> to find the process"]'
        exit 1
    fi
    
    for PID in $PIDS; do
        # Kill the process
        if [[ "$FORCE" == "true" ]]; then
            kill -9 "$PID" 2>/dev/null
        else
            kill "$PID" 2>/dev/null
        fi
        
        sleep 0.5
        
        # Verify kill
        if ps -p "$PID" >/dev/null 2>&1; then
            ((FAIL_COUNT++))
            KILLED_PROCESSES+=("{\"pid\":$PID,\"name\":\"$PROC_NAME\",\"killed\":false,\"error\":\"Process still running\"}")
        else
            ((KILL_COUNT++))
            KILLED_PROCESSES+=("{\"pid\":$PID,\"name\":\"$PROC_NAME\",\"killed\":true,\"error\":null}")
        fi
    done
fi

# Build killed processes array
killed_json="["
first=true
for proc in "${KILLED_PROCESSES[@]}"; do
    [[ "$first" != "true" ]] && killed_json+=","
    killed_json+="$proc"
    first=false
done
killed_json+="]"

SUCCESS="false"
[[ $KILL_COUNT -gt 0 ]] && SUCCESS="true"

# Build suggestions
SUGGESTIONS=()
if [[ "$SUCCESS" == "true" ]]; then
    SUGGESTIONS+=("Successfully killed $KILL_COUNT process(es)")
    [[ $FAIL_COUNT -gt 0 ]] && SUGGESTIONS+=("Failed to kill $FAIL_COUNT process(es)")
else
    SUGGESTIONS+=("Failed to kill any processes")
    if [[ "$FORCE" == "false" ]]; then
        SUGGESTIONS+=("Try with force=true for SIGKILL")
    else
        SUGGESTIONS+=("Process may be protected or running as root")
        SUGGESTIONS+=("Try with sudo or check permissions")
    fi
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

data=$(cat <<EOF
{
    "target": "$PROCESS",
    "was_pid": $IS_PID,
    "force": $FORCE,
    "processes_killed": $KILL_COUNT,
    "processes_failed": $FAIL_COUNT,
    "processes": $killed_json,
    "success": $SUCCESS
}
EOF
)

output_success "$data" "$suggestions_json"
