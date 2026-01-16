# ping_dns.ps1 - Ping external DNS servers on Windows
# Usage: .\ping_dns.ps1 [-Count <n>] [-Test]

param(
    [Parameter(Mandatory = $false)]
    [int]$Count = 4,
    
    [Parameter(Mandatory = $false)]
    [switch]$Test
)

# Import common functions
. "$PSScriptRoot\common.ps1"

# Handle test mode
if ($Test -or (Test-IsTestMode -Args $args)) {
    Output-TestResponse -ScriptName "ping_dns"
    exit 0
}

try {
    # DNS servers to test
    $dnsServers = @(
        @{ ip = "8.8.8.8"; name = "Google Public DNS" },
        @{ ip = "1.1.1.1"; name = "Cloudflare DNS" }
    )
    
    $results = @()
    $serversReachable = 0
    $bestServer = $null
    $bestLatency = [double]::MaxValue
    
    foreach ($server in $dnsServers) {
        $ip = $server.ip
        $name = $server.name
        
        # Run ping
        $pingResults = Test-Connection -ComputerName $ip -Count $Count -ErrorAction SilentlyContinue
        
        $packetsSent = $Count
        $packetsReceived = 0
        $avgTime = $null
        
        if ($pingResults) {
            $packetsReceived = $pingResults.Count
            $times = $pingResults | ForEach-Object { $_.ResponseTime }
            if ($times.Count -gt 0) {
                $avgTime = ($times | Measure-Object -Average).Average
                $avgTime = [math]::Round($avgTime, 1)
            }
        }
        
        $reachable = $packetsReceived -gt 0
        $packetLoss = if ($packetsSent -gt 0) { (($packetsSent - $packetsReceived) / $packetsSent) * 100 } else { 100 }
        
        if ($reachable) {
            $serversReachable++
            if ($avgTime -and $avgTime -lt $bestLatency) {
                $bestLatency = $avgTime
                $bestServer = $ip
            }
        }
        
        $results += @{
            server = $ip
            name = $name
            reachable = $reachable
            packets_sent = $packetsSent
            packets_received = $packetsReceived
            packet_loss_percent = [math]::Round($packetLoss, 1)
            avg_time_ms = $avgTime
        }
    }
    
    $internetAccessible = $serversReachable -gt 0
    
    # Build suggestions
    $suggestions = @()
    if (-not $internetAccessible) {
        $suggestions += "Cannot reach external DNS servers - no internet connectivity"
        $suggestions += "If gateway ping succeeded, this is a WAN issue"
        $suggestions += "Check if modem is connected to ISP"
        $suggestions += "Contact ISP if modem shows connected but no internet"
    } elseif ($serversReachable -lt $dnsServers.Count) {
        $suggestions += "Internet is accessible but some DNS servers are unreachable"
        if ($bestServer) {
            $suggestions += "Consider using the reachable DNS server ($bestServer)"
        }
    }
    
    $data = @{
        servers_tested = $dnsServers.Count
        servers_reachable = $serversReachable
        internet_accessible = $internetAccessible
        results = $results
        best_server = $bestServer
        best_latency_ms = if ($bestLatency -lt [double]::MaxValue) { $bestLatency } else { $null }
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @("Check network connectivity")
}
