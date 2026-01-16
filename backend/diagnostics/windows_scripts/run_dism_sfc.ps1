# run_dism_sfc.ps1 - Run DISM and SFC system file checker on Windows
# Usage: .\run_dism_sfc.ps1 [-SfcOnly] [-DismOnly] [-Test]

param(
    [Parameter(Mandatory = $false)]
    [switch]$SfcOnly,
    
    [Parameter(Mandatory = $false)]
    [switch]$DismOnly,
    
    [Parameter(Mandatory = $false)]
    [switch]$Test
)

# Import common functions
. "$PSScriptRoot\common.ps1"

# Handle test mode
if ($Test -or (Test-IsTestMode -Args $args)) {
    Output-TestResponse -ScriptName "run_dism_sfc"
    exit 0
}

# Check for admin rights
if (-not (Test-IsAdmin)) {
    Output-Failure -Error "Administrator privileges required" -Suggestions @(
        "Run PowerShell as Administrator",
        "Right-click PowerShell and select 'Run as administrator'"
    )
    exit 1
}

try {
    $actionsPerformed = @()
    $errorsEncountered = @()
    $sfcResult = $null
    $dismResult = $null
    
    # Run DISM first (unless SfcOnly)
    if (-not $SfcOnly) {
        $actionsPerformed += "Starting DISM scan..."
        
        # Run DISM /CheckHealth first
        Write-Host "Running DISM /CheckHealth..." -ForegroundColor Cyan
        $checkHealth = dism /online /cleanup-image /checkhealth 2>&1
        $actionsPerformed += "DISM CheckHealth completed"
        
        # Run DISM /ScanHealth
        Write-Host "Running DISM /ScanHealth..." -ForegroundColor Cyan
        $scanHealth = dism /online /cleanup-image /scanhealth 2>&1
        $actionsPerformed += "DISM ScanHealth completed"
        
        # Run DISM /RestoreHealth
        Write-Host "Running DISM /RestoreHealth (this may take a while)..." -ForegroundColor Cyan
        $restoreHealth = dism /online /cleanup-image /restorehealth 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            $dismResult = @{
                success = $true
                exit_code = $LASTEXITCODE
                message = "DISM completed successfully - no corruption found or repairs made"
            }
            $actionsPerformed += "DISM RestoreHealth completed successfully"
        } else {
            $dismResult = @{
                success = $false
                exit_code = $LASTEXITCODE
                message = "DISM encountered issues"
            }
            $errorsEncountered += "DISM returned exit code: $LASTEXITCODE"
        }
    }
    
    # Run SFC (unless DismOnly)
    if (-not $DismOnly) {
        $actionsPerformed += "Starting System File Checker..."
        
        Write-Host "Running SFC /scannow (this may take a while)..." -ForegroundColor Cyan
        $sfcOutput = sfc /scannow 2>&1
        
        $sfcExitCode = $LASTEXITCODE
        $sfcMessage = ""
        
        if ($sfcOutput -match "did not find any integrity violations") {
            $sfcMessage = "No integrity violations found"
            $sfcSuccess = $true
        } elseif ($sfcOutput -match "successfully repaired") {
            $sfcMessage = "Corrupted files found and repaired"
            $sfcSuccess = $true
        } elseif ($sfcOutput -match "found corrupt files but was unable to fix") {
            $sfcMessage = "Found corrupt files but unable to repair"
            $sfcSuccess = $false
            $errorsEncountered += "SFC found unrepairable corruption"
        } else {
            $sfcMessage = "SFC completed"
            $sfcSuccess = ($sfcExitCode -eq 0)
        }
        
        $sfcResult = @{
            success = $sfcSuccess
            exit_code = $sfcExitCode
            message = $sfcMessage
        }
        $actionsPerformed += "SFC scan completed: $sfcMessage"
    }
    
    $overallSuccess = ($errorsEncountered.Count -eq 0)
    
    # Build suggestions
    $suggestions = @()
    if ($overallSuccess) {
        $suggestions += "System file check completed successfully"
        $suggestions += "No critical issues found or all issues were repaired"
    } else {
        $suggestions += "Some issues were detected during the scan"
        if ($sfcResult -and -not $sfcResult.success) {
            $suggestions += "Try running DISM /RestoreHealth again before SFC"
            $suggestions += "A system restore or Windows repair install may be needed"
        }
    }
    $suggestions += "A system restart is recommended after these repairs"
    
    $data = @{
        success = $overallSuccess
        ran_dism = (-not $SfcOnly)
        ran_sfc = (-not $DismOnly)
        dism_result = $dismResult
        sfc_result = $sfcResult
        actions_performed = $actionsPerformed
        errors = $errorsEncountered
        requires_restart = $true
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @(
        "Run as Administrator",
        "Ensure Windows is not in Safe Mode"
    )
}
