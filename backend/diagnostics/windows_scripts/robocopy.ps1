# robocopy.ps1 - File copy operations using robocopy on Windows
# Usage: .\robocopy.ps1 -Source <path> -Destination <path> [-Mirror] [-Verbose] [-Test]

param(
    [Parameter(Mandatory = $false)]
    [string]$Source = "",
    
    [Parameter(Mandatory = $false)]
    [string]$Destination = "",
    
    [Parameter(Mandatory = $false)]
    [switch]$Mirror,
    
    [Parameter(Mandatory = $false)]
    [switch]$VerboseOutput,
    
    [Parameter(Mandatory = $false)]
    [switch]$Test
)

# Import common functions
. "$PSScriptRoot\common.ps1"

# Handle test mode
if ($Test -or (Test-IsTestMode -Args $args)) {
    Output-TestResponse -ScriptName "robocopy"
    exit 0
}

if (-not $Source -or -not $Destination) {
    Output-Failure -Error "Source and Destination paths are required" -Suggestions @(
        "Usage: robocopy.ps1 -Source <path> -Destination <path>",
        "Example: robocopy.ps1 -Source 'C:\Data' -Destination 'D:\Backup'"
    )
    exit 1
}

if (-not (Test-Path $Source)) {
    Output-Failure -Error "Source path does not exist: $Source" -Suggestions @(
        "Verify the source path is correct",
        "Ensure you have access to the source location"
    )
    exit 1
}

try {
    # Build robocopy arguments
    $args = @($Source, $Destination)
    
    if ($Mirror) {
        # Mirror mode: make destination identical to source
        $args += "/MIR"
    } else {
        # Default: copy all files and subdirectories
        $args += "/E"
    }
    
    # Common options
    $args += "/R:3"    # Retry 3 times
    $args += "/W:5"    # Wait 5 seconds between retries
    $args += "/NP"     # No progress percentage (cleaner output)
    $args += "/NDL"    # No directory list
    $args += "/NJH"    # No job header
    $args += "/NJS"    # No job summary
    $args += "/BYTES"  # Show bytes instead of size units
    
    if ($VerboseOutput) {
        $args += "/V"
    }
    
    # Run robocopy
    $startTime = Get-Date
    $output = & robocopy @args 2>&1
    $exitCode = $LASTEXITCODE
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds
    
    # Parse exit code
    # Robocopy exit codes are bitmasks:
    # 0 = No files copied, no errors
    # 1 = One or more files copied
    # 2 = Extra files/dirs detected
    # 4 = Mismatched files/dirs detected
    # 8 = Some files/dirs could not be copied
    # 16 = Serious error
    
    $success = $exitCode -lt 8  # 0-7 are generally successful
    $filescopied = 0
    $bytesCopied = 0
    $errors = 0
    
    # Try to parse output for statistics
    $outputString = $output -join "`n"
    
    if ($outputString -match "Files\s*:\s*(\d+)") {
        $filescopied = [int]$Matches[1]
    }
    if ($outputString -match "Bytes\s*:\s*(\d+)") {
        $bytesCopied = [long]$Matches[1]
    }
    if ($outputString -match "Failed\s*:\s*(\d+)") {
        $errors = [int]$Matches[1]
    }
    
    # Format bytes
    $formattedSize = if ($bytesCopied -ge 1GB) {
        "{0:N2} GB" -f ($bytesCopied / 1GB)
    } elseif ($bytesCopied -ge 1MB) {
        "{0:N2} MB" -f ($bytesCopied / 1MB)
    } elseif ($bytesCopied -ge 1KB) {
        "{0:N2} KB" -f ($bytesCopied / 1KB)
    } else {
        "$bytesCopied bytes"
    }
    
    # Interpret exit code
    $exitMessage = switch ($exitCode) {
        0 { "No files copied - source and destination are identical" }
        1 { "Files copied successfully" }
        2 { "Extra files or directories detected at destination" }
        3 { "Files copied, extra files detected" }
        4 { "Some mismatched files or directories detected" }
        5 { "Files copied, some mismatches detected" }
        6 { "Extra files and mismatches detected" }
        7 { "Files copied, extra files and mismatches detected" }
        8 { "Some files or directories could not be copied" }
        16 { "Serious error - robocopy failed" }
        default { "Unknown exit code: $exitCode" }
    }
    
    # Build suggestions
    $suggestions = @()
    if ($success) {
        $suggestions += "Copy operation completed"
        $suggestions += "Duration: $([math]::Round($duration, 1)) seconds"
        if ($filescopied -gt 0) {
            $suggestions += "Copied $filescopied files ($formattedSize)"
        }
    } else {
        $suggestions += "Copy operation encountered errors"
        if ($exitCode -eq 8) {
            $suggestions += "Some files could not be copied - check permissions"
        } elseif ($exitCode -ge 16) {
            $suggestions += "Serious error occurred - check source and destination paths"
        }
    }
    
    if ($Mirror) {
        $suggestions += "Mirror mode: destination is now synchronized with source"
    }
    
    $data = @{
        success = $success
        source = $Source
        destination = $Destination
        mirror_mode = $Mirror.IsPresent
        exit_code = $exitCode
        exit_message = $exitMessage
        files_copied = $filescopied
        bytes_copied = $bytesCopied
        bytes_formatted = $formattedSize
        errors = $errors
        duration_seconds = [math]::Round($duration, 1)
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @(
        "Verify source and destination paths",
        "Check you have read/write permissions"
    )
}
