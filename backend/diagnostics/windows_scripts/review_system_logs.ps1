# review_system_logs.ps1 - Review Windows system event logs
# Usage: .\review_system_logs.ps1 [-LogName <name>] [-Hours <n>] [-Level <Error|Warning|All>] [-Test]

param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("System", "Application", "Security")]
    [string]$LogName = "System",
    
    [Parameter(Mandatory = $false)]
    [int]$Hours = 24,
    
    [Parameter(Mandatory = $false)]
    [ValidateSet("Error", "Warning", "All")]
    [string]$Level = "Error",
    
    [Parameter(Mandatory = $false)]
    [switch]$Test
)

# Import common functions
. "$PSScriptRoot\common.ps1"

# Handle test mode
if ($Test -or (Test-IsTestMode -Args $args)) {
    Output-TestResponse -ScriptName "review_system_logs"
    exit 0
}

try {
    $startTime = (Get-Date).AddHours(-$Hours)
    
    # Build level filter
    $levelFilter = switch ($Level) {
        "Error" { 1, 2 }  # Critical and Error
        "Warning" { 1, 2, 3 }  # Critical, Error, Warning
        "All" { 1, 2, 3, 4 }  # Critical, Error, Warning, Information
    }
    
    # Get events
    $events = Get-WinEvent -FilterHashtable @{
        LogName = $LogName
        StartTime = $startTime
        Level = $levelFilter
    } -MaxEvents 100 -ErrorAction SilentlyContinue
    
    $eventList = @()
    $errorCount = 0
    $warningCount = 0
    $criticalCount = 0
    
    foreach ($event in $events) {
        $levelName = switch ($event.Level) {
            1 { "Critical"; $criticalCount++ }
            2 { "Error"; $errorCount++ }
            3 { "Warning"; $warningCount++ }
            4 { "Information" }
            default { "Unknown" }
        }
        
        $eventList += @{
            time = $event.TimeCreated.ToString("yyyy-MM-dd HH:mm:ss")
            level = $levelName
            source = $event.ProviderName
            event_id = $event.Id
            message = if ($event.Message.Length -gt 200) { 
                $event.Message.Substring(0, 200) + "..." 
            } else { 
                $event.Message 
            }
        }
    }
    
    # Get summary of most common errors
    $topSources = $events | Group-Object -Property ProviderName | 
                  Sort-Object -Property Count -Descending |
                  Select-Object -First 5 |
                  ForEach-Object { @{ source = $_.Name; count = $_.Count } }
    
    # Build suggestions
    $suggestions = @()
    if ($criticalCount -gt 0) {
        $suggestions += "Found $criticalCount CRITICAL events - immediate attention recommended"
    }
    if ($errorCount -gt 0) {
        $suggestions += "Found $errorCount errors in the past $Hours hours"
    }
    if ($warningCount -gt 0) {
        $suggestions += "Found $warningCount warnings"
    }
    if ($eventList.Count -eq 0) {
        $suggestions += "No events matching criteria found in the past $Hours hours"
    }
    
    # Add specific suggestions based on common error sources
    foreach ($source in $topSources) {
        if ($source.source -match "Disk|Storage") {
            $suggestions += "Disk-related errors detected - check drive health with CrystalDiskInfo"
        } elseif ($source.source -match "WHEA|Hardware") {
            $suggestions += "Hardware errors detected - check temperatures and hardware connections"
        } elseif ($source.source -match "Service Control|Services") {
            $suggestions += "Service failures detected - run 'services.msc' to check service status"
        } elseif ($source.source -match "Kernel") {
            $suggestions += "Kernel events detected - may indicate driver or hardware issues"
        }
    }
    
    $data = @{
        log_name = $LogName
        time_range_hours = $Hours
        filter_level = $Level
        total_events = $eventList.Count
        critical_count = $criticalCount
        error_count = $errorCount
        warning_count = $warningCount
        top_sources = $topSources
        events = $eventList
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @(
        "Run as Administrator for full log access",
        "Check Event Viewer manually: eventvwr.msc"
    )
}
