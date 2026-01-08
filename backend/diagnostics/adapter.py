"""Network adapter status diagnostic.

See docs/functions/check_adapter_status.md for full specification.
"""

from typing import Any
import json
import time

from .base import BaseDiagnostic, DiagnosticResult
from .platform import Platform

# #region agent log
def _dbg_adapter(loc: str, msg: str, data: dict, hyp: str = "H-ADAPTER"):
    with open("/Users/tyurgal/Documents/python/diag/network-diag/.cursor/debug.log", "a") as f:
        f.write(json.dumps({"location": loc, "message": msg, "data": data, "timestamp": int(time.time()*1000), "sessionId": "debug-session", "hypothesisId": hyp}) + "\n")
# #endregion


class CheckAdapterStatus(BaseDiagnostic):
    """Check if network adapters are enabled and operational."""

    name = "check_adapter_status"
    description = "Check network adapter status"
    osi_layer = "Physical/Link"

    async def run(self, interface_name: str | None = None) -> DiagnosticResult:
        """
        Check adapter status.

        Args:
            interface_name: Specific interface to check (optional)

        Returns:
            DiagnosticResult with adapter information
        """
        if self.platform == Platform.MACOS:
            return await self._run_macos(interface_name)
        elif self.platform == Platform.WINDOWS:
            return await self._run_windows(interface_name)
        else:
            return self._failure(
                error=f"Unsupported platform: {self.platform.value}",
                suggestions=["This diagnostic only supports macOS and Windows"],
            )

    async def _run_macos(self, interface_name: str | None) -> DiagnosticResult:
        """Run diagnostic on macOS."""
        result = await self.executor.run("ifconfig -a", shell=True)

        if not result.success:
            return self._failure(
                error="Failed to get network interfaces",
                raw_output=result.stderr,
                suggestions=["Check if ifconfig command is available"],
            )

        adapters = self._parse_macos_ifconfig(result.stdout)

        # Filter to specific interface if requested
        if interface_name:
            adapters = [a for a in adapters if a["name"] == interface_name]

        # Calculate summary stats (EXCLUDE loopback from counts - it's always connected)
        real_adapters = [a for a in adapters if a["type"] != "loopback"]
        active_count = sum(1 for a in real_adapters if a["status"] == "up")
        connected_count = sum(1 for a in real_adapters if a["is_connected"])

        # #region agent log
        # H1/H3: Log all adapters to see what data the LLM will receive
        wifi_adapters = [a for a in adapters if a["name"].startswith("en")]
        _dbg_adapter("adapter.py:_run_macos:parsed", "Parsed adapter data", {
            "all_adapters": adapters,
            "wifi_adapters": wifi_adapters,
            "active_count": active_count,
            "connected_count": connected_count,
        }, "H1")
        # H3: Specifically log WiFi adapter status
        for wa in wifi_adapters:
            _dbg_adapter("adapter.py:_run_macos:wifi_status", f"WiFi adapter {wa['name']} status", {
                "name": wa["name"],
                "status": wa["status"],  # up/down (enabled/disabled)
                "is_connected": wa["is_connected"],  # connected to network?
                "has_ip": wa["has_ip"],
            }, "H3")
        # #endregion

        # Find primary interface (first non-loopback with IP that's connected)
        primary = next(
            (a["name"] for a in real_adapters if a["has_ip"] and a["is_connected"]),
            None,
        )
        
        # Check if any real adapter has network connectivity
        has_network_connection = connected_count > 0

        # Generate suggestions if needed
        suggestions = []
        if active_count == 0:
            suggestions.append("All network adapters are disabled")
            suggestions.append("ACTION: Call enable_wifi to enable the WiFi adapter")
            suggestions.append("Enable a network adapter in System Preferences > Network")
        elif connected_count == 0:
            suggestions.append("CRITICAL: No network adapters are connected to any network")
            suggestions.append("ACTION: Call enable_wifi to enable WiFi and attempt connection")
            suggestions.append("WiFi may be turned off or not connected to a network")
            suggestions.append("If WiFi is already on, user needs to manually select a network")

        # #region agent log
        # H5: Log the summary fields that should tell LLM to stop
        _dbg_adapter("adapter.py:_run_macos:summary", "Summary stats for LLM", {
            "active_count": active_count,
            "connected_count": connected_count,
            "has_network_connection": has_network_connection,
            "primary_interface": primary,
            "suggestions_count": len(suggestions),
            "suggestions": suggestions,
        }, "H5")
        # #endregion

        return self._success(
            data={
                "adapters": adapters,
                "active_count": active_count,
                "connected_count": connected_count,
                "has_network_connection": has_network_connection,  # FALSE = STOP diagnostics!
                "primary_interface": primary,
            },
            raw_output=result.stdout,
            suggestions=suggestions if suggestions else None,
        )

    def _parse_macos_ifconfig(self, output: str) -> list[dict[str, Any]]:
        """Parse macOS ifconfig output into adapter list."""
        adapters = []
        current: dict[str, Any] | None = None

        for line in output.split("\n"):
            # New interface starts with name at beginning of line
            if line and not line.startswith("\t") and ":" in line:
                if current:
                    adapters.append(current)

                name = line.split(":")[0]
                flags = ""
                if "<" in line and ">" in line:
                    flags = line[line.index("<") + 1 : line.index(">")]

                # Determine type
                if name == "lo0":
                    iface_type = "loopback"
                elif name.startswith("en"):
                    iface_type = "ethernet"  # Could be wifi, refined later
                elif name.startswith(("utun", "bridge", "awdl", "llw")):
                    iface_type = "virtual"
                else:
                    iface_type = "other"

                current = {
                    "name": name,
                    "display_name": name,
                    "status": "up" if "UP" in flags else "down",
                    "type": iface_type,
                    "mac_address": None,
                    "has_ip": False,
                    "is_connected": "RUNNING" in flags,
                }

            elif current and line.startswith("\t"):
                line = line.strip()
                if line.startswith("ether "):
                    current["mac_address"] = line.split()[1]
                elif line.startswith("inet "):
                    current["has_ip"] = True
                elif line.startswith("status: "):
                    status = line.split(": ")[1]
                    current["is_connected"] = status == "active"

        if current:
            adapters.append(current)

        # Filter out virtual interfaces for cleaner output
        adapters = [
            a
            for a in adapters
            if a["type"] not in ("virtual", "loopback") or a["has_ip"]
        ]

        return adapters

    async def _run_windows(self, interface_name: str | None) -> DiagnosticResult:
        """Run diagnostic on Windows."""
        cmd = (
            "Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, "
            "MacAddress, MediaConnectionState | ConvertTo-Json"
        )
        result = await self.executor.run(cmd, shell=True)

        if not result.success:
            return self._failure(
                error="Failed to get network adapters",
                raw_output=result.stderr,
                suggestions=["Check if PowerShell is available"],
            )

        adapters = self._parse_windows_adapters(result.stdout)

        if interface_name:
            adapters = [a for a in adapters if a["name"] == interface_name]

        active_count = sum(1 for a in adapters if a["status"] == "up")
        connected_count = sum(1 for a in adapters if a["is_connected"])

        primary = next(
            (a["name"] for a in adapters if a["has_ip"] and a["is_connected"]),
            None,
        )

        suggestions = []
        if active_count == 0:
            suggestions.append("All network adapters are disabled")
            suggestions.append(
                "Enable adapter: Control Panel > Network and Sharing Center > "
                "Change adapter settings"
            )
        elif connected_count == 0:
            suggestions.append("No adapters are connected to a network")
            suggestions.append("Check WiFi connection or Ethernet cable")

        return self._success(
            data={
                "adapters": adapters,
                "active_count": active_count,
                "connected_count": connected_count,
                "primary_interface": primary,
            },
            raw_output=result.stdout,
            suggestions=suggestions if suggestions else None,
        )

    def _parse_windows_adapters(self, output: str) -> list[dict[str, Any]]:
        """Parse Windows Get-NetAdapter JSON output."""
        import json

        try:
            data = json.loads(output)
            if isinstance(data, dict):
                data = [data]
        except json.JSONDecodeError:
            return []

        adapters = []
        for item in data:
            status = item.get("Status", "").lower()
            media = item.get("MediaConnectionState", 0)

            adapters.append(
                {
                    "name": item.get("Name", "Unknown"),
                    "display_name": item.get("InterfaceDescription", ""),
                    "status": "up" if status == "up" else "down",
                    "type": "ethernet",  # Could refine based on InterfaceType
                    "mac_address": item.get("MacAddress"),
                    "has_ip": media == 1,  # Assume IP if connected
                    "is_connected": media == 1,
                }
            )

        return adapters


# Module-level function for easy importing
async def check_adapter_status(interface_name: str | None = None, interface: str | None = None) -> DiagnosticResult:
    """Check network adapter status."""
    # Accept both 'interface' and 'interface_name' for LLM compatibility
    iface = interface or interface_name
    diag = CheckAdapterStatus()
    return await diag.run(interface_name=iface)


