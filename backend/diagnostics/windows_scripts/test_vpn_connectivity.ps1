# test_vpn_connectivity.ps1 - Test VPN connection status on Windows
# Usage: .\test_vpn_connectivity.ps1 [-VpnType <type>] [-TestEndpoint <ip>] [-Test]

param(
    [Parameter(Mandatory = $false)]
    [string]$VpnType = "",
    
    [Parameter(Mandatory = $false)]
    [string]$TestEndpoint = "",
    
    [Parameter(Mandatory = $false)]
    [switch]$Test
)

# Import common functions
. "$PSScriptRoot\common.ps1"

# Handle test mode
if ($Test -or (Test-IsTestMode -Args $args)) {
    Output-TestResponse -ScriptName "test_vpn_connectivity"
    exit 0
}

try {
    $vpnConnected = $false
    $vpnInterface = $null
    $vpnIp = $null
    $detectedType = "unknown"
    $detectionMethod = "interface_scan"
    
    # Method 1: Check for VPN adapters
    $adapters = Get-NetAdapter | Where-Object { 
        $_.InterfaceDescription -match "VPN|TAP|WireGuard|OpenVPN|Cisco|Pulse|Palo Alto|FortiClient|F5|Zscaler" -or
        $_.Name -match "VPN|TAP"
    }
    
    foreach ($adapter in $adapters) {
        if ($adapter.Status -eq "Up") {
            $vpnConnected = $true
            $vpnInterface = $adapter.Name
            
            # Get VPN IP
            $ipConfig = Get-NetIPAddress -InterfaceIndex $adapter.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue
            if ($ipConfig) {
                $vpnIp = $ipConfig.IPAddress
            }
            
            # Detect type
            if ($adapter.InterfaceDescription -match "TAP|OpenVPN") {
                $detectedType = "openvpn"
            } elseif ($adapter.InterfaceDescription -match "WireGuard") {
                $detectedType = "wireguard"
            } elseif ($adapter.InterfaceDescription -match "Cisco") {
                $detectedType = "cisco"
            } else {
                $detectedType = "system_vpn"
            }
            break
        }
    }
    
    # Method 2: Check Windows VPN connections using rasdial
    if (-not $vpnConnected) {
        $rasOutput = rasdial 2>&1
        if ($rasOutput -match "Connected to") {
            $vpnConnected = $true
            $detectionMethod = "rasdial"
            $detectedType = "windows_vpn"
            $vpnInterface = "RAS"
        }
    }
    
    # Method 3: Check Get-VpnConnection
    if (-not $vpnConnected) {
        $vpnConnections = Get-VpnConnection -ErrorAction SilentlyContinue | Where-Object { $_.ConnectionStatus -eq "Connected" }
        if ($vpnConnections) {
            $vpnConnected = $true
            $vpnInterface = $vpnConnections[0].Name
            $detectedType = "windows_vpn"
            $detectionMethod = "get_vpnconnection"
        }
    }
    
    if (-not $vpnConnected) {
        $data = @{
            vpn_connected = $false
            vpn_type = $null
            vpn_interface = $null
            vpn_ip = $null
            routes_active = $false
            dns_via_vpn = $false
            internal_reachable = $null
            detection_method = $detectionMethod
        }
        
        Output-Success -Data $data -Suggestions @(
            "No active VPN connection detected",
            "Connect to your VPN and try again",
            "Check VPN client application is running"
        )
        exit 0
    }
    
    # Check VPN routes
    $routesActive = $false
    $routes = Get-NetRoute -ErrorAction SilentlyContinue
    foreach ($route in $routes) {
        if ($route.DestinationPrefix -match "^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.|0\.0\.0\.0/1|128\.0\.0\.0/1)") {
            $routesActive = $true
            break
        }
    }
    
    # Check DNS via VPN
    $dnsViaVpn = $false
    $dnsServers = Get-DnsClientServerAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | 
                  Select-Object -ExpandProperty ServerAddresses
    foreach ($dns in $dnsServers) {
        if ($dns -match "^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)") {
            $dnsViaVpn = $true
            break
        }
    }
    
    # Test internal endpoint if provided
    $internalReachable = $null
    if ($TestEndpoint) {
        $pingResult = Test-Connection -ComputerName $TestEndpoint -Count 1 -Quiet -ErrorAction SilentlyContinue
        $internalReachable = $pingResult
    }
    
    # Use provided VPN type if given
    if ($VpnType) { $detectedType = $VpnType }
    
    # Build suggestions
    $suggestions = @()
    if ($vpnIp) { $suggestions += "VPN connected with IP: $vpnIp" }
    if (-not $routesActive) { $suggestions += "VPN routes may not be configured. Check VPN client settings." }
    if (-not $dnsViaVpn) { $suggestions += "DNS does not appear to go through VPN. This may cause DNS leaks." }
    if ($internalReachable -eq $false) {
        $suggestions += "Cannot reach internal endpoint $TestEndpoint. Check VPN routing."
    } elseif ($internalReachable -eq $true) {
        $suggestions += "Successfully reached internal endpoint: $TestEndpoint"
    }
    
    $data = @{
        vpn_connected = $true
        vpn_type = $detectedType
        vpn_interface = $vpnInterface
        vpn_ip = $vpnIp
        routes_active = $routesActive
        dns_via_vpn = $dnsViaVpn
        internal_reachable = $internalReachable
        detection_method = $detectionMethod
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @("Check VPN configuration")
}
