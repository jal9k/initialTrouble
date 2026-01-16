# repair_office365.ps1 - Repair Microsoft Office 365 installation on Windows
# Usage: .\repair_office365.ps1 [-QuickRepair] [-Test]

param(
    [Parameter(Mandatory = $false)]
    [switch]$QuickRepair,
    
    [Parameter(Mandatory = $false)]
    [switch]$Test
)

# Import common functions
. "$PSScriptRoot\common.ps1"

# Handle test mode
if ($Test -or (Test-IsTestMode -Args $args)) {
    Output-TestResponse -ScriptName "repair_office365"
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
    $officeInfo = @{}
    
    # Find Office installation
    $officeApps = Get-ItemProperty "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*" -ErrorAction SilentlyContinue |
                  Where-Object { $_.DisplayName -match "Microsoft 365|Office 365|Microsoft Office" }
    
    # Also check 32-bit registry on 64-bit systems
    $officeApps32 = Get-ItemProperty "HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*" -ErrorAction SilentlyContinue |
                    Where-Object { $_.DisplayName -match "Microsoft 365|Office 365|Microsoft Office" }
    
    $allOffice = @($officeApps) + @($officeApps32) | Where-Object { $_ } | Select-Object -First 1
    
    if (-not $allOffice) {
        Output-Failure -Error "Microsoft Office 365 not found" -Suggestions @(
            "Office 365 does not appear to be installed",
            "Install Office 365 from office.com or your organization's portal"
        )
        exit 1
    }
    
    $officeInfo = @{
        name = $allOffice.DisplayName
        version = $allOffice.DisplayVersion
        install_location = $allOffice.InstallLocation
        uninstall_string = $allOffice.UninstallString
    }
    
    # Find OfficeClickToRun.exe
    $clickToRunPath = $null
    $possiblePaths = @(
        "C:\Program Files\Common Files\Microsoft Shared\ClickToRun\OfficeClickToRun.exe",
        "C:\Program Files (x86)\Common Files\Microsoft Shared\ClickToRun\OfficeClickToRun.exe"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $clickToRunPath = $path
            break
        }
    }
    
    if (-not $clickToRunPath) {
        # Try alternative repair method using control panel
        $repairCommand = $allOffice.UninstallString -replace "/uninstall", "/repair"
        
        if ($repairCommand -and $repairCommand -ne $allOffice.UninstallString) {
            try {
                Start-Process "cmd.exe" -ArgumentList "/c $repairCommand" -Wait -NoNewWindow
                $actionsPerformed += "Initiated Office repair via uninstall string"
            }
            catch {
                $errorsEncountered += "Failed to start repair: $($_.Exception.Message)"
            }
        } else {
            Output-Failure -Error "Could not find Office Click-to-Run component" -Suggestions @(
                "Try repairing Office through Settings > Apps > Microsoft 365",
                "Or reinstall Office from office.com"
            )
            exit 1
        }
    } else {
        # Use Click-to-Run repair
        $repairType = if ($QuickRepair) { "quickrepair" } else { "repairall" }
        
        try {
            $actionsPerformed += "Starting Office repair ($repairType)..."
            
            # Run repair
            $process = Start-Process -FilePath $clickToRunPath -ArgumentList "scenario=Repair", "platform=x64", "culture=en-us", "RepairType=$repairType" -PassThru -Wait
            
            if ($process.ExitCode -eq 0) {
                $actionsPerformed += "Office repair initiated successfully"
            } else {
                $errorsEncountered += "Repair process returned exit code: $($process.ExitCode)"
            }
        }
        catch {
            $errorsEncountered += "Failed to start repair: $($_.Exception.Message)"
        }
    }
    
    # Clear Office cache
    $officeCachePaths = @(
        "$env:LOCALAPPDATA\Microsoft\Office\16.0\OfficeFileCache",
        "$env:LOCALAPPDATA\Microsoft\Office\OTele",
        "$env:APPDATA\Microsoft\Office\Recent"
    )
    
    foreach ($cachePath in $officeCachePaths) {
        if (Test-Path $cachePath) {
            try {
                Remove-Item -Path "$cachePath\*" -Recurse -Force -ErrorAction SilentlyContinue
                $actionsPerformed += "Cleared cache: $cachePath"
            }
            catch {
                # Non-critical, don't add to errors
            }
        }
    }
    
    # Reset Office activation (optional, only if issues persist)
    # This is commented out as it may require re-activation
    # cscript.exe "C:\Program Files\Microsoft Office\Office16\ospp.vbs" /rearm
    
    $success = ($actionsPerformed.Count -gt 0) -and ($errorsEncountered.Count -eq 0)
    
    # Build suggestions
    $suggestions = @()
    if ($success) {
        $suggestions += "Office 365 repair process completed"
        if (-not $QuickRepair) {
            $suggestions += "Online repair may take some time to complete in the background"
        }
        $suggestions += "Restart your computer after repair completes"
        $suggestions += "If issues persist, try online repair with -QuickRepair:$false"
    } else {
        $suggestions += "Office repair may have encountered issues"
        $suggestions += "Try repairing through Settings > Apps > Microsoft 365 > Modify"
        $suggestions += "Consider uninstalling and reinstalling Office"
    }
    
    $data = @{
        success = $success
        repair_type = if ($QuickRepair) { "quick" } else { "online" }
        office_info = $officeInfo
        actions_performed = $actionsPerformed
        errors = $errorsEncountered
        requires_restart = $true
    }
    
    Output-Success -Data $data -Suggestions $suggestions
}
catch {
    Output-Failure -Error $_.Exception.Message -Suggestions @(
        "Run as Administrator",
        "Try repairing Office through Settings > Apps"
    )
}
