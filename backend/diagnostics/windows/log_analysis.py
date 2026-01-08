"""Windows system log analysis diagnostic.

Analyzes Event Viewer, crash dumps, BSOD events, and Reliability Monitor
to diagnose system crashes and errors.

See documents/functions/review_system_logs.md for full specification.
"""

import json
import re
from datetime import datetime, timedelta
from typing import Any

from ..base import BaseDiagnostic, DiagnosticResult
from ..platform import Platform


class ReviewSystemLogs(BaseDiagnostic):
    """Analyze Windows system logs to diagnose crashes and errors."""

    name = "review_system_logs"
    description = "Analyze Windows Event Viewer and crash dumps"
    osi_layer = "Application"

    # Common BSOD error codes and their likely causes
    BSOD_CODES = {
        "DRIVER_IRQL_NOT_LESS_OR_EQUAL": "Driver issue - outdated or faulty driver",
        "PAGE_FAULT_IN_NONPAGED_AREA": "RAM issue or driver problem",
        "SYSTEM_SERVICE_EXCEPTION": "Driver or system file corruption",
        "KMODE_EXCEPTION_NOT_HANDLED": "Driver compatibility issue",
        "NTFS_FILE_SYSTEM": "Disk or file system corruption",
        "KERNEL_DATA_INPAGE_ERROR": "Hard drive or memory failure",
        "CRITICAL_PROCESS_DIED": "Critical system process crashed",
        "DPC_WATCHDOG_VIOLATION": "Driver taking too long - usually SSD/storage driver",
        "WHEA_UNCORRECTABLE_ERROR": "Hardware error - CPU, RAM, or motherboard",
        "MEMORY_MANAGEMENT": "RAM or virtual memory issue",
    }

    async def run(
        self,
        log_types: list[str] | None = None,
        time_range_hours: int = 72,
        severity_filter: str = "error",
    ) -> DiagnosticResult:
        """
        Analyze Windows system logs.

        Args:
            log_types: Which logs to analyze. Options: "event_viewer", "crash_dumps", 
                      "bsod", "reliability". Default: all
            time_range_hours: How far back to search (default: 72 hours)
            time_range_hours: How far back to search in hours (default: 72)
            severity_filter: Minimum severity. Options: "info", "warning", "error", 
                           "critical" (default: "error")

        Returns:
            DiagnosticResult with log analysis
        """
        # Check platform
        if self.platform != Platform.WINDOWS:
            return self._failure(
                error="This tool is only available on Windows",
                suggestions=["Run this on a Windows computer"],
            )

        # Default to all log types
        if not log_types:
            log_types = ["event_viewer", "crash_dumps", "bsod", "reliability"]

        # Validate severity
        severity_levels = ["info", "warning", "error", "critical"]
        if severity_filter not in severity_levels:
            severity_filter = "error"
        
        min_level = severity_levels.index(severity_filter)

        results = {
            "analysis_period": f"Last {time_range_hours} hours",
            "critical_events": [],
            "error_events": [],
            "warning_events": [],
            "crash_dumps_found": 0,
            "crash_dump_details": [],
            "bsod_events": [],
            "reliability_score": None,
            "top_issues": [],
            "recommendations": [],
        }

        # Analyze each log type
        if "event_viewer" in log_types:
            events = await self._analyze_event_viewer(time_range_hours, min_level)
            results["critical_events"] = events.get("critical", [])
            results["error_events"] = events.get("error", [])
            results["warning_events"] = events.get("warning", [])

        if "crash_dumps" in log_types:
            dumps = await self._analyze_crash_dumps(time_range_hours)
            results["crash_dumps_found"] = dumps.get("count", 0)
            results["crash_dump_details"] = dumps.get("details", [])

        if "bsod" in log_types:
            bsod = await self._analyze_bsod(time_range_hours)
            results["bsod_events"] = bsod

        if "reliability" in log_types:
            reliability = await self._get_reliability_score()
            results["reliability_score"] = reliability

        # Generate top issues and recommendations
        results["top_issues"] = self._rank_issues(results)
        results["recommendations"] = self._generate_recommendations(results)

        return self._success(
            data=results,
            suggestions=results["recommendations"][:5],  # Top 5 recommendations
        )

    async def _analyze_event_viewer(
        self,
        hours: int,
        min_level: int,
    ) -> dict[str, list]:
        """Analyze Event Viewer logs."""
        # Map severity levels
        level_map = {
            0: 1,  # info -> Information (4) - we won't query this
            1: 3,  # warning -> Warning
            2: 2,  # error -> Error  
            3: 1,  # critical -> Critical
        }
        
        max_level = level_map[min_level]

        cmd = f"""
        $startTime = (Get-Date).AddHours(-{hours})
        
        $events = Get-WinEvent -FilterHashtable @{{
            LogName = 'System', 'Application'
            Level = 1,2,3  # Critical, Error, Warning
            StartTime = $startTime
        }} -MaxEvents 100 -ErrorAction SilentlyContinue |
        Select-Object TimeCreated, LevelDisplayName, ProviderName, Id, Message |
        ForEach-Object {{
            @{{
                time = $_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss')
                level = $_.LevelDisplayName
                source = $_.ProviderName
                id = $_.Id
                message = $_.Message.Substring(0, [Math]::Min($_.Message.Length, 200))
            }}
        }}
        
        $events | ConvertTo-Json -Depth 3
        """
        
        result = await self.executor.run(cmd, shell=True, timeout=60)

        if not result.success:
            return {"critical": [], "error": [], "warning": []}

        try:
            events = json.loads(result.stdout) if result.stdout.strip() else []
            if isinstance(events, dict):
                events = [events]
        except json.JSONDecodeError:
            return {"critical": [], "error": [], "warning": []}

        # Categorize by level
        categorized = {"critical": [], "error": [], "warning": []}
        for event in events:
            level = event.get("level", "").lower()
            if "critical" in level:
                categorized["critical"].append(event)
            elif "error" in level:
                categorized["error"].append(event)
            elif "warning" in level:
                categorized["warning"].append(event)

        return categorized

    async def _analyze_crash_dumps(self, hours: int) -> dict[str, Any]:
        """Analyze crash dump files."""
        cmd = f"""
        $dumps = @()
        $startTime = (Get-Date).AddHours(-{hours})
        
        # Check common dump locations
        $paths = @(
            "$env:LOCALAPPDATA\\CrashDumps",
            "$env:WINDIR\\Minidump",
            "$env:WINDIR\\MEMORY.DMP"
        )
        
        foreach ($path in $paths) {{
            if (Test-Path $path) {{
                $items = Get-ChildItem -Path $path -File -ErrorAction SilentlyContinue |
                    Where-Object {{ $_.LastWriteTime -gt $startTime }}
                foreach ($item in $items) {{
                    $dumps += @{{
                        path = $item.FullName
                        name = $item.Name
                        size = $item.Length
                        created = $item.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')
                    }}
                }}
            }}
        }}
        
        @{{
            count = $dumps.Count
            details = $dumps | Select-Object -First 10
        }} | ConvertTo-Json -Depth 3
        """
        
        result = await self.executor.run(cmd, shell=True, timeout=30)

        if not result.success:
            return {"count": 0, "details": []}

        try:
            return json.loads(result.stdout) if result.stdout.strip() else {"count": 0, "details": []}
        except json.JSONDecodeError:
            return {"count": 0, "details": []}

    async def _analyze_bsod(self, hours: int) -> list[dict[str, Any]]:
        """Analyze BSOD events from Event Viewer."""
        cmd = f"""
        $startTime = (Get-Date).AddHours(-{hours})
        
        # BugCheck events (Event ID 1001 from BugCheck source)
        $bsod = Get-WinEvent -FilterHashtable @{{
            LogName = 'System'
            ProviderName = 'Microsoft-Windows-WER-SystemErrorReporting'
            Id = 1001
            StartTime = $startTime
        }} -MaxEvents 20 -ErrorAction SilentlyContinue |
        ForEach-Object {{
            # Parse the message for error code
            $msg = $_.Message
            $code = if ($msg -match 'code:\\s*(\\w+)') {{ $matches[1] }} else {{ 'Unknown' }}
            
            @{{
                time = $_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss')
                code = $code
                message = $msg.Substring(0, [Math]::Min($msg.Length, 300))
            }}
        }}
        
        $bsod | ConvertTo-Json -Depth 2
        """
        
        result = await self.executor.run(cmd, shell=True, timeout=30)

        if not result.success:
            return []

        try:
            events = json.loads(result.stdout) if result.stdout.strip() else []
            if isinstance(events, dict):
                events = [events]
            
            # Add human-readable causes
            for event in events:
                code = event.get("code", "")
                for known_code, cause in self.BSOD_CODES.items():
                    if known_code in code.upper():
                        event["likely_cause"] = cause
                        break
            
            return events
        except json.JSONDecodeError:
            return []

    async def _get_reliability_score(self) -> float | None:
        """Get Windows Reliability Monitor score."""
        cmd = """
        $reliability = Get-CimInstance -ClassName Win32_ReliabilityStabilityMetrics |
            Sort-Object -Property TimeGenerated -Descending |
            Select-Object -First 1 -Property SystemStabilityIndex
        
        if ($reliability) {
            $reliability.SystemStabilityIndex
        } else {
            'null'
        }
        """
        
        result = await self.executor.run(cmd, shell=True, timeout=30)

        if not result.success:
            return None

        try:
            score = result.stdout.strip()
            if score and score != "null":
                return float(score)
        except ValueError:
            pass

        return None

    def _rank_issues(self, results: dict) -> list[dict[str, Any]]:
        """Rank issues by frequency and severity."""
        issues = []

        # Count BSOD codes
        bsod_counts = {}
        for event in results.get("bsod_events", []):
            code = event.get("code", "Unknown")
            bsod_counts[code] = bsod_counts.get(code, 0) + 1

        for code, count in bsod_counts.items():
            issues.append({
                "type": "BSOD",
                "code": code,
                "count": count,
                "severity": "critical",
                "cause": self.BSOD_CODES.get(code, "Unknown cause"),
            })

        # Count error sources
        error_sources = {}
        for event in results.get("error_events", []):
            source = event.get("source", "Unknown")
            error_sources[source] = error_sources.get(source, 0) + 1

        for source, count in sorted(error_sources.items(), key=lambda x: -x[1])[:5]:
            issues.append({
                "type": "Error",
                "source": source,
                "count": count,
                "severity": "error",
            })

        # Sort by count (most frequent first)
        issues.sort(key=lambda x: -x.get("count", 0))
        return issues[:10]

    def _generate_recommendations(self, results: dict) -> list[str]:
        """Generate recommendations based on findings."""
        recommendations = []

        # BSOD recommendations
        bsod_events = results.get("bsod_events", [])
        if bsod_events:
            recommendations.append(
                f"Found {len(bsod_events)} blue screen event(s). Review driver updates."
            )
            
            # Specific recommendations based on codes
            for event in bsod_events[:3]:
                cause = event.get("likely_cause")
                if cause:
                    recommendations.append(f"BSOD cause: {cause}")

        # Crash dump recommendations
        if results.get("crash_dumps_found", 0) > 0:
            recommendations.append(
                f"Found {results['crash_dumps_found']} crash dump(s). "
                "Consider analyzing with WinDbg or BlueScreenView."
            )

        # Reliability score
        score = results.get("reliability_score")
        if score is not None:
            if score < 5:
                recommendations.append(
                    f"System stability score is low ({score:.1f}/10). "
                    "Consider system repair or driver updates."
                )
            elif score < 7:
                recommendations.append(
                    f"System stability score is moderate ({score:.1f}/10)."
                )
            else:
                recommendations.append(
                    f"System stability score is good ({score:.1f}/10)."
                )

        # Critical events
        if results.get("critical_events"):
            recommendations.append(
                f"Found {len(results['critical_events'])} critical event(s). "
                "These require immediate attention."
            )

        if not recommendations:
            recommendations.append("No significant issues found in system logs.")

        return recommendations


# Module-level function for easy importing
async def review_system_logs(
    log_types: list[str] | None = None,
    time_range_hours: int = 72,
    severity_filter: str = "error",
) -> DiagnosticResult:
    """Analyze Windows system logs.
    
    Args:
        log_types: Which logs to analyze (event_viewer, crash_dumps, bsod, reliability)
        time_range_hours: How far back to search
        severity_filter: Minimum severity (info, warning, error, critical)
        
    Returns:
        DiagnosticResult with log analysis
    """
    diag = ReviewSystemLogs()
    return await diag.run(
        log_types=log_types,
        time_range_hours=time_range_hours,
        severity_filter=severity_filter,
    )

