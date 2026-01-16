# Test diagnostic scripts for Windows
# Usage: pwsh -File scripts/test_diagnostics.ps1

$ErrorActionPreference = "Stop"

$ScriptDir = "backend/diagnostics/windows_scripts"

if (-not (Test-Path $ScriptDir)) {
    Write-Host "❌ Script directory not found: $ScriptDir" -ForegroundColor Red
    exit 1
}

$Failed = 0
$Passed = 0
$Skipped = 0

Write-Host "=============================================="
Write-Host "Testing Windows diagnostic scripts..."
Write-Host "=============================================="
Write-Host ""

Get-ChildItem "$ScriptDir/*.ps1" | ForEach-Object {
    $name = $_.BaseName
    
    # Skip common.ps1
    if ($name -eq "common") { return }
    
    Write-Host -NoNewline ("  Testing {0,-30} " -f "$name...")
    
    try {
        $output = & $_.FullName -Test 2>&1 | Out-String
        
        # Try to parse as JSON
        try {
            $json = $output | ConvertFrom-Json -ErrorAction Stop
            
            if ($null -ne $json.success) {
                Write-Host "✓ PASS" -ForegroundColor Green
                $Passed++
            } else {
                Write-Host "✗ FAIL (missing success field)" -ForegroundColor Red
                Write-Host "    Output: $($output.Substring(0, [Math]::Min(100, $output.Length)))..."
                $Failed++
            }
        }
        catch {
            Write-Host "✗ FAIL (invalid JSON)" -ForegroundColor Red
            Write-Host "    Output: $($output.Substring(0, [Math]::Min(100, $output.Length)))..."
            $Failed++
        }
    }
    catch {
        Write-Host "✗ FAIL ($($_.Exception.Message))" -ForegroundColor Red
        $Failed++
    }
}

Write-Host ""
Write-Host "=============================================="
Write-Host "Results: $Passed passed, $Failed failed, $Skipped skipped"
Write-Host "=============================================="

if ($Failed -gt 0) { exit 1 }
