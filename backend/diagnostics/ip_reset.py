"""IP stack reset diagnostics - release IP, renew IP, and flush DNS cache.

Cross-platform tools for resetting network configuration.
"""

from typing import Any

from .base import BaseDiagnostic, DiagnosticResult
from .platform import Platform


class IpRelease(BaseDiagnostic):
    """Release the current DHCP IP address."""

    name = "ip_release"
    description = "Release DHCP IP address"
    osi_layer = "Network"

    async def run(
        self,
        interface: str | None = None,
    ) -> DiagnosticResult:
        """
        Release the current DHCP IP address.

        Args:
            interface: Specific network interface (optional)
                       Windows: "Ethernet", "Wi-Fi"
                       macOS: "en0", "en1"
                       Linux: "eth0", "wlan0"

        Returns:
            DiagnosticResult with release status
        """
        if self.platform == Platform.WINDOWS:
            return await self._run_windows(interface)
        elif self.platform == Platform.MACOS:
            return await self._run_macos(interface)
        elif self.platform == Platform.LINUX:
            return await self._run_linux(interface)
        else:
            return self._failure(
                error=f"Unsupported platform: {self.platform.value}",
                suggestions=["This tool supports Windows, macOS, and Linux"],
            )

    async def _run_windows(self, interface: str | None) -> DiagnosticResult:
        """Release IP on Windows using ipconfig."""
        if interface:
            cmd = f'ipconfig /release "{interface}"'
        else:
            cmd = "ipconfig /release"

        result = await self.executor.run(cmd, shell=True, timeout=30)

        if not result.success:
            # Check for common errors
            if "requires elevation" in result.stderr.lower() or "access denied" in result.stderr.lower():
                return self._failure(
                    error="Administrator privileges required",
                    raw_output=result.stderr,
                    suggestions=[
                        "Run as Administrator to release IP",
                        "Right-click and select 'Run as administrator'",
                    ],
                )
            return self._failure(
                error="Failed to release IP address",
                raw_output=result.stderr,
                suggestions=[
                    f"Verify interface name: {interface}" if interface else "Check if DHCP is being used",
                    "Run 'ipconfig /all' to see available interfaces",
                ],
            )

        return self._success(
            data={
                "action": "release",
                "interface": interface or "all",
                "released": True,
            },
            raw_output=result.stdout,
            suggestions=[
                "IP address released successfully",
                "Run ip_renew to obtain a new IP address",
            ],
        )

    async def _run_macos(self, interface: str | None) -> DiagnosticResult:
        """Release IP on macOS using ipconfig."""
        iface = interface or "en0"

        # On macOS, we set the interface to use no IP temporarily
        # This effectively releases the DHCP lease
        cmd = f"sudo ipconfig set {iface} NONE 2>/dev/null || ipconfig set {iface} NONE"

        result = await self.executor.run(cmd, shell=True, timeout=15)

        # Note: ipconfig set often succeeds silently
        if "permission denied" in result.stderr.lower():
            return self._failure(
                error="Administrator privileges required",
                raw_output=result.stderr,
                suggestions=[
                    "Run with sudo to release IP",
                    "Or use System Preferences > Network",
                ],
            )

        return self._success(
            data={
                "action": "release",
                "interface": iface,
                "released": True,
            },
            raw_output=result.stdout or "IP configuration cleared",
            suggestions=[
                f"IP address released on {iface}",
                "Run ip_renew to obtain a new IP address",
            ],
        )

    async def _run_linux(self, interface: str | None) -> DiagnosticResult:
        """Release IP on Linux using dhclient."""
        # Try to detect interface if not specified
        if not interface:
            detect_cmd = "ip route | grep default | awk '{print $5}' | head -1"
            detect_result = await self.executor.run(detect_cmd, shell=True)
            interface = detect_result.stdout.strip() or "eth0"

        # Try dhclient first, fall back to dhcpcd
        cmd = f"sudo dhclient -r {interface} 2>/dev/null || dhclient -r {interface} 2>/dev/null || sudo dhcpcd -k {interface} 2>/dev/null"

        result = await self.executor.run(cmd, shell=True, timeout=15)

        if "permission denied" in result.stderr.lower():
            return self._failure(
                error="Administrator privileges required",
                raw_output=result.stderr,
                suggestions=[
                    "Run with sudo: sudo dhclient -r " + interface,
                ],
            )

        return self._success(
            data={
                "action": "release",
                "interface": interface,
                "released": True,
            },
            raw_output=result.stdout or "DHCP lease released",
            suggestions=[
                f"IP address released on {interface}",
                "Run ip_renew to obtain a new IP address",
            ],
        )


