# ping_address.ps1 - Ping any specified address on Windows
# Usage: .\ping_address.ps1 -Host <host> [-Count <n>] [-Test]

param(
    [Parameter(Mandatory = $false)]
    [string]$HostAddress = "",
    
    [Parameter(Mandatory = $false)]
    [int]$Count = 4,
    
    [Parameter(Mandatory = $false)]
    [switch]$Test
)

# Import common functions
. "$PSScriptRoot\common.ps1"

# Handle test mode
if ($Test -or (Test-IsTestMode -Args $args)) {
    Output-TestResponse -ScriptName "ping_address"
    exit 0
}

if (-not $HostAddress) {
    Output-Failure -Error "Host address is required" -Suggestions @("Provide an IP address or hostname to ping")
    exit 1
}

try {
    # Run ping
    $pingResults = Test-Connection -ComputerName $HostAddress -Count $Count -ErrorAction SilentlyContinue
    
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
        $suggestions += "Host '$HostAddress' is not responding to ping"
        $suggestions += "Verify the hostname or IP address is correct"
        $suggestions += "The host may be blocking ICMP ping requests"
        $suggestions += "Check if you have internet connectivity (run ping_dns)"
        $suggestions += "If this is a website, try test_dns_resolution instead"
    } elseif ($packetLoss -gt 0) {
        $suggestions += "Intermittent connectivity to $HostAddress ($([math]::Round($packetLoss, 1))% packet loss)"
        $suggestions += "Network congestion or unstable connection detected"
        $suggestions += "Consider running traceroute to identify the problem hop"
    } elseif ($avgTime -and $avgTime -gt 200) {
        $suggestions += "High latency detected ($($avgTime)ms average)"
    }
    
    $data = @{
        host = $HostAddress
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
