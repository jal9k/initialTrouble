"""IP configuration diagnostic.

See docs/functions/get_ip_config.md for full specification.
"""

import re
from typing import Any

from .base import BaseDiagnostic, DiagnosticResult
from .platform import Platform


class GetIPConfig(BaseDiagnostic):
    """Get IP configuration for network interfaces."""

    name = "get_ip_config"
    description = "Get IP configuration including DHCP status"
    osi_layer = "Network"

    async def run(self, interface_name: str | None = None) -> DiagnosticResult:
        """
        Get IP configuration.

        Args:
            interface_name: Specific interface to check (optional)

        Returns:
            DiagnosticResult with IP configuration
        """
        if self.platform == Platform.MACOS:
            return await self._run_macos(interface_name)
        elif self.platform == Platform.WINDOWS:
            return await self._run_windows(interface_name)
        else:
            return self._failure(
                error=f"Unsupported platform: {self.platform.value}",
            )

    async def _run_macos(self, interface_name: str | None) -> DiagnosticResult:
        """Run diagnostic on macOS."""
        # Get interface info
        ifconfig_result = await self.executor.run("ifconfig", shell=True)

        # Get default gateway
        route_result = await self.executor.run(
            "netstat -nr | grep default | head -1", shell=True
        )

        # Get DNS servers
        dns_result = await self.executor.run(
            "scutil --dns | grep 'nameserver\\[' | head -5", shell=True
        )

        if not ifconfig_result.success:
            return self._failure(
                error="Failed to get network configuration",
                raw_output=ifconfig_result.stderr,
            )

        interfaces = self._parse_macos_ifconfig(ifconfig_result.stdout)
        gateway = self._parse_macos_gateway(route_result.stdout)
        dns_servers = self._parse_macos_dns(dns_result.stdout)

        # Filter to specific interface
        if interface_name:
            interfaces = [i for i in interfaces if i["interface"] == interface_name]

        # Add gateway and DNS to primary interface
        for iface in interfaces:
            if gateway and (not interface_name or iface["interface"] == interface_name):
                iface["gateway"] = gateway
            iface["dns_servers"] = dns_servers

        # Calculate summary
        has_valid_ip = any(
            i["ip_address"] and not i["is_apipa"] for i in interfaces
        )
        has_gateway = bool(gateway)
        primary_ip = next(
            (i["ip_address"] for i in interfaces if i["ip_address"] and not i["is_apipa"]),
            None,
        )

        # Generate suggestions
        suggestions = []
        if not has_valid_ip:
            apipa = any(i["is_apipa"] for i in interfaces)
            if apipa:
                suggestions.append(
                    "APIPA address detected (169.254.x.x) - DHCP server is unreachable"
                )
                suggestions.append("Check physical network connection")
                suggestions.append("Verify DHCP server is running on the network")
            else:
                suggestions.append("No IP address assigned to interface")
                suggestions.append("Run check_adapter_status to verify adapter is connected")
        elif not has_gateway:
            suggestions.append("No default gateway configured")
            suggestions.append("Check DHCP configuration or set static gateway")

        return self._success(
            data={
                "interfaces": interfaces,
                "has_valid_ip": has_valid_ip,
                "has_gateway": has_gateway,
                "primary_ip": primary_ip,
                "primary_gateway": gateway,
            },
            raw_output=ifconfig_result.stdout,
            suggestions=suggestions if suggestions else None,
        )

    def _parse_macos_ifconfig(self, output: str) -> list[dict[str, Any]]:
        """Parse ifconfig output for IP configuration."""
        interfaces = []
        current_iface = None
        current_data: dict[str, Any] = {}

        for line in output.split("\n"):
            if line and not line.startswith("\t") and ":" in line:
                if current_iface and current_data.get("ip_address"):
                    interfaces.append(current_data)

                current_iface = line.split(":")[0]
                current_data = {
                    "interface": current_iface,
                    "ip_address": None,
                    "subnet_mask": None,
                    "gateway": None,
                    "dns_servers": [],
                    "dhcp_enabled": True,  # Assume DHCP
                    "dhcp_server": None,
                    "lease_obtained": None,
                    "lease_expires": None,
                    "is_apipa": False,
                    "ipv6_address": None,
                }

            elif current_iface and line.startswith("\t"):
                line = line.strip()
                if line.startswith("inet "):
                    parts = line.split()
                    ip = parts[1]
                    current_data["ip_address"] = ip
                    current_data["is_apipa"] = ip.startswith("169.254.")

                    # Parse netmask
                    if "netmask" in line:
                        mask_idx = parts.index("netmask") + 1
                        if mask_idx < len(parts):
                            hex_mask = parts[mask_idx]
                            current_data["subnet_mask"] = self._hex_to_dotted(hex_mask)

                elif line.startswith("inet6 "):
                    parts = line.split()
                    if len(parts) > 1 and not parts[1].startswith("fe80::"):
                        current_data["ipv6_address"] = parts[1].split("%")[0]

        if current_iface and current_data.get("ip_address"):
            interfaces.append(current_data)

        return interfaces

    def _hex_to_dotted(self, hex_mask: str) -> str:
        """Convert hex netmask to dotted notation."""
        try:
            if hex_mask.startswith("0x"):
                hex_mask = hex_mask[2:]
            octets = [int(hex_mask[i : i + 2], 16) for i in range(0, 8, 2)]
            return ".".join(str(o) for o in octets)
        except (ValueError, IndexError):
            return hex_mask

    def _parse_macos_gateway(self, output: str) -> str | None:
        """Parse default gateway from netstat output."""
        for line in output.split("\n"):
            if "default" in line:
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]
        return None

    def _parse_macos_dns(self, output: str) -> list[str]:
        """Parse DNS servers from scutil output."""
        servers = []
        for line in output.split("\n"):
            if "nameserver" in line:
                match = re.search(r":\s*(\d+\.\d+\.\d+\.\d+)", line)
                if match:
                    servers.append(match.group(1))
        return list(dict.fromkeys(servers))  # Remove duplicates

    async def _run_windows(self, interface_name: str | None) -> DiagnosticResult:
        """Run diagnostic on Windows."""
        cmd = "Get-NetIPConfiguration | ConvertTo-Json -Depth 4"
        result = await self.executor.run(cmd, shell=True)

        if not result.success:
            return self._failure(
                error="Failed to get IP configuration",
                raw_output=result.stderr,
            )

        interfaces = self._parse_windows_config(result.stdout)

        if interface_name:
            interfaces = [i for i in interfaces if i["interface"] == interface_name]

        has_valid_ip = any(i["ip_address"] and not i["is_apipa"] for i in interfaces)
        has_gateway = any(i["gateway"] for i in interfaces)
        primary_ip = next(
            (i["ip_address"] for i in interfaces if i["ip_address"] and not i["is_apipa"]),
            None,
        )
        primary_gateway = next((i["gateway"] for i in interfaces if i["gateway"]), None)

        suggestions = []
        if not has_valid_ip:
            if any(i["is_apipa"] for i in interfaces):
                suggestions.append("APIPA address detected - DHCP failure")
                suggestions.append("Try: ipconfig /release && ipconfig /renew")
            else:
                suggestions.append("No valid IP address assigned")
        elif not has_gateway:
            suggestions.append("No default gateway configured")

        return self._success(
            data={
                "interfaces": interfaces,
                "has_valid_ip": has_valid_ip,
                "has_gateway": has_gateway,
                "primary_ip": primary_ip,
                "primary_gateway": primary_gateway,
            },
            raw_output=result.stdout,
            suggestions=suggestions if suggestions else None,
        )

    def _parse_windows_config(self, output: str) -> list[dict[str, Any]]:
        """Parse Windows Get-NetIPConfiguration JSON output."""
        import json

        try:
            data = json.loads(output)
            if isinstance(data, dict):
                data = [data]
        except json.JSONDecodeError:
            return []

        interfaces = []
        for item in data:
            ipv4 = item.get("IPv4Address", [{}])
            if isinstance(ipv4, list) and ipv4:
                ipv4 = ipv4[0]
            elif not isinstance(ipv4, dict):
                ipv4 = {}

            gateway_obj = item.get("IPv4DefaultGateway", [{}])
            if isinstance(gateway_obj, list) and gateway_obj:
                gateway_obj = gateway_obj[0]
            elif not isinstance(gateway_obj, dict):
                gateway_obj = {}

            dns_obj = item.get("DNSServer", [])
            if isinstance(dns_obj, dict):
                dns_obj = [dns_obj]

            ip = ipv4.get("IPAddress")
            interfaces.append(
                {
                    "interface": item.get("InterfaceAlias", "Unknown"),
                    "ip_address": ip,
                    "subnet_mask": None,  # Would need prefix length conversion
                    "gateway": gateway_obj.get("NextHop"),
                    "dns_servers": [
                        d.get("ServerAddresses", []) for d in dns_obj if d
                    ],
                    "dhcp_enabled": True,
                    "dhcp_server": None,
                    "lease_obtained": None,
                    "lease_expires": None,
                    "is_apipa": bool(ip and ip.startswith("169.254.")),
                    "ipv6_address": None,
                }
            )

        return interfaces


async def get_ip_config(interface_name: str | None = None) -> DiagnosticResult:
    """Get IP configuration."""
    diag = GetIPConfig()
    return await diag.run(interface_name=interface_name)


