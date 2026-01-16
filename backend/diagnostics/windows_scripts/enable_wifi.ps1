# enable_wifi.ps1 - Enable/disable WiFi on Windows
# Usage: .\enable_wifi.ps1 [-Action <on|off>] [-Interface <name>] [-Test]

param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("on", "off")]
    [string]$Action = "on",
    
    [Parameter(Mandatory = $false)]
    [string]$Interface = "",
    
    [Parameter(Mandatory = $false)]
    [switch]$Test
)

# Import common functions
. "$PSScriptRoot\common.ps1"

# Handle test mode
if ($Test -or (Test-IsTestMode -Args $args)) {
    Output-TestResponse -ScriptName "enable_wifi"
    exit 0
}

try {
    # Find WiFi adapter
    $wifiAdapter = $null
    
    if ($Interface) {
        $wifiAdapter = Get-NetAdapter -Name $Interface -ErrorAction SilentlyContinue
    } else {
        $wifiAdapter = Get-NetAdapter | Where-Object {
            $_.InterfaceDescription -match "Wi-?Fi|Wireless|802\.11"
        } | Select-Object -First 1
    }
    
    if (-not $wifiAdapter) {
        Output-Failure -Error "Could not find WiFi adapter" -Suggestions @(
            "WiFi hardware may not be present",
            "Check Device Manager for wireless adapters"
        )
        exit 1
    }
    
    $previousState = if ($wifiAdapter.Status -eq "Up") { "enabled" } else { "disabled" }
    $targetState = if ($Action -eq "on") { "enabled" } else { "disabled" }
    
    # Execute action
    if ($Action -eq "on") {
        Enable-NetAdapter -Name $wifiAdapter.Name -Confirm:$false -ErrorAction Stop
    } else {
        Disable-NetAdapter -Name $wifiAdapter.Name -Confirm:$false -ErrorAction Stop
    }
    
    # Wait for state change
    Start-Sleep -Seconds 2
    
    # Verify result
    $wifiAdapter = Get-NetAdapter -Name $wifiAdapter.Name -ErrorAction SilentlyContinue
    $currentState = if ($wifiAdapter.Status -eq "Up") { "enabled" } else { "disabled" }
    
    $success = $currentState -eq $targetState
    
    # Build suggestions
    $suggestions = @()
    if ($success) {
        if ($targetState -eq "enabled") {
            $suggestions += "WiFi adapter enabled successfully"
            $suggestions += "Device should now scan for available networks"
            $suggestions += "May need to manually connect to a network"
        } else {
            $suggestions += "WiFi adapter disabled successfully"
        }
    } else {
        $suggestions += "Failed to change WiFi state"
        $suggestions += "Try running as Administrator"
        $suggestions += "Check if WiFi is blocked by airplane mode"
    }
    
    $data = @{
        action = $Action
        interface = $wifiAdapter.Name
        previous_state = $previousState
        current_state = $currentState
        target_state = $targetState
        success = $success
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @("Run as Administrator", "Check WiFi adapter status in Device Manager")
}
