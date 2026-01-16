# flush_dns.ps1 - Flush DNS cache on Windows
# Usage: .\flush_dns.ps1 [-Test]

param(
    [Parameter(Mandatory = $false)]
    [switch]$Test
)

# Import common functions
. "$PSScriptRoot\common.ps1"

# Handle test mode
if ($Test -or (Test-IsTestMode -Args $args)) {
    Output-TestResponse -ScriptName "flush_dns"
    exit 0
}

try {
    $commandsRun = @()
    $errors = @()
    $success = $false
    
    # Method 1: ipconfig /flushdns
    try {
        $result = ipconfig /flushdns 2>&1
        $commandsRun += "ipconfig /flushdns"
        if ($result -match "Successfully") {
            $success = $true
        }
    }
    catch {
        $errors += $_.Exception.Message
    }
    
    # Method 2: Clear-DnsClientCache (PowerShell cmdlet)
    try {
        Clear-DnsClientCache -ErrorAction Stop
        $commandsRun += "Clear-DnsClientCache"
        $success = $true
    }
    catch {
        $errors += $_.Exception.Message
    }
    
    # Method 3: Also register DNS (helps with name resolution issues)
    try {
        $result = ipconfig /registerdns 2>&1
        $commandsRun += "ipconfig /registerdns"
    }
    catch {
        # Non-critical, don't add to errors
    }
    
    # Build suggestions
    $suggestions = @()
    if ($success) {
        $suggestions += "DNS cache flushed successfully"
        $suggestions += "Cached DNS entries have been cleared"
        $suggestions += "New DNS lookups will query DNS servers directly"
    } else {
        $suggestions += "DNS cache flush may have failed"
        $suggestions += "Try running as Administrator"
    }
    
    $data = @{
        success = $success
        commands_run = $commandsRun
        errors = $errors
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @("Run as Administrator")
}
