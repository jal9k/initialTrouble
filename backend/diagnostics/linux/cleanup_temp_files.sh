#!/usr/bin/env bash
# cleanup_temp_files.sh - Clean up temporary files on Linux
# Usage: ./cleanup_temp_files.sh [dry_run]

source "$(dirname "$0")/common.sh"

# Handle test mode
if is_test_mode "$1"; then
    output_test_response "cleanup_temp_files"
    exit 0
fi

DRY_RUN="${1:-false}"
[[ "$DRY_RUN" == "true" ]] && DRY_RUN="true" || DRY_RUN="false"

declare -a CLEANED_LOCATIONS=()
declare -a ERRORS=()
TOTAL_FREED=0
FILES_DELETED=0
FOLDERS_CLEANED=0

# Function to get directory size in bytes
get_dir_size() {
    local dir="$1"
    du -sb "$dir" 2>/dev/null | awk '{print $1}'
}

# Function to clean a directory
clean_directory() {
    local dir="$1"
    local desc="$2"
    
    if [[ -d "$dir" ]]; then
        local size_before=$(get_dir_size "$dir")
        [[ -z "$size_before" ]] && size_before=0
        local file_count=$(find "$dir" -type f 2>/dev/null | wc -l | tr -d ' ')
        
        if [[ "$DRY_RUN" == "true" ]]; then
            CLEANED_LOCATIONS+=("{\"path\":\"$dir\",\"description\":\"$desc\",\"size_bytes\":$size_before,\"files\":$file_count,\"action\":\"would_clean\"}")
        else
            rm -rf "$dir"/* 2>/dev/null || true
            local size_after=$(get_dir_size "$dir")
            [[ -z "$size_after" ]] && size_after=0
            local freed=$((size_before - size_after))
            
            if [[ $freed -gt 0 ]]; then
                TOTAL_FREED=$((TOTAL_FREED + freed))
                FILES_DELETED=$((FILES_DELETED + file_count))
                ((FOLDERS_CLEANED++))
            fi
            
            CLEANED_LOCATIONS+=("{\"path\":\"$dir\",\"description\":\"$desc\",\"size_freed_bytes\":$freed,\"files_deleted\":$file_count}")
        fi
    fi
}

# Clean system temp directories
clean_directory "/tmp" "System temp directory"
clean_directory "/var/tmp" "Variable temp directory"
clean_directory "$HOME/.cache" "User cache directory"

# Trash
clean_directory "$HOME/.local/share/Trash/files" "User trash files"
clean_directory "$HOME/.local/share/Trash/info" "User trash info"

# Chrome caches (if exists)
if [[ -d "$HOME/.config/google-chrome" ]]; then
    clean_directory "$HOME/.config/google-chrome/Default/Cache" "Chrome cache"
fi

# Firefox caches (if exists)
if [[ -d "$HOME/.mozilla/firefox" ]]; then
    FIREFOX_PROFILE=$(find "$HOME/.mozilla/firefox" -maxdepth 1 -type d -name "*.default*" 2>/dev/null | head -1)
    if [[ -n "$FIREFOX_PROFILE" ]]; then
        clean_directory "$FIREFOX_PROFILE/cache2" "Firefox cache"
    fi
fi

# Thumbnails
clean_directory "$HOME/.cache/thumbnails" "Thumbnails cache"

# Build cleaned locations array
cleaned_json="["
first=true
for loc in "${CLEANED_LOCATIONS[@]}"; do
    [[ "$first" != "true" ]] && cleaned_json+=","
    cleaned_json+="$loc"
    first=false
done
cleaned_json+="]"

# Format size for display
format_size() {
    local bytes=$1
    if [[ $bytes -ge 1073741824 ]]; then
        echo "$(awk "BEGIN {printf \"%.2f\", $bytes / 1073741824}") GB"
    elif [[ $bytes -ge 1048576 ]]; then
        echo "$(awk "BEGIN {printf \"%.2f\", $bytes / 1048576}") MB"
    elif [[ $bytes -ge 1024 ]]; then
        echo "$(awk "BEGIN {printf \"%.2f\", $bytes / 1024}") KB"
    else
        echo "$bytes bytes"
    fi
}

FORMATTED_SIZE=$(format_size $TOTAL_FREED)

# Build suggestions
SUGGESTIONS=()
if [[ "$DRY_RUN" == "true" ]]; then
    SUGGESTIONS+=("Dry run completed - no files were deleted")
    SUGGESTIONS+=("Run with dry_run=false to actually clean files")
else
    SUGGESTIONS+=("Cleanup completed successfully")
    SUGGESTIONS+=("Freed approximately $FORMATTED_SIZE")
    [[ $FILES_DELETED -gt 0 ]] && SUGGESTIONS+=("Deleted $FILES_DELETED files from $FOLDERS_CLEANED locations")
fi

suggestions_json=$(to_json_array "${SUGGESTIONS[@]}")

data=$(cat <<EOF
{
    "dry_run": $DRY_RUN,
    "total_freed_bytes": $TOTAL_FREED,
    "total_freed_formatted": "$FORMATTED_SIZE",
    "files_deleted": $FILES_DELETED,
    "folders_cleaned": $FOLDERS_CLEANED,
    "locations": $cleaned_json,
    "errors": []
}
EOF
)

output_success "$data" "$suggestions_json"
