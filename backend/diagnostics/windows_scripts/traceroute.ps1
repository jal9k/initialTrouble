# traceroute.ps1 - Trace route to destination on Windows
# Usage: .\traceroute.ps1 -Host <host> [-MaxHops <n>] [-Test]

param(
    [Parameter(Mandatory = $false)]
    [string]$HostAddress = "",
    
    [Parameter(Mandatory = $false)]
    [int]$MaxHops = 30,
    
    [Parameter(Mandatory = $false)]
    [switch]$Test
)

# Import common functions
. "$PSScriptRoot\common.ps1"

# Handle test mode
if ($Test -or (Test-IsTestMode -Args $args)) {
    Output-TestResponse -ScriptName "traceroute"
    exit 0
}

if (-not $HostAddress) {
    Output-Failure -Error "Destination host is required" -Suggestions @("Provide an IP address or hostname to trace")
    exit 1
}

try {
    # Run tracert
    $traceOutput = tracert -h $MaxHops -w 3000 $HostAddress 2>&1
    
    $hops = @()
    $destinationReached = $false
    
    foreach ($line in $traceOutput) {
        $line = $line.Trim()
        if (-not $line) { continue }
        if ($line -match "^Tracing|^over a maximum|^Trace complete") { continue }
        
        # Parse hop line
        if ($line -match "^\s*(\d+)") {
            $hopNumber = [int]$Matches[1]
            
            # Check for timeout
            if ($line -match "\*\s+\*\s+\*") {
                $hops += @{
                    hop_number = $hopNumber
                    timed_out = $true
                    address = $null
                    hostname = $null
                    times_ms = @()
                    avg_time_ms = $null
                }
                continue
            }
            
            # Extract times and address
            $times = @()
            $matches = [regex]::Matches($line, "(\d+)\s*ms")
            foreach ($match in $matches) {
                $times += [double]$match.Groups[1].Value
            }
            
            # Extract IP address
            $address = $null
            $hostname = $null
            
            if ($line -match "\[?(\d+\.\d+\.\d+\.\d+)\]?") {
                $address = $Matches[1]
            }
            
            # Extract hostname (before IP in brackets)
            if ($line -match "([a-zA-Z0-9.-]+)\s+\[$address\]") {
                $hostname = $Matches[1]
            }
            
            $avgTime = $null
            if ($times.Count -gt 0) {
                $avgTime = [math]::Round(($times | Measure-Object -Average).Average, 1)
            }
            
            $hops += @{
                hop_number = $hopNumber
                timed_out = $false
                address = $address
                hostname = $hostname
                times_ms = $times
                avg_time_ms = $avgTime
            }
        }
    }
    
    # Check if destination reached
    if ($hops.Count -gt 0) {
        $lastHop = $hops[-1]
        if (-not $lastHop.timed_out -and $lastHop.address) {
            $destinationReached = $true
        }
    }
    
    # Build suggestions
    $suggestions = @()
    if (-not $destinationReached) {
        $suggestions += "Could not reach destination '$HostAddress'"
        $suggestions += "Check where the trace stops to identify the problem"
        if ($hops.Count -gt 0 -and $hops[-1].timed_out) {
            $suggestions += "The last hop timed out - may indicate firewall blocking"
        }
    } elseif ($hops.Count -gt 15) {
        $suggestions += "Route has many hops ($($hops.Count)) - may affect latency"
    }
    
    $data = @{
        destination = $HostAddress
        destination_reached = $destinationReached
        total_hops = $hops.Count
        max_hops_setting = $MaxHops
        hops = $hops
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @("Check network connectivity")
}
