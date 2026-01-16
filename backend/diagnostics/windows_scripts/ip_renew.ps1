# ip_renew.ps1 - Renew DHCP lease on Windows
# Usage: .\ip_renew.ps1 [-Interface <name>] [-Test]

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
    Output-TestResponse -ScriptName "ip_renew"
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
    
    # Renew DHCP
    ipconfig /renew $Interface 2>&1 | Out-Null
    
    # Wait for DHCP to complete
    Start-Sleep -Seconds 3
    
    # Verify renewal
    $newConfig = Get-NetIPAddress -InterfaceAlias $Interface -AddressFamily IPv4 -ErrorAction SilentlyContinue
    $newIp = if ($newConfig) { $newConfig.IPAddress } else { $null }
    $gateway = Get-DefaultGateway
    
    $success = $false
    $currentState = "unknown"
    
    if ($newIp -and -not $newIp.StartsWith("169.254.")) {
        $success = $true
        $currentState = "has_valid_ip"
    } elseif ($newIp -and $newIp.StartsWith("169.254.")) {
        $currentState = "apipa"
    } else {
        $currentState = "no_ip"
    }
    
    # Build suggestions
    $suggestions = @()
    if ($success) {
        $suggestions += "DHCP lease renewed successfully"
        if ($newIp -ne $prevIp) {
            $suggestions += "IP changed from $prevIp to $newIp"
        } else {
            $suggestions += "IP address: $newIp (unchanged)"
        }
        if ($gateway) { $suggestions += "Gateway: $gateway" }
    } elseif ($currentState -eq "apipa") {
        $suggestions += "Obtained APIPA address (169.254.x.x) - DHCP server unreachable"
        $suggestions += "Check physical network connection"
        $suggestions += "Verify DHCP server is running on network"
    } else {
        $suggestions += "DHCP renewal failed"
        $suggestions += "Check network connection"
        $suggestions += "Try: ipconfig /renew `"$Interface`""
    }
    
    $data = @{
        interface = $Interface
        previous_ip = $prevIp
        current_ip = $newIp
        gateway = $gateway
        current_state = $currentState
        success = $success
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @("Run as Administrator")
}
