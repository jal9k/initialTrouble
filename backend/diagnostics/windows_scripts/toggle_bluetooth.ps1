# toggle_bluetooth.ps1 - Enable/disable Bluetooth on Windows
# Usage: .\toggle_bluetooth.ps1 [-Action <on|off>] [-Test]

param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("on", "off")]
    [string]$Action = "on",
    
    [Parameter(Mandatory = $false)]
    [switch]$Test
)

# Import common functions
. "$PSScriptRoot\common.ps1"

# Handle test mode
if ($Test -or (Test-IsTestMode -Args $args)) {
    Output-TestResponse -ScriptName "toggle_bluetooth"
    exit 0
}

try {
    # Find Bluetooth adapter
    $btAdapter = Get-NetAdapter | Where-Object {
        $_.InterfaceDescription -match "Bluetooth"
    } | Select-Object -First 1
    
    # Also check PnP devices for Bluetooth
    $btDevice = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | 
                Where-Object { $_.Status -ne "Error" } |
                Select-Object -First 1
    
    if (-not $btAdapter -and -not $btDevice) {
        Output-Failure -Error "Could not find Bluetooth adapter" -Suggestions @(
            "Bluetooth hardware may not be present",
            "Check Device Manager for Bluetooth radios"
        )
        exit 1
    }
    
    $previousState = "unknown"
    $method = "unknown"
    
    # Determine current state and method
    if ($btAdapter) {
        $previousState = if ($btAdapter.Status -eq "Up") { "enabled" } else { "disabled" }
        $method = "net_adapter"
    } elseif ($btDevice) {
        $previousState = if ($btDevice.Status -eq "OK") { "enabled" } else { "disabled" }
        $method = "pnp_device"
    }
    
    $targetState = if ($Action -eq "on") { "enabled" } else { "disabled" }
    $success = $false
    $currentState = "unknown"
    
    # Execute action based on available method
    if ($btAdapter) {
        if ($Action -eq "on") {
            Enable-NetAdapter -Name $btAdapter.Name -Confirm:$false -ErrorAction Stop
        } else {
            Disable-NetAdapter -Name $btAdapter.Name -Confirm:$false -ErrorAction Stop
        }
        
        Start-Sleep -Seconds 2
        
        $btAdapter = Get-NetAdapter -Name $btAdapter.Name -ErrorAction SilentlyContinue
        $currentState = if ($btAdapter.Status -eq "Up") { "enabled" } else { "disabled" }
    }
    elseif ($btDevice) {
        if ($Action -eq "on") {
            Enable-PnpDevice -InstanceId $btDevice.InstanceId -Confirm:$false -ErrorAction Stop
        } else {
            Disable-PnpDevice -InstanceId $btDevice.InstanceId -Confirm:$false -ErrorAction Stop
        }
        
        Start-Sleep -Seconds 2
        
        $btDevice = Get-PnpDevice -InstanceId $btDevice.InstanceId -ErrorAction SilentlyContinue
        $currentState = if ($btDevice.Status -eq "OK") { "enabled" } else { "disabled" }
    }
    
    $success = $currentState -eq $targetState
    
    # Build suggestions
    $suggestions = @()
    if ($success) {
        if ($targetState -eq "enabled") {
            $suggestions += "Bluetooth enabled successfully"
            $suggestions += "Device is now discoverable"
        } else {
            $suggestions += "Bluetooth disabled successfully"
        }
    } else {
        $suggestions += "Failed to toggle Bluetooth"
        $suggestions += "Try running as Administrator"
        $suggestions += "Check Windows Settings > Devices > Bluetooth"
    }
    
    $data = @{
        action = $Action
        previous_state = $previousState
        current_state = $currentState
        target_state = $targetState
        method = $method
        success = $success
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @("Run as Administrator", "Check Device Manager for Bluetooth")
}
