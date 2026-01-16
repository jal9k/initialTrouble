# ping_gateway.ps1 - Ping the default gateway on Windows
# Usage: .\ping_gateway.ps1 [-Gateway <ip>] [-Count <n>] [-Test]

param(
    [Parameter(Mandatory = $false)]
    [string]$Gateway = "",
    
    [Parameter(Mandatory = $false)]
    [int]$Count = 4,
    
    [Parameter(Mandatory = $false)]
    [switch]$Test
)

# Import common functions
. "$PSScriptRoot\common.ps1"

# Handle test mode
if ($Test -or (Test-IsTestMode -Args $args)) {
    Output-TestResponse -ScriptName "ping_gateway"
    exit 0
}

try {
    # Auto-detect gateway if not provided
    if (-not $Gateway) {
        $Gateway = Get-DefaultGateway
    }
    
    if (-not $Gateway) {
        Output-Failure -Error "Could not determine default gateway" -Suggestions @(
            "Run get_ip_config to check network configuration",
            "Verify network cable or WiFi connection"
        )
        exit 1
    }
    
    # Run ping
    $pingResults = Test-Connection -ComputerName $Gateway -Count $Count -ErrorAction SilentlyContinue
    
    $packetsSent = $Count
    $packetsReceived = 0
    $results = @()
    $times = @()
    
    if ($pingResults) {
        foreach ($result in $pingResults) {
            $packetsReceived++
            $time = $result.ResponseTime
            $times += $time
            $results += @{
                sequence = $results.Count
                success = $true
                time_ms = $time
            }
        }
    }
    
    # Add failed pings
    for ($i = $packetsReceived; $i -lt $Count; $i++) {
        $results += @{
            sequence = $i
            success = $false
            time_ms = $null
        }
    }
    
    $reachable = $packetsReceived -gt 0
    $packetLoss = if ($packetsSent -gt 0) { (($packetsSent - $packetsReceived) / $packetsSent) * 100 } else { 100 }
    
    $minTime = $null
    $avgTime = $null
    $maxTime = $null
    
    if ($times.Count -gt 0) {
        $stats = $times | Measure-Object -Minimum -Maximum -Average
        $minTime = $stats.Minimum
        $avgTime = [math]::Round($stats.Average, 1)
        $maxTime = $stats.Maximum
    }
    
    # Build suggestions
    $suggestions = @()
    if (-not $reachable) {
        $suggestions += "Gateway is not responding"
        $suggestions += "Check if router/modem is powered on"
        $suggestions += "Verify Ethernet cable is connected or WiFi is associated"
        $suggestions += "Try restarting the router"
        $suggestions += "Check if gateway IP is correct: $Gateway"
    } elseif ($packetLoss -gt 0) {
        $suggestions += "Intermittent connectivity ($([math]::Round($packetLoss, 1))% packet loss)"
        $suggestions += "Check WiFi signal strength if on wireless"
        $suggestions += "Try a different Ethernet cable if wired"
    }
    
    $data = @{
        gateway_ip = $Gateway
        reachable = $reachable
        packets_sent = $packetsSent
        packets_received = $packetsReceived
        packet_loss_percent = [math]::Round($packetLoss, 1)
        min_time_ms = $minTime
        avg_time_ms = $avgTime
        max_time_ms = $maxTime
        results = $results
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @("Check network connectivity")
}
