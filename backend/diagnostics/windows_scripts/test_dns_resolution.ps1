# test_dns_resolution.ps1 - Test DNS resolution on Windows
# Usage: .\test_dns_resolution.ps1 [-Hostnames <comma_separated>] [-DnsServer <ip>] [-Test]

param(
    [Parameter(Mandatory = $false)]
    [string]$Hostnames = "google.com,cloudflare.com",
    
    [Parameter(Mandatory = $false)]
    [string]$DnsServer = "",
    
    [Parameter(Mandatory = $false)]
    [switch]$Test
)

# Import common functions
. "$PSScriptRoot\common.ps1"

# Handle test mode
if ($Test -or (Test-IsTestMode -Args $args)) {
    Output-TestResponse -ScriptName "test_dns_resolution"
    exit 0
}

try {
    # Split hostnames
    $hosts = $Hostnames -split ','
    
    $results = @()
    $resolvedCount = 0
    $totalTime = 0
    $dnsUsed = $null
    
    foreach ($hostname in $hosts) {
        $hostname = $hostname.Trim()
        $startTime = Get-Date
        
        # Resolve DNS
        $resolved = $false
        $ipAddresses = @()
        $errorMsg = $null
        $dnsServerUsed = $null
        
        try {
            if ($DnsServer) {
                $dnsResult = Resolve-DnsName -Name $hostname -Server $DnsServer -Type A -ErrorAction Stop
            } else {
                $dnsResult = Resolve-DnsName -Name $hostname -Type A -ErrorAction Stop
            }
            
            foreach ($record in $dnsResult) {
                if ($record.Type -eq 'A') {
                    $ipAddresses += $record.IPAddress
                    $resolved = $true
                }
            }
            
            # Get DNS server used (from first result if available)
            if ($dnsResult -and $dnsResult[0].QueryType) {
                $dnsServerUsed = if ($DnsServer) { $DnsServer } else { "system" }
                if (-not $dnsUsed) { $dnsUsed = $dnsServerUsed }
            }
        }
        catch {
            $errorMsg = $_.Exception.Message
            if ($errorMsg -match "NXDOMAIN|not exist") {
                $errorMsg = "NXDOMAIN - domain not found"
            } elseif ($errorMsg -match "timeout|timed out") {
                $errorMsg = "DNS request timed out"
            }
        }
        
        $endTime = Get-Date
        $resolutionTime = [math]::Round(($endTime - $startTime).TotalMilliseconds)
        
        if ($resolved) {
            $resolvedCount++
            $totalTime += $resolutionTime
        }
        
        $results += @{
            hostname = $hostname
            resolved = $resolved
            ip_addresses = $ipAddresses
            dns_server_used = $dnsServerUsed
            record_type = if ($resolved) { "A" } else { $null }
            resolution_time_ms = if ($resolved) { $resolutionTime } else { $null }
            error = $errorMsg
        }
    }
    
    $dnsWorking = $resolvedCount -gt 0
    $avgTime = if ($resolvedCount -gt 0) { [math]::Round($totalTime / $resolvedCount, 1) } else { $null }
    
    # Build suggestions
    $suggestions = @()
    if (-not $dnsWorking) {
        $suggestions += "DNS resolution is not working"
        $suggestions += "If ping_dns succeeded, this is a DNS-specific issue"
        $suggestions += "Try changing DNS server to 8.8.8.8 or 1.1.1.1"
        $suggestions += "On Windows: Network adapter settings > IPv4 > DNS server addresses"
    } elseif ($resolvedCount -lt $hosts.Count) {
        $failedHosts = ($results | Where-Object { -not $_.resolved } | ForEach-Object { $_.hostname }) -join ', '
        $suggestions += "DNS works but some domains failed: $failedHosts"
        $suggestions += "These domains may not exist or may be blocked"
    }
    
    $data = @{
        hosts_tested = $hosts.Count
        hosts_resolved = $resolvedCount
        dns_working = $dnsWorking
        results = $results
        avg_resolution_time_ms = $avgTime
        dns_server = $dnsUsed
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @("Check DNS configuration")
}