class IpRenew(BaseDiagnostic):
    """Renew the DHCP IP address."""

    name = "ip_renew"
    description = "Renew DHCP IP address"
    osi_layer = "Network"

    async def run(
        self,
        interface: str | None = None,
    ) -> DiagnosticResult:
        """
        Renew the DHCP IP address.

        Args:
            interface: Specific network interface (optional)

        Returns:
            DiagnosticResult with renew status
        """
        if self.platform == Platform.WINDOWS:
            return await self._run_windows(interface)
        elif self.platform == Platform.MACOS:
            return await self._run_macos(interface)
        elif self.platform == Platform.LINUX:
            return await self._run_linux(interface)
        else:
            return self._failure(
                error=f"Unsupported platform: {self.platform.value}",
                suggestions=["This tool supports Windows, macOS, and Linux"],
            )

    async def _run_windows(self, interface: str | None) -> DiagnosticResult:
        """Renew IP on Windows using ipconfig."""
        if interface:
            cmd = f'ipconfig /renew "{interface}"'
        else:
            cmd = "ipconfig /renew"

        result = await self.executor.run(cmd, shell=True, timeout=60)

        if not result.success:
            if "requires elevation" in result.stderr.lower() or "access denied" in result.stderr.lower():
                return self._failure(
                    error="Administrator privileges required",
                    raw_output=result.stderr,
                    suggestions=[
                        "Run as Administrator to renew IP",
                    ],
                )
            if "unable to contact" in result.stderr.lower() or "dhcp server" in result.stderr.lower():
                return self._failure(
                    error="Could not contact DHCP server",
                    raw_output=result.stderr,
                    suggestions=[
                        "Check network connection",
                        "Verify router/DHCP server is online",
                        "Try restarting the router",
                    ],
                )
            return self._failure(
                error="Failed to renew IP address",
                raw_output=result.stderr,
            )

        # Parse the new IP from output
        new_ip = self._parse_new_ip(result.stdout)

        return self._success(
            data={
                "action": "renew",
                "interface": interface or "all",
                "renewed": True,
                "new_ip": new_ip,
            },
            raw_output=result.stdout,
            suggestions=["IP address renewed successfully"] if new_ip else None,
        )

    async def _run_macos(self, interface: str | None) -> DiagnosticResult:
        """Renew IP on macOS using ipconfig."""
        iface = interface or "en0"

        # Set interface to use DHCP
        cmd = f"sudo ipconfig set {iface} DHCP 2>/dev/null || ipconfig set {iface} DHCP"

        result = await self.executor.run(cmd, shell=True, timeout=30)

        if "permission denied" in result.stderr.lower():
            return self._failure(
                error="Administrator privileges required",
                raw_output=result.stderr,
                suggestions=[
                    "Run with sudo to renew IP",
                    "Or use System Preferences > Network",
                ],
            )

        # Get the new IP
        ip_cmd = f"ipconfig getifaddr {iface}"
        ip_result = await self.executor.run(ip_cmd, shell=True)
        new_ip = ip_result.stdout.strip() if ip_result.success else None

        return self._success(
            data={
                "action": "renew",
                "interface": iface,
                "renewed": True,
                "new_ip": new_ip,
            },
            raw_output=result.stdout or f"DHCP renewed on {iface}",
            suggestions=[f"New IP address: {new_ip}"] if new_ip else None,
        )

    async def _run_linux(self, interface: str | None) -> DiagnosticResult:
        """Renew IP on Linux using dhclient."""
        # Try to detect interface if not specified
        if not interface:
            detect_cmd = "ip route | grep default | awk '{print $5}' | head -1"
            detect_result = await self.executor.run(detect_cmd, shell=True)
            interface = detect_result.stdout.strip() or "eth0"

        # Try dhclient first, fall back to dhcpcd
        cmd = f"sudo dhclient {interface} 2>/dev/null || dhclient {interface} 2>/dev/null || sudo dhcpcd {interface} 2>/dev/null"

        result = await self.executor.run(cmd, shell=True, timeout=30)

        if "permission denied" in result.stderr.lower():
            return self._failure(
                error="Administrator privileges required",
                raw_output=result.stderr,
                suggestions=[
                    "Run with sudo: sudo dhclient " + interface,
                ],
            )

        # Get new IP
        ip_cmd = f"ip addr show {interface} | grep 'inet ' | awk '{{print $2}}' | cut -d/ -f1"
        ip_result = await self.executor.run(ip_cmd, shell=True)
        new_ip = ip_result.stdout.strip() if ip_result.success else None

        return self._success(
            data={
                "action": "renew",
                "interface": interface,
                "renewed": True,
                "new_ip": new_ip,
            },
            raw_output=result.stdout or "DHCP lease renewed",
            suggestions=[f"New IP address: {new_ip}"] if new_ip else None,
        )

    def _parse_new_ip(self, output: str) -> str | None:
        """Parse new IP address from ipconfig output."""
        import re
        # Look for IPv4 Address pattern in ipconfig output
        match = re.search(
            r"IPv4 Address[.\s]*:\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})",
            output,
            re.IGNORECASE,
        )
        if match:
            return match.group(1)

        # Fallback: look for any IP address pattern
        match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", output)
        if match:
            ip = match.group(1)
            # Exclude common non-client IPs
            if not ip.startswith("255.") and not ip.startswith("0."):
                return ip

        return None


