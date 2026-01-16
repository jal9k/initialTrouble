# check_adapter_status.ps1 - Check network adapter status on Windows
# Usage: .\check_adapter_status.ps1 [-InterfaceName <name>] [-Test]

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
    Output-TestResponse -ScriptName "check_adapter_status"
    exit 0
}

try {
    # Get network adapters
    $adapters = Get-NetAdapter -ErrorAction SilentlyContinue
    
    if ($InterfaceName) {
        $adapters = $adapters | Where-Object { $_.Name -eq $InterfaceName }
    }
    
    if (-not $adapters) {
        Output-Failure -Error "No network adapters found" -Suggestions @(
            "Check if network adapters are installed",
            "Run 'Get-NetAdapter' to see available adapters"
        )
        exit 1
    }
    
    $adapterList = @()
    $activeCount = 0
    $connectedCount = 0
    $primaryInterface = $null
    
    foreach ($adapter in $adapters) {
        $status = if ($adapter.Status -eq "Up") { "up" } else { "down" }
        $isConnected = $adapter.MediaConnectionState -eq 1
        
        # Check if has IP
        $hasIp = $false
        $ipConfig = Get-NetIPAddress -InterfaceIndex $adapter.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue
        if ($ipConfig) {
            $hasIp = $true
        }
        
        # Determine type
        $type = "ethernet"
        if ($adapter.Name -match "Wi-?Fi|Wireless|WLAN") {
            $type = "wireless"
        } elseif ($adapter.Name -match "Bluetooth") {
            $type = "bluetooth"
        } elseif ($adapter.InterfaceDescription -match "Virtual|VPN|TAP") {
            $type = "virtual"
        }
        
        $adapterInfo = @{
            name = $adapter.Name
            display_name = $adapter.InterfaceDescription
            status = $status
            type = $type
            mac_address = $adapter.MacAddress
            has_ip = $hasIp
            is_connected = $isConnected
        }
        $adapterList += $adapterInfo
        
        # Count stats (exclude virtual)
        if ($type -ne "virtual") {
            if ($status -eq "up") { $activeCount++ }
            if ($isConnected) { $connectedCount++ }
            if ($hasIp -and $isConnected -and -not $primaryInterface) {
                $primaryInterface = $adapter.Name
            }
        }
    }
    
    $hasNetworkConnection = $connectedCount -gt 0
    
    # Build suggestions
    $suggestions = @()
    if ($activeCount -eq 0) {
        $suggestions += "All network adapters are disabled"
        $suggestions += "ACTION: Call enable_wifi to enable the WiFi adapter"
        $suggestions += "Enable adapter: Control Panel > Network and Sharing Center > Change adapter settings"
    } elseif ($connectedCount -eq 0) {
        $suggestions += "No adapters are connected to a network"
        $suggestions += "Check WiFi connection or Ethernet cable"
    }
    
    $data = @{
        adapters = $adapterList
        active_count = $activeCount
        connected_count = $connectedCount
        has_network_connection = $hasNetworkConnection
        primary_interface = $primaryInterface
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @("Check PowerShell permissions")
}
