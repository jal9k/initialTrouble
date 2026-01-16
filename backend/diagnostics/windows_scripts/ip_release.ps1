# ip_release.ps1 - Release DHCP lease on Windows
# Usage: .\ip_release.ps1 [-Interface <name>] [-Test]

param(
    [Parameter(Mandatory = $false)]
    [string]$Interface = "",
    
    [Parameter(Mandatory = $false)]
    [switch]$Test
)

# Import common functions
. "$PSScriptRoot\common.ps1"

# Handle test mode
if ($Test -or (Test-IsTestMode -Args $args)) {
    Output-TestResponse -ScriptName "ip_release"
    exit 0
}

try {
    # Get current IP configuration
    $currentConfig = $null
    
    if ($Interface) {
        $currentConfig = Get-NetIPAddress -InterfaceAlias $Interface -AddressFamily IPv4 -ErrorAction SilentlyContinue
    } else {
        # Get primary interface (default route interface)
        $defaultRoute = Get-NetRoute -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($defaultRoute) {
            $adapter = Get-NetAdapter -InterfaceIndex $defaultRoute.InterfaceIndex -ErrorAction SilentlyContinue
            $Interface = $adapter.Name
            $currentConfig = Get-NetIPAddress -InterfaceIndex $defaultRoute.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue
        }
    }
    
    if (-not $Interface) {
        Output-Failure -Error "Could not determine network interface" -Suggestions @(
            "Specify an interface name",
            "Run 'Get-NetAdapter' to see available adapters"
        )
        exit 1
    }
    
    $prevIp = if ($currentConfig) { $currentConfig.IPAddress } else { $null }
    $prevState = if ($prevIp) { "has_ip" } else { "no_ip" }
    
    # Release DHCP
    ipconfig /release $Interface 2>&1 | Out-Null
    $exitCode = $LASTEXITCODE
    
    # Wait for release
    Start-Sleep -Seconds 1
    
    # Verify release
    $newConfig = Get-NetIPAddress -InterfaceAlias $Interface -AddressFamily IPv4 -ErrorAction SilentlyContinue
    $newIp = if ($newConfig) { $newConfig.IPAddress } else { $null }
    
    $success = (-not $newIp) -or ($newIp -ne $prevIp)
    $currentState = if ($newIp) { "still_has_ip" } else { "released" }
    
    # Build suggestions
    $suggestions = @()
    if ($success) {
        $suggestions += "DHCP lease released successfully"
        if ($prevIp) { $suggestions += "Previous IP: $prevIp" }
        $suggestions += "Run ip_renew to obtain a new lease"
    } else {
        $suggestions += "DHCP release may not have completed"
        $suggestions += "Try running as Administrator"
        $suggestions += "Or: ipconfig /release `"$Interface`""
    }
    
    $data = @{
        interface = $Interface
        previous_ip = $prevIp
        current_ip = $newIp
        previous_state = $prevState
        current_state = $currentState
        success = $success
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @("Run as Administrator")
}
