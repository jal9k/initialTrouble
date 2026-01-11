"""VPN connectivity diagnostic.

Tests VPN connection status and verifies tunnel functionality
across different VPN types and platforms.

See documents/functions/test_vpn_connectivity.md for full specification.
"""

import json
import re
from typing import Any

from .base import BaseDiagnostic, DiagnosticResult
from .platform import Platform


class TestVPNConnectivity(BaseDiagnostic):
    """Check VPN connection status and test connectivity."""

    name = "test_vpn_connectivity"
    description = "Test VPN connection status and tunnel functionality"
    osi_layer = "Network"

    # VPN interface patterns by platform
    VPN_INTERFACE_PATTERNS = {
        Platform.MACOS: {
            "wireguard": r"^utun\d+$",
            "openvpn": r"^(utun|tun)\d+$",
            "ipsec": r"^ipsec\d+$",
            "any": r"^(utun|tun|ipsec|ppp)\d+$",
        },
        Platform.WINDOWS: {
            # Windows VPN adapters typically have descriptive names
            "wireguard": r"WireGuard",
            "openvpn": r"TAP-Windows|OpenVPN",
            "any": r"(VPN|WireGuard|TAP|OpenVPN|Cisco|GlobalProtect)",
        },
        Platform.LINUX: {
            "wireguard": r"^wg\d+$",
            "openvpn": r"^tun\d+$",
            "any": r"^(wg|tun|tap|ppp)\d+$",
        },
    }

    async def run(
        self,
        vpn_type: str | None = None,
        test_endpoint: str | None = None,
    ) -> DiagnosticResult:
        """
        Test VPN connectivity.

        Args:
            vpn_type: Type of VPN (auto-detect if not specified).
                      Options: "wireguard", "openvpn", "ipsec", "cisco", "globalprotect"
            test_endpoint: Internal endpoint to test through VPN (e.g., "192.168.10.1")

        Returns:
            DiagnosticResult with VPN status and connectivity info
        """
        # Step 1: Detect VPN interfaces
        vpn_info = await self._detect_vpn()

        if not vpn_info["connected"]:
            return self._success(
                data={
                    "vpn_connected": False,
                    "vpn_type": None,
                    "vpn_interface": None,
                    "vpn_ip": None,
                    "routes_active": False,
                    "dns_via_vpn": False,
                    "internal_reachable": None,
                    "detection_method": vpn_info.get("method", "interface_scan"),
                },
                suggestions=[
                    "No active VPN connection detected",
                    "Connect to your VPN and try again",
                    "Check VPN client application is running",
                ],
            )

        # Step 2: Get VPN interface details
        vpn_interface = vpn_info["interface"]
        detected_type = vpn_type or vpn_info.get("type", "unknown")

        # Step 3: Get VPN IP address
        vpn_ip = await self._get_vpn_ip(vpn_interface)

        # Step 4: Check if VPN routes are active
        routes_active = await self._check_vpn_routes()

        # Step 5: Check DNS configuration
        dns_via_vpn = await self._check_dns_via_vpn()

        # Step 6: Test internal endpoint if provided
        internal_reachable = None
        if test_endpoint:
            internal_reachable = await self._test_endpoint(test_endpoint)

        # Generate suggestions based on findings
        suggestions = self._generate_suggestions(
            vpn_connected=True,
            vpn_ip=vpn_ip,
            routes_active=routes_active,
            dns_via_vpn=dns_via_vpn,
            internal_reachable=internal_reachable,
            test_endpoint=test_endpoint,
        )

        return self._success(
            data={
                "vpn_connected": True,
                "vpn_type": detected_type,
                "vpn_interface": vpn_interface,
                "vpn_ip": vpn_ip,
                "routes_active": routes_active,
                "dns_via_vpn": dns_via_vpn,
                "internal_reachable": internal_reachable,
                "detection_method": vpn_info.get("method", "interface_scan"),
            },
            suggestions=suggestions,
        )

    async def _detect_vpn(self) -> dict[str, Any]:
        """Detect if a VPN is connected and identify the interface."""
        if self.platform == Platform.MACOS:
            return await self._detect_vpn_macos()
        elif self.platform == Platform.WINDOWS:
            return await self._detect_vpn_windows()
        else:
            return await self._detect_vpn_linux()

    async def _detect_vpn_macos(self) -> dict[str, Any]:
        """Detect VPN on macOS."""
        # Method 1: Check for VPN interfaces
        result = await self.executor.run("ifconfig -l", shell=True)
        if result.success:
            interfaces = result.stdout.strip().split()
            patterns = self.VPN_INTERFACE_PATTERNS[Platform.MACOS]

            for iface in interfaces:
                # Check for utun interfaces (WireGuard, OpenVPN)
                if re.match(patterns["any"], iface):
                    # Verify it's up and has an IP
                    iface_result = await self.executor.run(
                        f"ifconfig {iface}", shell=True
                    )
                    if iface_result.success and "inet " in iface_result.stdout:
                        vpn_type = self._guess_vpn_type_macos(iface)
                        return {
                            "connected": True,
                            "interface": iface,
                            "type": vpn_type,
                            "method": "interface_scan",
                        }

        # Method 2: Check scutil for VPN connections
        result = await self.executor.run("scutil --nc list", shell=True)
        if result.success and "Connected" in result.stdout:
            # Parse the connected VPN name
            for line in result.stdout.split("\n"):
                if "Connected" in line:
                    return {
                        "connected": True,
                        "interface": "scutil_vpn",
                        "type": "system_vpn",
                        "method": "scutil",
                    }

        return {"connected": False, "method": "interface_scan"}

    async def _detect_vpn_windows(self) -> dict[str, Any]:
        """Detect VPN on Windows."""
        # Method 1: Check Get-VpnConnection
        result = await self.executor.run(
            "Get-VpnConnection | Where-Object {$_.ConnectionStatus -eq 'Connected'} | "
            "Select-Object Name, ServerAddress | ConvertTo-Json",
            shell=True,
        )
        if result.success and result.stdout.strip() and result.stdout.strip() != "":
            try:
                data = json.loads(result.stdout)
                if data:
                    if isinstance(data, dict):
                        data = [data]
                    return {
                        "connected": True,
                        "interface": data[0].get("Name", "VPN"),
                        "type": "windows_vpn",
                        "method": "Get-VpnConnection",
                    }
            except json.JSONDecodeError:
                pass

        # Method 2: Check for VPN network adapters
        result = await self.executor.run(
            "Get-NetAdapter | Where-Object {$_.InterfaceDescription -match 'VPN|TAP|WireGuard|OpenVPN'} | "
            "Where-Object {$_.Status -eq 'Up'} | Select-Object Name, InterfaceDescription | ConvertTo-Json",
            shell=True,
        )
        if result.success and result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                if data:
                    if isinstance(data, dict):
                        data = [data]
                    return {
                        "connected": True,
                        "interface": data[0].get("Name", "VPN Adapter"),
                        "type": self._guess_vpn_type_windows(data[0].get("InterfaceDescription", "")),
                        "method": "Get-NetAdapter",
                    }
            except json.JSONDecodeError:
                pass

        return {"connected": False, "method": "Get-VpnConnection"}

    async def _detect_vpn_linux(self) -> dict[str, Any]:
        """Detect VPN on Linux."""
        # Method 1: Check for WireGuard interfaces
        result = await self.executor.run("ip link show type wireguard 2>/dev/null", shell=True)
        if result.success and result.stdout.strip():
            # Extract interface name
            match = re.search(r"^\d+:\s+(\w+):", result.stdout)
            if match:
                return {
                    "connected": True,
                    "interface": match.group(1),
                    "type": "wireguard",
                    "method": "ip_link",
                }

        # Method 2: Check for tun/tap interfaces
        result = await self.executor.run("ip link show", shell=True)
        if result.success:
            patterns = self.VPN_INTERFACE_PATTERNS[Platform.LINUX]
            for line in result.stdout.split("\n"):
                match = re.search(r"^\d+:\s+(\w+):", line)
                if match:
                    iface = match.group(1)
                    if re.match(patterns["any"], iface):
                        return {
                            "connected": True,
                            "interface": iface,
                            "type": self._guess_vpn_type_linux(iface),
                            "method": "ip_link",
                        }

        # Method 3: Check NetworkManager
        result = await self.executor.run(
            "nmcli connection show --active 2>/dev/null | grep -i vpn",
            shell=True,
        )
        if result.success and result.stdout.strip():
            return {
                "connected": True,
                "interface": "nmcli_vpn",
                "type": "networkmanager_vpn",
                "method": "nmcli",
            }

        return {"connected": False, "method": "ip_link"}

    def _guess_vpn_type_macos(self, interface: str) -> str:
        """Guess VPN type from macOS interface name."""
        if interface.startswith("utun"):
            return "wireguard_or_openvpn"
        elif interface.startswith("ipsec"):
            return "ipsec"
        elif interface.startswith("ppp"):
            return "pptp_or_l2tp"
        return "unknown"

    def _guess_vpn_type_windows(self, description: str) -> str:
        """Guess VPN type from Windows adapter description."""
        desc_lower = description.lower()
        if "wireguard" in desc_lower:
            return "wireguard"
        elif "tap" in desc_lower or "openvpn" in desc_lower:
            return "openvpn"
        elif "cisco" in desc_lower:
            return "cisco"
        elif "globalprotect" in desc_lower:
            return "globalprotect"
        return "unknown"

    def _guess_vpn_type_linux(self, interface: str) -> str:
        """Guess VPN type from Linux interface name."""
        if interface.startswith("wg"):
            return "wireguard"
        elif interface.startswith("tun"):
            return "openvpn"
        elif interface.startswith("tap"):
            return "openvpn_tap"
        elif interface.startswith("ppp"):
            return "pptp_or_l2tp"
        return "unknown"

    async def _get_vpn_ip(self, interface: str) -> str | None:
        """Get the IP address assigned to the VPN interface."""
        if self.platform == Platform.WINDOWS:
            result = await self.executor.run(
                f"Get-NetIPAddress -InterfaceAlias '{interface}' -AddressFamily IPv4 | "
                "Select-Object IPAddress | ConvertTo-Json",
                shell=True,
            )
            if result.success:
                try:
                    data = json.loads(result.stdout)
                    if isinstance(data, list):
                        data = data[0]
                    return data.get("IPAddress")
                except (json.JSONDecodeError, IndexError):
                    pass
        else:
            result = await self.executor.run(f"ifconfig {interface} 2>/dev/null || ip addr show {interface}", shell=True)
            if result.success:
                # Look for inet line
                match = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", result.stdout)
                if match:
                    return match.group(1)
        return None

    async def _check_vpn_routes(self) -> bool:
        """Check if VPN routes are active in the routing table."""
        if self.platform == Platform.WINDOWS:
            result = await self.executor.run("route print", shell=True)
        else:
            result = await self.executor.run("netstat -rn 2>/dev/null || ip route", shell=True)

        if not result.success:
            return False

        # Look for common VPN routing patterns
        output = result.stdout.lower()
        
        # VPN typically adds routes like 0.0.0.0/0 or 10.x.x.x ranges
        vpn_route_indicators = [
            "10.0.0.0",
            "10.8.0.0",
            "172.16.",
            "192.168.",
            "0.0.0.0/1",
            "128.0.0.0/1",
        ]
        
        return any(indicator in output for indicator in vpn_route_indicators)

    async def _check_dns_via_vpn(self) -> bool:
        """Check if DNS queries go through the VPN."""
        if self.platform == Platform.WINDOWS:
            result = await self.executor.run(
                "Get-DnsClientServerAddress | Select-Object InterfaceAlias, ServerAddresses | ConvertTo-Json",
                shell=True,
            )
        elif self.platform == Platform.MACOS:
            result = await self.executor.run("scutil --dns", shell=True)
        else:
            result = await self.executor.run("cat /etc/resolv.conf", shell=True)

        if not result.success:
            return False

        # Check for private DNS servers (common in VPN configs)
        private_dns_patterns = [
            r"10\.\d+\.\d+\.\d+",
            r"172\.(1[6-9]|2[0-9]|3[01])\.\d+\.\d+",
            r"192\.168\.\d+\.\d+",
        ]

        for pattern in private_dns_patterns:
            if re.search(pattern, result.stdout):
                return True

        return False

    async def _test_endpoint(self, endpoint: str) -> bool:
        """Test connectivity to an internal endpoint through VPN."""
        if self.platform == Platform.WINDOWS:
            result = await self.executor.run(
                f"Test-NetConnection -ComputerName {endpoint} -InformationLevel Quiet",
                shell=True,
            )
            return "True" in result.stdout
        else:
            result = await self.executor.run(
                f"ping -c 1 -W 3 {endpoint}",
                shell=True,
            )
            return result.success and ("1 received" in result.stdout or "1 packets received" in result.stdout)

    def _generate_suggestions(
        self,
        vpn_connected: bool,
        vpn_ip: str | None,
        routes_active: bool,
        dns_via_vpn: bool,
        internal_reachable: bool | None,
        test_endpoint: str | None,
    ) -> list[str] | None:
        """Generate suggestions based on VPN status."""
        suggestions = []

        if vpn_connected and vpn_ip:
            suggestions.append(f"VPN connected with IP: {vpn_ip}")

        if not routes_active:
            suggestions.append(
                "VPN routes may not be configured. Check VPN client settings."
            )

        if not dns_via_vpn:
            suggestions.append(
                "DNS does not appear to go through VPN. "
                "This may cause DNS leaks. Check VPN DNS settings."
            )

        if test_endpoint and internal_reachable is False:
            suggestions.append(
                f"Cannot reach internal endpoint {test_endpoint}. "
                "Check VPN routing and endpoint availability."
            )
        elif test_endpoint and internal_reachable is True:
            suggestions.append(f"Successfully reached internal endpoint: {test_endpoint}")

        return suggestions if suggestions else None


# Module-level function for easy importing
async def test_vpn_connectivity(
    vpn_type: str | None = None,
    test_endpoint: str | None = None,
) -> DiagnosticResult:
    """Test VPN connectivity.
    
    Args:
        vpn_type: Type of VPN (auto-detect if not specified)
        test_endpoint: Internal endpoint to test through VPN
        
    Returns:
        DiagnosticResult with VPN status and connectivity info
    """
    diag = TestVPNConnectivity()
    return await diag.run(vpn_type=vpn_type, test_endpoint=test_endpoint)

