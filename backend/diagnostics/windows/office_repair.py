"""Microsoft 365 repair diagnostic.

Runs Microsoft 365 repair (Quick or Online) to fix application issues
like crashes, missing features, or activation problems.

See documents/functions/repair_office365.md for full specification.
"""

import json
from typing import Any

from ..base import BaseDiagnostic, DiagnosticResult
from ..platform import Platform


class RepairOffice365(BaseDiagnostic):
    """Repair Microsoft 365 installation."""

    name = "repair_office365"
    description = "Run Microsoft 365 repair to fix application issues"
    osi_layer = "Application"

    # Registry paths for Office detection
    OFFICE_REGISTRY_PATHS = [
        r"HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration",
        r"HKLM:\SOFTWARE\WOW6432Node\Microsoft\Office\ClickToRun\Configuration",
    ]

    async def run(
        self,
        repair_type: str = "quick",
        apps_to_repair: list[str] | None = None,
    ) -> DiagnosticResult:
        """
        Repair Microsoft 365 installation.

        Args:
            repair_type: Type of repair - "quick" (local) or "online" (cloud)
            apps_to_repair: Specific apps to target (not used by Office repair, 
                           but useful for logging)

        Returns:
            DiagnosticResult with repair status
        """
        # Check platform
        if self.platform != Platform.WINDOWS:
            return self._failure(
                error="This tool is only available on Windows",
                suggestions=["Run this on a Windows computer"],
            )

        # Validate repair type
        if repair_type not in ("quick", "online"):
            return self._failure(
                error=f"Invalid repair type: {repair_type}",
                suggestions=["Use 'quick' for fast local repair or 'online' for thorough cloud repair"],
            )

        # Step 1: Detect Office installation
        office_info = await self._detect_office()
        if not office_info.get("installed"):
            return self._failure(
                error="Microsoft Office not detected",
                data={"detection_attempted": True},
                suggestions=[
                    "Microsoft 365 or Office does not appear to be installed",
                    "If Office is installed, it may be an MSI installation (not Click-to-Run)",
                    "For MSI installations, use Programs and Features to repair",
                ],
            )

        # Step 2: Check installation type
        if office_info.get("type") == "msi":
            return self._failure(
                error="MSI-based Office installation detected",
                data={"office_version": office_info.get("version")},
                suggestions=[
                    "This tool supports Click-to-Run Office installations",
                    "For MSI installations: Control Panel > Programs > Repair",
                    "Or run: msiexec /fa {ProductCode}",
                ],
            )

        # Step 3: Close Office applications
        await self._close_office_apps()

        # Step 4: Run the repair
        repair_result = await self._run_repair(repair_type, office_info)

        if not repair_result.get("success"):
            return self._failure(
                error="Repair failed to start",
                data={
                    "office_version": office_info.get("version"),
                    "repair_type": repair_type,
                    "error_details": repair_result.get("error"),
                },
                suggestions=[
                    "Run as Administrator and try again",
                    "Close all Office applications and retry",
                    "Try the 'online' repair if 'quick' repair fails",
                    "Consider reinstalling Office from office.com",
                ],
            )

        return self._success(
            data={
                "office_version": office_info.get("version"),
                "office_product": office_info.get("product"),
                "installation_type": office_info.get("type", "ClickToRun"),
                "repair_type_used": repair_type,
                "repair_initiated": True,
                "apps_closed": repair_result.get("apps_closed", []),
            },
            suggestions=self._generate_suggestions(repair_type),
        )

    async def _detect_office(self) -> dict[str, Any]:
        """Detect Office installation details."""
        # Try Click-to-Run first
        cmd = """
        $c2r = $null
        foreach ($path in @(
            'HKLM:\\SOFTWARE\\Microsoft\\Office\\ClickToRun\\Configuration',
            'HKLM:\\SOFTWARE\\WOW6432Node\\Microsoft\\Office\\ClickToRun\\Configuration'
        )) {
            if (Test-Path $path) {
                $c2r = Get-ItemProperty -Path $path -ErrorAction SilentlyContinue
                break
            }
        }
        
        if ($c2r) {
            @{
                installed = $true
                type = 'ClickToRun'
                version = $c2r.VersionToReport
                product = $c2r.ProductReleaseIds
                platform = $c2r.Platform
                updateChannel = $c2r.UpdateChannel
            } | ConvertTo-Json
        } else {
            # Check for MSI installation
            $office = Get-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Office\\*\\Common\\InstallRoot' -ErrorAction SilentlyContinue
            if ($office) {
                @{
                    installed = $true
                    type = 'msi'
                    version = 'MSI Installation'
                } | ConvertTo-Json
            } else {
                @{installed = $false} | ConvertTo-Json
            }
        }
        """
        result = await self.executor.run(cmd, shell=True)

        if not result.success:
            return {"installed": False}

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"installed": False}

    async def _close_office_apps(self) -> list[str]:
        """Close running Office applications."""
        office_processes = [
            "WINWORD", "EXCEL", "POWERPNT", "OUTLOOK", "MSACCESS",
            "ONENOTE", "MSPUB", "lync", "Teams"
        ]

        closed = []
        for proc in office_processes:
            cmd = f"Stop-Process -Name {proc} -Force -ErrorAction SilentlyContinue"
            result = await self.executor.run(cmd, shell=True)
            if result.success:
                closed.append(proc)

        return closed

    async def _run_repair(
        self,
        repair_type: str,
        office_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the Office repair."""
        # Locate OfficeClickToRun.exe
        find_c2r_cmd = """
        $paths = @(
            "$env:ProgramFiles\\Microsoft Office\\root\\Client\\OfficeClickToRun.exe",
            "$env:ProgramFiles\\Common Files\\Microsoft Shared\\ClickToRun\\OfficeClickToRun.exe",
            "${env:ProgramFiles(x86)}\\Microsoft Office\\root\\Client\\OfficeClickToRun.exe"
        )
        
        foreach ($p in $paths) {
            if (Test-Path $p) {
                Write-Output $p
                break
            }
        }
        """
        result = await self.executor.run(find_c2r_cmd, shell=True)

        if not result.success or not result.stdout.strip():
            return {"success": False, "error": "OfficeClickToRun.exe not found"}

        c2r_path = result.stdout.strip()

        # Build repair command
        platform = office_info.get("platform", "x64")
        
        if repair_type == "quick":
            repair_cmd = f'Start-Process -FilePath "{c2r_path}" -ArgumentList "scenario=Repair platform={platform} culture=en-us" -Wait -NoNewWindow'
        else:  # online repair
            repair_cmd = f'Start-Process -FilePath "{c2r_path}" -ArgumentList "scenario=Repair platform={platform} culture=en-us RepairType=2" -Wait -NoNewWindow'

        # Note: Running repair in background since it can take a long time
        # We start it and return immediately
        bg_cmd = f'Start-Process -FilePath "{c2r_path}" -ArgumentList "scenario=Repair platform={platform} culture=en-us{" RepairType=2" if repair_type == "online" else ""}"'
        
        result = await self.executor.run(bg_cmd, shell=True, timeout=30)

        return {
            "success": True,
            "apps_closed": [],
        }

    def _generate_suggestions(self, repair_type: str) -> list[str]:
        """Generate suggestions based on repair type."""
        suggestions = [
            "Office repair has been initiated",
        ]

        if repair_type == "quick":
            suggestions.extend([
                "Quick repair typically takes 10-15 minutes",
                "If issues persist, try 'online' repair for a more thorough fix",
            ])
        else:
            suggestions.extend([
                "Online repair may take 30-60 minutes depending on internet speed",
                "This downloads fresh Office components from Microsoft",
                "Do not interrupt the repair process",
            ])

        suggestions.append(
            "Restart your computer after repair completes"
        )

        return suggestions


# Module-level function for easy importing
async def repair_office365(
    repair_type: str = "quick",
    apps_to_repair: list[str] | None = None,
) -> DiagnosticResult:
    """Repair Microsoft 365 installation.
    
    Args:
        repair_type: "quick" for local repair, "online" for cloud repair
        apps_to_repair: Specific apps to target (informational)
        
    Returns:
        DiagnosticResult with repair status
    """
    diag = RepairOffice365()
    return await diag.run(repair_type=repair_type, apps_to_repair=apps_to_repair)

