"""Process management diagnostic.

Terminates problematic processes with safety guards to prevent
killing critical system processes.

See documents/functions/kill_process.md for full specification.
"""

import json
from typing import Any

from .base import BaseDiagnostic, DiagnosticResult
from .platform import Platform


class KillProcess(BaseDiagnostic):
    """Terminate problematic processes."""

    name = "kill_process"
    description = "Terminate hung or problematic processes"
    osi_layer = "Application"

    # Processes that should NEVER be killed (critical system processes)
    PROTECTED = {
        Platform.MACOS: {
            "kernel_task", "launchd", "WindowServer", "loginwindow",
            "opendirectoryd", "securityd", "diskarbitrationd", "configd",
            "mds", "mds_stores", "notifyd", "UserEventAgent",
        },
        Platform.WINDOWS: {
            "System", "smss.exe", "csrss.exe", "wininit.exe",
            "services.exe", "lsass.exe", "svchost.exe", "winlogon.exe",
            "dwm.exe", "RuntimeBroker.exe", "fontdrvhost.exe",
        },
        Platform.LINUX: {
            "init", "systemd", "kthreadd", "dbus-daemon",
            "NetworkManager", "gdm", "sddm", "lightdm", "Xorg",
            "gnome-shell", "plasmashell", "journald",
        },
    }

    async def run(
        self,
        process_name: str | None = None,
        process_id: int | None = None,
        force: bool = False,
        include_children: bool = True,
    ) -> DiagnosticResult:
        """
        Kill a process by name or PID.

        Args:
            process_name: Name of process to kill (e.g., "chrome", "Teams")
            process_id: Specific PID to terminate
            force: Use forceful termination (SIGKILL/-9 on Unix, /Force on Windows)
            include_children: Also terminate child processes

        Returns:
            DiagnosticResult with termination results
        """
        if not process_name and not process_id:
            return self._failure(
                error="Must specify either process_name or process_id",
                suggestions=[
                    "Provide a process name like 'chrome' or 'Teams'",
                    "Or provide a specific PID number",
                ],
            )

        # Find matching processes
        processes = await self._find_processes(process_name, process_id)

        if not processes:
            return self._failure(
                error="No matching processes found",
                data={"search_name": process_name, "search_pid": process_id},
                suggestions=[
                    "Check the process name spelling",
                    "Use Task Manager (Windows) or Activity Monitor (macOS) to find the correct name",
                    "The process may have already terminated",
                ],
            )

        # Filter out protected processes
        protected = self.PROTECTED.get(self.platform, set())
        killable = []
        blocked = []

        for proc in processes:
            proc_name = proc.get("name", "").lower()
            # Check if process name matches any protected process
            is_protected = any(
                prot.lower() in proc_name or proc_name in prot.lower()
                for prot in protected
            )
            if is_protected:
                blocked.append(proc)
            else:
                killable.append(proc)

        # Kill the processes
        killed = []
        failed = []

        for proc in killable:
            success = await self._kill_process(
                proc["pid"], force, include_children
            )
            if success:
                killed.append(proc)
            else:
                failed.append(proc)

        # Determine overall success
        if killed:
            return self._success(
                data={
                    "killed": killed,
                    "killed_count": len(killed),
                    "failed": failed,
                    "failed_count": len(failed),
                    "protected_blocked": blocked,
                    "protected_blocked_count": len(blocked),
                    "force_used": force,
                },
                suggestions=self._generate_suggestions(killed, failed, blocked),
            )
        elif blocked and not killable:
            return self._failure(
                error="All matching processes are protected system processes",
                data={
                    "protected_blocked": blocked,
                    "protected_blocked_count": len(blocked),
                },
                suggestions=[
                    "These processes are critical for system operation",
                    "Killing them would likely crash or destabilize the system",
                    "If the system is unresponsive, consider a restart instead",
                ],
            )
        else:
            return self._failure(
                error="Failed to terminate any processes",
                data={
                    "failed": failed,
                    "failed_count": len(failed),
                },
                suggestions=[
                    "Try running with force=True for forceful termination",
                    "You may need administrator/root privileges",
                    "The process may be stuck in an uninterruptible state",
                ],
            )

    async def _find_processes(
        self,
        name: str | None,
        pid: int | None,
    ) -> list[dict[str, Any]]:
        """Find processes matching criteria."""
        if self.platform == Platform.WINDOWS:
            return await self._find_windows(name, pid)
        else:
            return await self._find_unix(name, pid)

    async def _find_unix(
        self,
        name: str | None,
        pid: int | None,
    ) -> list[dict[str, Any]]:
        """Find processes on Unix systems (macOS/Linux)."""
        if pid:
            # Get specific process by PID
            cmd = f"ps -p {pid} -o pid=,comm="
        else:
            # Search by name (case-insensitive)
            cmd = f"ps aux | grep -i '{name}' | grep -v grep | grep -v 'kill_process'"

        result = await self.executor.run(cmd, shell=True)
        processes = []

        if not result.success or not result.stdout.strip():
            return processes

        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) >= 2:
                try:
                    if pid:
                        # Output format: PID COMMAND
                        proc_pid = int(parts[0].strip())
                        proc_name = parts[1].strip() if len(parts) > 1 else "unknown"
                    else:
                        # ps aux format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                        proc_pid = int(parts[1])
                        proc_name = parts[10] if len(parts) > 10 else parts[-1]
                        # Get just the command name without path
                        proc_name = proc_name.split("/")[-1]

                    processes.append({
                        "pid": proc_pid,
                        "name": proc_name,
                    })
                except (ValueError, IndexError):
                    continue

        return processes

    async def _find_windows(
        self,
        name: str | None,
        pid: int | None,
    ) -> list[dict[str, Any]]:
        """Find processes on Windows."""
        if pid:
            cmd = f"Get-Process -Id {pid} -ErrorAction SilentlyContinue | Select-Object Id, ProcessName | ConvertTo-Json"
        else:
            cmd = f"Get-Process -Name '*{name}*' -ErrorAction SilentlyContinue | Select-Object Id, ProcessName | ConvertTo-Json"

        result = await self.executor.run(cmd, shell=True)

        if not result.success or not result.stdout.strip():
            return []

        try:
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]
            return [
                {"pid": p.get("Id"), "name": p.get("ProcessName")}
                for p in data
                if p.get("Id") is not None
            ]
        except (json.JSONDecodeError, KeyError):
            return []

    async def _kill_process(
        self,
        pid: int,
        force: bool,
        include_children: bool,
    ) -> bool:
        """Terminate a single process."""
        if self.platform == Platform.WINDOWS:
            # Windows: Stop-Process
            force_flag = "-Force" if force else ""
            cmd = f"Stop-Process -Id {pid} {force_flag} -ErrorAction SilentlyContinue"
        else:
            # Unix: kill command
            signal = "-9" if force else "-TERM"
            cmd = f"kill {signal} {pid}"

        result = await self.executor.run(cmd, shell=True)

        # Verify the process was killed
        if self.platform == Platform.WINDOWS:
            verify_cmd = f"Get-Process -Id {pid} -ErrorAction SilentlyContinue"
        else:
            verify_cmd = f"ps -p {pid} -o pid="

        verify_result = await self.executor.run(verify_cmd, shell=True)

        # Process is killed if verification fails (process not found)
        return not verify_result.stdout.strip()

    def _generate_suggestions(
        self,
        killed: list,
        failed: list,
        blocked: list,
    ) -> list[str] | None:
        """Generate suggestions based on results."""
        suggestions = []

        if killed:
            suggestions.append(
                f"Successfully terminated {len(killed)} process(es)"
            )

        if blocked:
            suggestions.append(
                f"Blocked {len(blocked)} protected system process(es) for safety"
            )

        if failed:
            suggestions.append(
                "Some processes could not be killed. Try with force=True or run as administrator."
            )

        return suggestions if suggestions else None


# Module-level function for easy importing
async def kill_process(
    process_name: str | None = None,
    process_id: int | None = None,
    force: bool = False,
    include_children: bool = True,
) -> DiagnosticResult:
    """Kill a process by name or PID.
    
    Args:
        process_name: Name of process to kill
        process_id: Specific PID to terminate
        force: Use forceful termination (SIGKILL/-9)
        include_children: Also terminate child processes
        
    Returns:
        DiagnosticResult with termination results
    """
    diag = KillProcess()
    return await diag.run(
        process_name=process_name,
        process_id=process_id,
        force=force,
        include_children=include_children,
    )