class FlushDns(BaseDiagnostic):
    """Flush the DNS resolver cache."""

    name = "flush_dns"
    description = "Clear DNS resolver cache"
    osi_layer = "Application"

    async def run(self) -> DiagnosticResult:
        """
        Flush the DNS resolver cache.

        Returns:
            DiagnosticResult with flush status
        """
        if self.platform == Platform.WINDOWS:
            return await self._run_windows()
        elif self.platform == Platform.MACOS:
            return await self._run_macos()
        elif self.platform == Platform.LINUX:
            return await self._run_linux()
        else:
            return self._failure(
                error=f"Unsupported platform: {self.platform.value}",
                suggestions=["This tool supports Windows, macOS, and Linux"],
            )

    async def _run_windows(self) -> DiagnosticResult:
        """Flush DNS on Windows using ipconfig."""
        cmd = "ipconfig /flushdns"
        result = await self.executor.run(cmd, shell=True, timeout=15)

        if not result.success:
            if "requires elevation" in result.stderr.lower():
                return self._failure(
                    error="Administrator privileges required",
                    raw_output=result.stderr,
                    suggestions=["Run as Administrator to flush DNS cache"],
                )
            return self._failure(
                error="Failed to flush DNS cache",
                raw_output=result.stderr,
            )

        success = "successfully flushed" in result.stdout.lower()

        return self._success(
            data={
                "action": "flush_dns",
                "flushed": success,
            },
            raw_output=result.stdout,
            suggestions=["DNS cache cleared. Try accessing the website again."] if success else None,
        )

    async def _run_macos(self) -> DiagnosticResult:
        """Flush DNS on macOS using dscacheutil and killall."""
        # macOS requires both commands for complete flush
        cmds = [
            "sudo dscacheutil -flushcache 2>/dev/null || dscacheutil -flushcache",
            "sudo killall -HUP mDNSResponder 2>/dev/null || killall -HUP mDNSResponder 2>/dev/null",
        ]

        outputs = []
        errors = []

        for cmd in cmds:
            result = await self.executor.run(cmd, shell=True, timeout=10)
            if result.stdout:
                outputs.append(result.stdout)
            # Check for permission issues during first execution
            if result.stderr:
                stderr_lower = result.stderr.lower()
                if "permission denied" in stderr_lower or "operation not permitted" in stderr_lower:
                    return self._failure(
                        error="Administrator privileges may be required",
                        suggestions=[
                            "Run with sudo: sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder",
                        ],
                    )
                errors.append(result.stderr)

        return self._success(
            data={
                "action": "flush_dns",
                "flushed": True,
            },
            raw_output="\n".join(outputs) if outputs else "DNS cache flushed",
            suggestions=["DNS cache cleared. Try accessing the website again."],
        )

    async def _run_linux(self) -> DiagnosticResult:
        """Flush DNS on Linux using systemd-resolve or other methods."""
        # Try multiple methods as Linux distros vary
        methods = [
            ("systemd-resolve --flush-caches", "systemd-resolved"),
            ("resolvectl flush-caches", "resolvectl"),
            ("sudo /etc/init.d/nscd restart", "nscd"),
            ("sudo service dnsmasq restart", "dnsmasq"),
        ]

        for cmd, method in methods:
            result = await self.executor.run(cmd, shell=True, timeout=15)
            if result.success or result.return_code == 0:
                return self._success(
                    data={
                        "action": "flush_dns",
                        "flushed": True,
                        "method": method,
                    },
                    raw_output=result.stdout or f"DNS cache flushed using {method}",
                    suggestions=["DNS cache cleared. Try accessing the website again."],
                )

        # If all methods failed, provide guidance
        return self._failure(
            error="Could not flush DNS cache",
            suggestions=[
                "Try: sudo systemd-resolve --flush-caches",
                "Or: sudo service nscd restart",
                "Or: sudo service dnsmasq restart",
                "Your system may use a different DNS caching method",
            ],
        )


# Module-level functions for easy importing
async def ip_release(interface: str | None = None) -> DiagnosticResult:
    """Release DHCP IP address.
    
    Args:
        interface: Specific network interface (optional)
        
    Returns:
        DiagnosticResult with release status
    """
    diag = IpRelease()
    return await diag.run(interface=interface)


async def ip_renew(interface: str | None = None) -> DiagnosticResult:
    """Renew DHCP IP address.
    
    Args:
        interface: Specific network interface (optional)
        
    Returns:
        DiagnosticResult with renew status
    """
    diag = IpRenew()
    return await diag.run(interface=interface)


async def flush_dns() -> DiagnosticResult:
    """Flush DNS resolver cache.
    
    Returns:
        DiagnosticResult with flush status
    """
    diag = FlushDns()
    return await diag.run()

