"""Connectivity diagnostics (ping gateway and DNS).

See docs/functions/ping_gateway.md and docs/functions/ping_dns.md for specifications.
"""

import re
from typing import Any

from .base import BaseDiagnostic, DiagnosticResult
from .platform import Platform


class PingGateway(BaseDiagnostic):
    """Test connectivity to the default gateway."""

    name = "ping_gateway"
    description = "Ping the default gateway"
    osi_layer = "Network"

    async def run(
        self,
        gateway: str | None = None,
        count: int = 4,
    ) -> DiagnosticResult:
        """
        Ping the gateway.

        Args:
            gateway: Gateway IP (auto-detected if not provided)
            count: Number of pings to send

        Returns:
            DiagnosticResult with ping results
        """
        # Auto-detect gateway if not provided
        if not gateway:
            gateway = await self._get_gateway()
            if not gateway:
                return self._failure(
                    error="Could not determine default gateway",
                    suggestions=[
                        "Run get_ip_config to check network configuration",
                        "Verify network cable or WiFi connection",
                    ],
                )

        # Run ping
        if self.platform == Platform.WINDOWS:
            cmd = f"ping -n {count} -w 5000 {gateway}"
        else:
            cmd = f"ping -c {count} -W 5 {gateway}"

        result = await self.executor.run(cmd, shell=True, timeout=30)

        # Parse results
        ping_data = self._parse_ping_output(result.stdout)
        ping_data["gateway_ip"] = gateway

        # Generate suggestions
        suggestions = []
        if not ping_data["reachable"]:
            suggestions.extend(
                [
                    "Gateway is not responding",
                    "Check if router/modem is powered on",
                    "Verify Ethernet cable is connected or WiFi is associated",
                    "Try restarting the router",
                    f"Check if gateway IP is correct: {gateway}",
                ]
            )
        elif ping_data["packet_loss_percent"] > 0:
            suggestions.extend(
                [
                    f"Intermittent connectivity ({ping_data['packet_loss_percent']:.0f}% packet loss)",
                    "Check WiFi signal strength if on wireless",
                    "Try a different Ethernet cable if wired",
                ]
            )

        return self._success(
            data=ping_data,
            raw_output=result.stdout,
            suggestions=suggestions if suggestions else None,
        )

    async def _get_gateway(self) -> str | None:
        """Auto-detect the default gateway."""
        if self.platform == Platform.WINDOWS:
            cmd = "(Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Select-Object -First 1).NextHop"
        else:
            cmd = "route -n get default 2>/dev/null | grep gateway | awk '{print $2}'"

        result = await self.executor.run(cmd, shell=True)
        if result.success and result.stdout.strip():
            return result.stdout.strip()

        # Fallback: try netstat
        if self.platform != Platform.WINDOWS:
            result = await self.executor.run(
                "netstat -nr | grep default | head -1 | awk '{print $2}'",
                shell=True,
            )
            if result.success and result.stdout.strip():
                return result.stdout.strip()

        return None

    def _parse_ping_output(self, output: str) -> dict[str, Any]:
        """Parse ping command output."""
        results: list[dict[str, Any]] = []
        packets_sent = 0
        packets_received = 0
        min_time = None
        avg_time = None
        max_time = None

        for line in output.split("\n"):
            # Parse individual ping responses
            if "bytes from" in line.lower() or "reply from" in line.lower():
                time_match = re.search(r"time[=<](\d+\.?\d*)\s*ms", line, re.IGNORECASE)
                ttl_match = re.search(r"ttl[=:](\d+)", line, re.IGNORECASE)
                seq_match = re.search(r"(?:icmp_seq|seq)[=:]?(\d+)", line, re.IGNORECASE)

                results.append(
                    {
                        "sequence": int(seq_match.group(1)) if seq_match else len(results),
                        "success": True,
                        "time_ms": float(time_match.group(1)) if time_match else None,
                        "ttl": int(ttl_match.group(1)) if ttl_match else None,
                    }
                )

            # Parse timeout lines
            elif "request timeout" in line.lower() or "request timed out" in line.lower():
                results.append(
                    {
                        "sequence": len(results),
                        "success": False,
                        "time_ms": None,
                        "ttl": None,
                    }
                )

            # Parse summary line
            elif "packets transmitted" in line.lower() or "packets: sent" in line.lower():
                sent_match = re.search(r"(\d+)\s*(?:packets\s+)?(?:transmitted|sent)", line, re.IGNORECASE)
                recv_match = re.search(r"(\d+)\s*(?:packets\s+)?received", line, re.IGNORECASE)
                if sent_match:
                    packets_sent = int(sent_match.group(1))
                if recv_match:
                    packets_received = int(recv_match.group(1))

            # Parse statistics line
            elif "min/avg/max" in line.lower() or "minimum" in line.lower():
                # macOS/Linux format: min/avg/max/stddev = 1.0/2.0/3.0/0.5 ms
                stats_match = re.search(
                    r"(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*)", line
                )
                if stats_match:
                    min_time = float(stats_match.group(1))
                    avg_time = float(stats_match.group(2))
                    max_time = float(stats_match.group(3))
                else:
                    # Windows format: Minimum = 0ms, Maximum = 1ms, Average = 0ms
                    min_match = re.search(r"minimum\s*=\s*(\d+)", line, re.IGNORECASE)
                    max_match = re.search(r"maximum\s*=\s*(\d+)", line, re.IGNORECASE)
                    avg_match = re.search(r"average\s*=\s*(\d+)", line, re.IGNORECASE)
                    if min_match:
                        min_time = float(min_match.group(1))
                    if max_match:
                        max_time = float(max_match.group(1))
                    if avg_match:
                        avg_time = float(avg_match.group(1))

        # Calculate packet loss
        if packets_sent == 0:
            packets_sent = len(results) if results else 4
            packets_received = sum(1 for r in results if r["success"])

        packet_loss = (
            ((packets_sent - packets_received) / packets_sent * 100)
            if packets_sent > 0
            else 100.0
        )

        return {
            "reachable": packets_received > 0,
            "packets_sent": packets_sent,
            "packets_received": packets_received,
            "packet_loss_percent": packet_loss,
            "min_time_ms": min_time,
            "avg_time_ms": avg_time,
            "max_time_ms": max_time,
            "results": results,
        }


