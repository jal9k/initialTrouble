#!/usr/bin/env bash
# Test diagnostic scripts for a specific platform
# Usage: ./scripts/test_diagnostics.sh [macos|linux]

set -euo pipefail

# Determine platform
PLATFORM="${1:-$(uname -s | tr '[:upper:]' '[:lower:]')}"
[[ "$PLATFORM" == "darwin" ]] && PLATFORM="macos"

SCRIPT_DIR="backend/diagnostics/${PLATFORM}"

if [[ ! -d "$SCRIPT_DIR" ]]; then
    echo "❌ Script directory not found: $SCRIPT_DIR"
    exit 1
fi

FAILED=0
PASSED=0
SKIPPED=0

echo "=============================================="
echo "Testing ${PLATFORM} diagnostic scripts..."
echo "=============================================="
echo ""

for script in "$SCRIPT_DIR"/*.sh; do
    [[ -f "$script" ]] || continue
    name=$(basename "$script" .sh)
    
    # Skip common.sh
    [[ "$name" == "common" ]] && continue
    
    printf "  Testing %-30s " "${name}..."
    
    # Run script in test mode and capture output
    if output=$(bash "$script" --test 2>&1); then
        # Validate JSON output
        if command -v jq &>/dev/null; then
            if echo "$output" | jq -e '.success != null' > /dev/null 2>&1; then
                echo "✓ PASS"
                ((PASSED++))
            else
                echo "✗ FAIL (invalid JSON structure)"
                echo "    Output: ${output:0:100}..."
                ((FAILED++))
            fi
        else
            # Without jq, just check for basic JSON structure
            if [[ "$output" == *'"success"'* ]]; then
                echo "✓ PASS (no jq for validation)"
                ((PASSED++))
            else
                echo "✗ FAIL (invalid output)"
                ((FAILED++))
            fi
        fi
    else
        exit_code=$?
        echo "✗ FAIL (exit code $exit_code)"
        echo "    Output: ${output:0:100}..."
        ((FAILED++))
    fi
done

echo ""
echo "=============================================="
echo "Results: ${PASSED} passed, ${FAILED} failed, ${SKIPPED} skipped"
echo "=============================================="

[[ $FAILED -eq 0 ]] || exit 1
