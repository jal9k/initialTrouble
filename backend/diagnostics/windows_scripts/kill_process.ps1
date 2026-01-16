# kill_process.ps1 - Kill a process by name or PID on Windows
# Usage: .\kill_process.ps1 -Process <name_or_pid> [-Force] [-Test]

param(
    [Parameter(Mandatory = $false)]
    [string]$Process = "",
    
    [Parameter(Mandatory = $false)]
    [switch]$Force,
    
    [Parameter(Mandatory = $false)]
    [switch]$Test
)

# Import common functions
. "$PSScriptRoot\common.ps1"

# Handle test mode
if ($Test -or (Test-IsTestMode -Args $args)) {
    Output-TestResponse -ScriptName "kill_process"
    exit 0
}

if (-not $Process) {
    Output-Failure -Error "Process name or PID is required" -Suggestions @("Usage: kill_process.ps1 -Process <name_or_pid>")
    exit 1
}

try {
    $killedProcesses = @()
    $killCount = 0
    $failCount = 0
    $isPid = $Process -match '^\d+$'
    
    if ($isPid) {
        # Kill by PID
        $pid = [int]$Process
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        
        if (-not $proc) {
            Output-Failure -Error "Process with PID $pid not found" -Suggestions @("The process may have already terminated")
            exit 1
        }
        
        $procName = $proc.ProcessName
        
        try {
            if ($Force) {
                Stop-Process -Id $pid -Force -ErrorAction Stop
            } else {
                Stop-Process -Id $pid -ErrorAction Stop
            }
            
            Start-Sleep -Seconds 1
            
            # Verify kill
            $stillRunning = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($stillRunning) {
                $failCount++
                $killedProcesses += @{
                    pid = $pid
                    name = $procName
                    killed = $false
                    error = "Process still running"
                }
            } else {
                $killCount++
                $killedProcesses += @{
                    pid = $pid
                    name = $procName
                    killed = $true
                    error = $null
                }
            }
        }
        catch {
            $failCount++
            $killedProcesses += @{
                pid = $pid
                name = $procName
                killed = $false
                error = $_.Exception.Message
            }
        }
    }
    else {
        # Kill by name
        $procs = Get-Process -Name $Process -ErrorAction SilentlyContinue
        
        if (-not $procs) {
            Output-Failure -Error "No processes found matching '$Process'" -Suggestions @(
                "Check the process name and try again",
                "Use Get-Process to see running processes"
            )
            exit 1
        }
        
        foreach ($proc in $procs) {
            try {
                if ($Force) {
                    Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                } else {
                    Stop-Process -Id $proc.Id -ErrorAction Stop
                }
                
                Start-Sleep -Milliseconds 500
                
                # Verify kill
                $stillRunning = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
                if ($stillRunning) {
                    $failCount++
                    $killedProcesses += @{
                        pid = $proc.Id
                        name = $proc.ProcessName
                        killed = $false
                        error = "Process still running"
                    }
                } else {
                    $killCount++
                    $killedProcesses += @{
                        pid = $proc.Id
                        name = $proc.ProcessName
                        killed = $true
                        error = $null
                    }
                }
            }
            catch {
                $failCount++
                $killedProcesses += @{
                    pid = $proc.Id
                    name = $proc.ProcessName
                    killed = $false
                    error = $_.Exception.Message
                }
            }
        }
    }
    
    $success = $killCount -gt 0
    
    # Build suggestions
    $suggestions = @()
    if ($success) {
        $suggestions += "Successfully killed $killCount process(es)"
        if ($failCount -gt 0) {
            $suggestions += "Failed to kill $failCount process(es)"
        }
    } else {
        $suggestions += "Failed to kill any processes"
        if (-not $Force) {
            $suggestions += "Try with -Force for forceful termination"
        } else {
            $suggestions += "Process may be protected or running as SYSTEM"
            $suggestions += "Try running as Administrator"
        }
    }
    
    $data = @{
        target = $Process
        was_pid = $isPid
        force = $Force.IsPresent
        processes_killed = $killCount
        processes_failed = $failCount
        processes = $killedProcesses
        success = $success
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @("Run as Administrator")
}
