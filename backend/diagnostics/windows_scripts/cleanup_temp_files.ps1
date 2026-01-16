# cleanup_temp_files.ps1 - Clean up temporary files on Windows
# Usage: .\cleanup_temp_files.ps1 [-DryRun] [-Test]

param(
    [Parameter(Mandatory = $false)]
    [switch]$DryRun,
    
    [Parameter(Mandatory = $false)]
    [switch]$Test
)

# Import common functions
. "$PSScriptRoot\common.ps1"

# Handle test mode
if ($Test -or (Test-IsTestMode -Args $args)) {
    Output-TestResponse -ScriptName "cleanup_temp_files"
    exit 0
}

try {
    $cleanedLocations = @()
    $totalFreed = 0
    $filesDeleted = 0
    $foldersCleaned = 0
    $errors = @()
    
    # Directories to clean
    $tempDirs = @(
        @{ Path = $env:TEMP; Description = "User temp directory" },
        @{ Path = "C:\Windows\Temp"; Description = "Windows temp directory" },
        @{ Path = "$env:LOCALAPPDATA\Temp"; Description = "Local app data temp" },
        @{ Path = "$env:LOCALAPPDATA\Microsoft\Windows\INetCache"; Description = "Internet cache" },
        @{ Path = "C:\Windows\Prefetch"; Description = "Prefetch cache" },
        @{ Path = "$env:USERPROFILE\AppData\Local\Google\Chrome\User Data\Default\Cache"; Description = "Chrome cache" },
        @{ Path = "$env:USERPROFILE\AppData\Local\Mozilla\Firefox\Profiles"; Description = "Firefox cache" }
    )
    
    foreach ($dir in $tempDirs) {
        if (Test-Path $dir.Path) {
            try {
                # Get size and file count before
                $items = Get-ChildItem -Path $dir.Path -Recurse -Force -ErrorAction SilentlyContinue
                $sizeBefore = ($items | Measure-Object -Property Length -Sum).Sum
                if (-not $sizeBefore) { $sizeBefore = 0 }
                $fileCount = ($items | Where-Object { -not $_.PSIsContainer }).Count
                
                if ($DryRun) {
                    $cleanedLocations += @{
                        path = $dir.Path
                        description = $dir.Description
                        size_bytes = $sizeBefore
                        files = $fileCount
                        action = "would_clean"
                    }
                } else {
                    # Delete files
                    Get-ChildItem -Path $dir.Path -Recurse -Force -ErrorAction SilentlyContinue | 
                        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
                    
                    # Get size after
                    $itemsAfter = Get-ChildItem -Path $dir.Path -Recurse -Force -ErrorAction SilentlyContinue
                    $sizeAfter = ($itemsAfter | Measure-Object -Property Length -Sum).Sum
                    if (-not $sizeAfter) { $sizeAfter = 0 }
                    
                    $freed = $sizeBefore - $sizeAfter
                    if ($freed -gt 0) {
                        $totalFreed += $freed
                        $filesDeleted += $fileCount
                        $foldersCleaned++
                    }
                    
                    $cleanedLocations += @{
                        path = $dir.Path
                        description = $dir.Description
                        size_freed_bytes = $freed
                        files_deleted = $fileCount
                    }
                }
            }
            catch {
                $errors += $_.Exception.Message
            }
        }
    }
    
    # Format size for display
    $formattedSize = if ($totalFreed -ge 1GB) {
        "{0:N2} GB" -f ($totalFreed / 1GB)
    } elseif ($totalFreed -ge 1MB) {
        "{0:N2} MB" -f ($totalFreed / 1MB)
    } elseif ($totalFreed -ge 1KB) {
        "{0:N2} KB" -f ($totalFreed / 1KB)
    } else {
        "$totalFreed bytes"
    }
    
    # Build suggestions
    $suggestions = @()
    if ($DryRun) {
        $suggestions += "Dry run completed - no files were deleted"
        $suggestions += "Run without -DryRun to actually clean files"
    } else {
        $suggestions += "Cleanup completed successfully"
        $suggestions += "Freed approximately $formattedSize"
        if ($filesDeleted -gt 0) {
            $suggestions += "Deleted $filesDeleted files from $foldersCleaned locations"
        }
    }
    
    $data = @{
        dry_run = $DryRun.IsPresent
        total_freed_bytes = $totalFreed
        total_freed_formatted = $formattedSize
        files_deleted = $filesDeleted
        folders_cleaned = $foldersCleaned
        locations = $cleanedLocations
        errors = $errors
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @("Run as Administrator for full cleanup")
}