class PingDNS(BaseDiagnostic):
    """Test connectivity to external DNS servers."""

    name = "ping_dns"
    description = "Ping external DNS servers"
    osi_layer = "Network"

    # Well-known DNS servers
    DNS_SERVERS = [
        ("8.8.8.8", "Google Public DNS"),
        ("1.1.1.1", "Cloudflare DNS"),
    ]

    async def run(self, count: int = 4) -> DiagnosticResult:
        """
        Ping DNS servers.

        Args:
            count: Number of pings per server

        Returns:
            DiagnosticResult with ping results for each server
        """
        results = []
        best_server = None
        best_latency = float("inf")

        for ip, name in self.DNS_SERVERS:
            if self.platform == Platform.WINDOWS:
                cmd = f"ping -n {count} -w 5000 {ip}"
            else:
                cmd = f"ping -c {count} -W 5 {ip}"

            result = await self.executor.run(cmd, shell=True, timeout=30)
            ping_data = self._parse_ping_output(result.stdout)

            server_result = {
                "server": ip,
                "name": name,
                "reachable": ping_data["reachable"],
                "packets_sent": ping_data["packets_sent"],
                "packets_received": ping_data["packets_received"],
                "packet_loss_percent": ping_data["packet_loss_percent"],
                "avg_time_ms": ping_data["avg_time_ms"],
            }
            results.append(server_result)

            # Track best server
            if ping_data["reachable"] and ping_data["avg_time_ms"]:
                if ping_data["avg_time_ms"] < best_latency:
                    best_latency = ping_data["avg_time_ms"]
                    best_server = ip

        # Calculate summary
        servers_reachable = sum(1 for r in results if r["reachable"])
        internet_accessible = servers_reachable > 0

        # Generate suggestions
        suggestions = []
        if not internet_accessible:
            suggestions.extend(
                [
                    "Cannot reach external DNS servers - no internet connectivity",
                    "If gateway ping succeeded, this is a WAN issue",
                    "Check if modem is connected to ISP",
                    "Contact ISP if modem shows connected but no internet",
                ]
            )
        elif servers_reachable < len(self.DNS_SERVERS):
            suggestions.append(
                "Internet is accessible but some DNS servers are unreachable"
            )
            if best_server:
                suggestions.append(f"Consider using the reachable DNS server ({best_server})")

        return self._success(
            data={
                "servers_tested": len(self.DNS_SERVERS),
                "servers_reachable": servers_reachable,
                "internet_accessible": internet_accessible,
                "results": results,
                "best_server": best_server,
                "best_latency_ms": best_latency if best_latency != float("inf") else None,
            },
            raw_output="",
            suggestions=suggestions if suggestions else None,
        )

    def _parse_ping_output(self, output: str) -> dict[str, Any]:
        """Parse ping output (reuse from PingGateway)."""
        # Use same parser as PingGateway
        gateway_diag = PingGateway()
        return gateway_diag._parse_ping_output(output)


async def ping_gateway(gateway: str | None = None, count: int = 4) -> DiagnosticResult:
    """Ping the default gateway."""
    diag = PingGateway()
    return await diag.run(gateway=gateway, count=count)


async def ping_dns(count: int = 4) -> DiagnosticResult:
    """Ping external DNS servers."""
    diag = PingDNS()
    return await diag.run(count=count)


