# fix_dell_audio.ps1 - Fix Dell audio driver issues on Windows
# Usage: .\fix_dell_audio.ps1 [-Test]

param(
    [Parameter(Mandatory = $false)]
    [switch]$Test
)

# Import common functions
. "$PSScriptRoot\common.ps1"

# Handle test mode
if ($Test -or (Test-IsTestMode -Args $args)) {
    Output-TestResponse -ScriptName "fix_dell_audio"
    exit 0
}

# Check for admin rights
if (-not (Test-IsAdmin)) {
    Output-Failure -Error "Administrator privileges required" -Suggestions @(
        "Run PowerShell as Administrator",
        "Right-click PowerShell and select 'Run as administrator'"
    )
    exit 1
}

try {
    $actionsPerformed = @()
    $errorsEncountered = @()
    $driverInfo = @{}
    
    # Find Dell audio devices
    $dellAudio = Get-PnpDevice -Class AudioEndpoint, MEDIA -ErrorAction SilentlyContinue | 
                 Where-Object { $_.FriendlyName -match "Dell|Realtek|Waves" }
    
    # Also check for Realtek audio (common on Dell systems)
    $realtekAudio = Get-PnpDevice -FriendlyName "*Realtek*" -ErrorAction SilentlyContinue
    
    $allAudio = @($dellAudio) + @($realtekAudio) | Where-Object { $_ } | Select-Object -Unique
    
    if (-not $allAudio) {
        Output-Failure -Error "No Dell/Realtek audio devices found" -Suggestions @(
            "This may not be a Dell system or audio drivers are not installed",
            "Check Device Manager for audio devices"
        )
        exit 1
    }
    
    foreach ($device in $allAudio) {
        $driverInfo[$device.FriendlyName] = @{
            status = $device.Status
            instance_id = $device.InstanceId
        }
    }
    
    # Step 1: Disable and re-enable audio devices
    foreach ($device in $allAudio) {
        if ($device.Status -eq "OK") {
            try {
                # Disable
                Disable-PnpDevice -InstanceId $device.InstanceId -Confirm:$false -ErrorAction Stop
                $actionsPerformed += "Disabled: $($device.FriendlyName)"
                
                Start-Sleep -Seconds 2
                
                # Re-enable
                Enable-PnpDevice -InstanceId $device.InstanceId -Confirm:$false -ErrorAction Stop
                $actionsPerformed += "Re-enabled: $($device.FriendlyName)"
            }
            catch {
                $errorsEncountered += "Failed to reset $($device.FriendlyName): $($_.Exception.Message)"
            }
        }
    }
    
    # Step 2: Restart Windows Audio services
    $audioServices = @(
        "AudioSrv",      # Windows Audio
        "AudioEndpointBuilder"  # Windows Audio Endpoint Builder
    )
    
    foreach ($svc in $audioServices) {
        try {
            $service = Get-Service -Name $svc -ErrorAction SilentlyContinue
            if ($service) {
                Restart-Service -Name $svc -Force -ErrorAction Stop
                $actionsPerformed += "Restarted service: $svc"
            }
        }
        catch {
            $errorsEncountered += "Failed to restart $svc: $($_.Exception.Message)"
        }
    }
    
    # Step 3: Clear audio cache
    $audioCachePath = "$env:LOCALAPPDATA\Microsoft\Windows\Audio"
    if (Test-Path $audioCachePath) {
        try {
            Remove-Item -Path "$audioCachePath\*" -Recurse -Force -ErrorAction Stop
            $actionsPerformed += "Cleared audio cache"
        }
        catch {
            $errorsEncountered += "Failed to clear audio cache: $($_.Exception.Message)"
        }
    }
    
    # Step 4: Check for Waves MaxxAudio (common on Dell)
    $wavesProcess = Get-Process -Name "*Waves*" -ErrorAction SilentlyContinue
    if ($wavesProcess) {
        try {
            Stop-Process -Name "*Waves*" -Force -ErrorAction SilentlyContinue
            $actionsPerformed += "Stopped Waves MaxxAudio process"
            
            Start-Sleep -Seconds 2
            
            # Try to restart it
            $wavesPath = "C:\Program Files\Waves\MaxxAudio\WavesSvc64.exe"
            if (Test-Path $wavesPath) {
                Start-Process $wavesPath -ErrorAction SilentlyContinue
                $actionsPerformed += "Restarted Waves MaxxAudio"
            }
        }
        catch {
            $errorsEncountered += "Failed to restart Waves: $($_.Exception.Message)"
        }
    }
    
    $success = ($actionsPerformed.Count -gt 0) -and ($errorsEncountered.Count -eq 0)
    
    # Build suggestions
    $suggestions = @()
    if ($success) {
        $suggestions += "Dell audio repair completed successfully"
        $suggestions += "Test audio playback to verify fix"
        $suggestions += "If issues persist, try reinstalling audio drivers from Dell Support"
    } else {
        $suggestions += "Some repair actions may have failed"
        $suggestions += "Check Device Manager for audio device status"
        $suggestions += "Consider downloading latest drivers from Dell Support website"
    }
    
    if ($errorsEncountered.Count -gt 0) {
        $suggestions += "Errors occurred - a system restart may help"
    }
    
    $data = @{
        success = $success
        devices_found = $driverInfo
        actions_performed = $actionsPerformed
        errors = $errorsEncountered
        requires_restart = ($errorsEncountered.Count -gt 0)
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @(
        "Run as Administrator",
        "Check if audio devices are present in Device Manager"
    )
}
