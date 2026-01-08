"""Windows system file repair diagnostic.

Runs DISM and SFC to repair Windows system file corruption.

See documents/functions/run_dism_sfc.md for full specification.
"""

import re
from typing import Any

from ..base import BaseDiagnostic, DiagnosticResult
from ..platform import Platform


class RunDismSfc(BaseDiagnostic):
    """Run DISM and SFC to repair Windows system files."""

    name = "run_dism_sfc"
    description = "Run DISM and SFC to repair Windows system file corruption"
    osi_layer = "Application"

    async def run(
        self,
        run_dism: bool = True,
        run_sfc: bool = True,
        check_only: bool = False,
    ) -> DiagnosticResult:
        """
        Run Windows system file repair tools.

        Args:
            run_dism: Run DISM /RestoreHealth first (default: True)
            run_sfc: Run SFC /scannow after DISM (default: True)
            check_only: Only scan for issues, don't repair (default: False)

        Returns:
            DiagnosticResult with repair results
        """
        # Check platform
        if self.platform != Platform.WINDOWS:
            return self._failure(
                error="This tool is only available on Windows",
                suggestions=["Run this on a Windows computer"],
            )

        # Check for Administrator privileges
        is_admin = await self._check_admin()
        if not is_admin:
            return self._failure(
                error="Administrator privileges required",
                suggestions=[
                    "Run as Administrator to use this tool",
                    "Right-click the application and select 'Run as administrator'",
                    "Or open an elevated PowerShell prompt",
                ],
            )

        results = {
            "dism_result": None,
            "dism_issues_found": 0,
            "dism_issues_fixed": 0,
            "sfc_result": None,
            "sfc_files_repaired": [],
            "reboot_required": False,
            "logs": {},
        }

        # Step 1: Run DISM if requested
        if run_dism:
            dism_result = await self._run_dism(check_only)
            results.update(dism_result)

        # Step 2: Run SFC if requested
        if run_sfc:
            sfc_result = await self._run_sfc(check_only)
            results.update(sfc_result)

        # Determine overall success
        success = True
        error = None

        if results.get("dism_result") == "error":
            success = False
            error = "DISM encountered an error"
        elif results.get("sfc_result") == "error":
            success = False
            error = "SFC encountered an error"
        elif results.get("dism_result") == "unrepairable" or results.get("sfc_result") == "unrepairable":
            success = False
            error = "Some corruption could not be repaired"

        if success:
            return self._success(
                data=results,
                suggestions=self._generate_suggestions(results),
            )
        else:
            return self._failure(
                error=error,
                data=results,
                suggestions=self._generate_suggestions(results),
            )

    async def _check_admin(self) -> bool:
        """Check if running with Administrator privileges."""
        cmd = """
        $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
        $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        """
        result = await self.executor.run(cmd, shell=True)
        return result.success and "True" in result.stdout

    async def _run_dism(self, check_only: bool) -> dict[str, Any]:
        """Run DISM health check and repair."""
        results = {
            "dism_result": None,
            "dism_issues_found": 0,
            "dism_issues_fixed": 0,
        }

        # First, run a quick health check
        check_cmd = "DISM /Online /Cleanup-Image /CheckHealth"
        check_result = await self.executor.run(check_cmd, shell=True, timeout=60)

        if not check_result.success:
            results["dism_result"] = "error"
            return results

        # Check if component store is healthy
        if "The component store is repairable" in check_result.stdout:
            results["dism_issues_found"] = 1
        elif "No component store corruption detected" in check_result.stdout:
            results["dism_result"] = "healthy"
            return results

        if check_only:
            # Run ScanHealth for more detailed scan
            scan_cmd = "DISM /Online /Cleanup-Image /ScanHealth"
            scan_result = await self.executor.run(scan_cmd, shell=True, timeout=300)
            
            if "component store corruption" in scan_result.stdout.lower():
                results["dism_result"] = "corruption_found"
                results["dism_issues_found"] = self._count_dism_issues(scan_result.stdout)
            else:
                results["dism_result"] = "healthy"
            return results

        # Run RestoreHealth to repair
        repair_cmd = "DISM /Online /Cleanup-Image /RestoreHealth"
        repair_result = await self.executor.run(repair_cmd, shell=True, timeout=1800)  # 30 min timeout

        if not repair_result.success:
            if "Error" in repair_result.stdout or "Error" in repair_result.stderr:
                results["dism_result"] = "error"
            else:
                results["dism_result"] = "unrepairable"
        elif "The restore operation completed successfully" in repair_result.stdout:
            results["dism_result"] = "repaired"
            results["dism_issues_fixed"] = results["dism_issues_found"]
        elif "No component store corruption detected" in repair_result.stdout:
            results["dism_result"] = "healthy"
        else:
            results["dism_result"] = "completed"

        results["logs"] = {"dism_log": r"%WINDIR%\Logs\DISM\dism.log"}

        return results

    async def _run_sfc(self, check_only: bool) -> dict[str, Any]:
        """Run System File Checker."""
        results = {
            "sfc_result": None,
            "sfc_files_repaired": [],
            "reboot_required": False,
        }

        if check_only:
            # SFC doesn't have a scan-only mode, so we use verifyonly
            cmd = "sfc /verifyonly"
        else:
            cmd = "sfc /scannow"

        # SFC can take a long time
        result = await self.executor.run(cmd, shell=True, timeout=1800)  # 30 min timeout

        if not result.success:
            results["sfc_result"] = "error"
            return results

        output = result.stdout

        # Parse SFC output
        if "did not find any integrity violations" in output:
            results["sfc_result"] = "no_violations"
        elif "successfully repaired" in output.lower():
            results["sfc_result"] = "repaired"
            results["sfc_files_repaired"] = self._parse_sfc_repairs(output)
        elif "found corrupt files but was unable to fix" in output.lower():
            results["sfc_result"] = "unrepairable"
        elif "found corrupt files and successfully repaired them" in output.lower():
            results["sfc_result"] = "repaired"
            results["reboot_required"] = True
        else:
            results["sfc_result"] = "completed"

        # Check if reboot is required
        if "pending" in output.lower() or "reboot" in output.lower():
            results["reboot_required"] = True

        results["logs"]["cbs_log"] = r"%WINDIR%\Logs\CBS\CBS.log"

        return results

    def _count_dism_issues(self, output: str) -> int:
        """Count issues found by DISM."""
        # Look for patterns like "X corruption(s)"
        match = re.search(r"(\d+)\s+corruption", output.lower())
        if match:
            return int(match.group(1))
        return 1 if "corruption" in output.lower() else 0

    def _parse_sfc_repairs(self, output: str) -> list[str]:
        """Parse list of files repaired by SFC."""
        files = []
        # SFC output typically shows files like:
        # 2023-12-23 10:30:15, Info  CBS  Repaired file: [path]
        for line in output.split("\n"):
            if "Repaired" in line or "repaired" in line:
                # Extract file path if present
                match = re.search(r":\\[^\s]+", line)
                if match:
                    files.append(match.group(0))
        return files[:10]  # Limit to first 10

    def _generate_suggestions(self, results: dict) -> list[str]:
        """Generate suggestions based on results."""
        suggestions = []

        dism_result = results.get("dism_result")
        sfc_result = results.get("sfc_result")

        if dism_result == "healthy" and sfc_result == "no_violations":
            suggestions.append("System files are healthy. No repairs were needed.")
        elif dism_result == "repaired" or sfc_result == "repaired":
            suggestions.append("System file repairs were successful.")
            if results.get("reboot_required"):
                suggestions.append("Please restart your computer to complete the repairs.")
        elif dism_result == "unrepairable" or sfc_result == "unrepairable":
            suggestions.append(
                "Some corruption could not be automatically repaired."
            )
            suggestions.append(
                "Consider running an in-place upgrade repair or reset Windows."
            )
            suggestions.append(
                "Check the CBS.log for details: %WINDIR%\\Logs\\CBS\\CBS.log"
            )
        elif dism_result == "error" or sfc_result == "error":
            suggestions.append(
                "An error occurred during repair. Check the logs for details."
            )
            suggestions.append(
                "Try running in Safe Mode or from Windows Recovery Environment."
            )

        if results.get("reboot_required"):
            suggestions.append("A restart is required to apply all changes.")

        return suggestions


# Module-level function for easy importing
async def run_dism_sfc(
    run_dism: bool = True,
    run_sfc: bool = True,
    check_only: bool = False,
) -> DiagnosticResult:
    """Run DISM and SFC to repair Windows system files.
    
    Args:
        run_dism: Run DISM /RestoreHealth
        run_sfc: Run SFC /scannow
        check_only: Only scan, don't repair
        
    Returns:
        DiagnosticResult with repair results
    """
    diag = RunDismSfc()
    return await diag.run(run_dism=run_dism, run_sfc=run_sfc, check_only=check_only)

