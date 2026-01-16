# get_ip_config.ps1 - Get IP configuration on Windows
# Usage: .\get_ip_config.ps1 [-InterfaceName <name>] [-Test]

param(
    [Parameter(Mandatory = $false)]
    [string]$InterfaceName = "",
    
    [Parameter(Mandatory = $false)]
    [switch]$Test
)

# Import common functions
. "$PSScriptRoot\common.ps1"

# Handle test mode
if ($Test -or (Test-IsTestMode -Args $args)) {
    Output-TestResponse -ScriptName "get_ip_config"
    exit 0
}

try {
    # Get IP configuration
    $ipConfigs = Get-NetIPConfiguration -ErrorAction SilentlyContinue
    
    if ($InterfaceName) {
        $ipConfigs = $ipConfigs | Where-Object { $_.InterfaceAlias -eq $InterfaceName }
    }
    
    $interfaceList = @()
    $hasValidIp = $false
    $hasGateway = $false
    $primaryIp = $null
    $primaryGateway = $null
    
    foreach ($config in $ipConfigs) {
        $ipv4 = $config.IPv4Address | Select-Object -First 1
        $gateway = $config.IPv4DefaultGateway | Select-Object -First 1
        $dns = $config.DNSServer | Where-Object { $_.AddressFamily -eq 2 } | ForEach-Object { $_.ServerAddresses }
        
        $ipAddress = if ($ipv4) { $ipv4.IPAddress } else { $null }
        $gatewayAddress = if ($gateway) { $gateway.NextHop } else { $null }
        
        $isApipa = $false
        if ($ipAddress -and $ipAddress.StartsWith("169.254.")) {
            $isApipa = $true
        }
        
        # Get IPv6
        $ipv6Address = $null
        $ipv6Config = $config.IPv6Address | Where-Object { -not $_.IPAddress.StartsWith("fe80::") } | Select-Object -First 1
        if ($ipv6Config) {
            $ipv6Address = $ipv6Config.IPAddress
        }
        
        $interfaceInfo = @{
            interface = $config.InterfaceAlias
            ip_address = $ipAddress
            subnet_mask = $null  # Would need prefix length conversion
            gateway = $gatewayAddress
            dns_servers = @($dns | Where-Object { $_ })
            dhcp_enabled = $true
            dhcp_server = $null
            is_apipa = $isApipa
            ipv6_address = $ipv6Address
        }
        $interfaceList += $interfaceInfo
        
        if ($ipAddress -and -not $isApipa) {
            $hasValidIp = $true
            if (-not $primaryIp) { $primaryIp = $ipAddress }
        }
        if ($gatewayAddress) {
            $hasGateway = $true
            if (-not $primaryGateway) { $primaryGateway = $gatewayAddress }
        }
    }
    
    # Build suggestions
    $suggestions = @()
    if (-not $hasValidIp) {
        $hasApipa = $interfaceList | Where-Object { $_.is_apipa } | Select-Object -First 1
        if ($hasApipa) {
            $suggestions += "APIPA address detected - DHCP failure"
            $suggestions += "Try: ipconfig /release && ipconfig /renew"
        } else {
            $suggestions += "No valid IP address assigned"
        }
    } elseif (-not $hasGateway) {
        $suggestions += "No default gateway configured"
    }
    
    $data = @{
        interfaces = $interfaceList
        has_valid_ip = $hasValidIp
        has_gateway = $hasGateway
        primary_ip = $primaryIp
        primary_gateway = $primaryGateway
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @("Check PowerShell permissions")
}
