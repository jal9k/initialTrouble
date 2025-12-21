"""Network adapter status diagnostic.

See docs/functions/check_adapter_status.md for full specification.
"""

from typing import Any

from .base import BaseDiagnostic, DiagnosticResult
from .platform import Platform


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

        # Calculate summary stats
        active_count = sum(1 for a in adapters if a["status"] == "up")
        connected_count = sum(1 for a in adapters if a["is_connected"])

        # Find primary interface (first non-loopback with IP that's connected)
        primary = next(
            (a["name"] for a in adapters if a["has_ip"] and a["is_connected"] and a["type"] != "loopback"),
            None,
        )

        # Generate suggestions if needed
        suggestions = []
        if active_count == 0:
            suggestions.append("All network adapters are disabled")
            suggestions.append("Enable a network adapter in System Preferences > Network")
        elif connected_count == 0:
            suggestions.append("No adapters are connected to a network")
            suggestions.append("Check if WiFi is connected to an access point")
            suggestions.append("Check if Ethernet cable is plugged in")

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
async def check_adapter_status(interface_name: str | None = None) -> DiagnosticResult:
    """Check network adapter status."""
    diag = CheckAdapterStatus()
    return await diag.run(interface_name=interface_name)


