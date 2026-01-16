# Common helper functions for Windows diagnostic scripts
# Dot-source this file in other scripts: . "$PSScriptRoot\common.ps1"

# ============================================================================
# JSON Output Helpers
# ============================================================================

function Output-Success {
    <#
    .SYNOPSIS
        Output a success JSON response
    .PARAMETER Data
        Hashtable of data to include in the response
    .PARAMETER Suggestions
        Array of suggestion strings
    #>
    param(
        [Parameter(Mandatory = $false)]
        [hashtable]$Data = @{},
        
        [Parameter(Mandatory = $false)]
        [string[]]$Suggestions = @()
    )
    
    $response = @{
        success = $true
        data = $Data
        error = $null
        suggestions = $Suggestions
    }
    
    $response | ConvertTo-Json -Depth 10 -Compress
}

function Output-Failure {
    <#
    .SYNOPSIS
        Output a failure JSON response
    .PARAMETER Error
        Error message string
    .PARAMETER Suggestions
        Array of suggestion strings
    .PARAMETER Data
        Optional hashtable of partial data
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$Error,
        
        [Parameter(Mandatory = $false)]
        [string[]]$Suggestions = @(),
        
        [Parameter(Mandatory = $false)]
        [hashtable]$Data = @{}
    )
    
    $response = @{
        success = $false
        data = $Data
        error = $Error
        suggestions = $Suggestions
    }
    
    $response | ConvertTo-Json -Depth 10 -Compress
}

# ============================================================================
# Network Helpers
# ============================================================================

function Get-DefaultGateway {
    <#
    .SYNOPSIS
        Get the default gateway IP address
    #>
    $route = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($route) {
        return $route.NextHop
    }
    return $null
}

function Get-PrimaryInterface {
    <#
    .SYNOPSIS
        Get the primary network interface name
    #>
    $route = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($route) {
        $adapter = Get-NetAdapter -InterfaceIndex $route.InterfaceIndex -ErrorAction SilentlyContinue
        if ($adapter) {
            return $adapter.Name
        }
    }
    return $null
}

function Test-InterfaceExists {
    <#
    .SYNOPSIS
        Check if a network interface exists
    .PARAMETER InterfaceName
        Name of the interface to check
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$InterfaceName
    )
    
    $adapter = Get-NetAdapter -Name $InterfaceName -ErrorAction SilentlyContinue
    return $null -ne $adapter
}

# ============================================================================
# Test Mode Support
# ============================================================================

function Test-IsTestMode {
    <#
    .SYNOPSIS
        Check if script is running in test mode
    .PARAMETER Args
        Command line arguments to check for --test or -Test
    #>
    param(
        [Parameter(Mandatory = $false)]
        [string[]]$Args = @()
    )
    
    return ($Args -contains '--test') -or ($Args -contains '-Test') -or ($env:TEST_MODE -eq '1')
}

function Output-TestResponse {
    <#
    .SYNOPSIS
        Output a test response for CI validation
    .PARAMETER ScriptName
        Name of the script being tested
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptName
    )
    
    Output-Success -Data @{
        test_mode = $true
        script = $ScriptName
    } -Suggestions @("Test mode - no actual diagnostic performed")
}

# ============================================================================
# Admin Check
# ============================================================================

function Test-IsAdmin {
    <#
    .SYNOPSIS
        Check if the current process has administrator privileges
    #>
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
