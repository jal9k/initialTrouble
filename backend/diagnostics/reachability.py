"""Website/host reachability diagnostics (ping address and traceroute).

Cross-platform tools for testing connectivity to any host.
"""

import re
from typing import Any

from .base import BaseDiagnostic, DiagnosticResult
from .platform import Platform


class PingAddress(BaseDiagnostic):
    """Ping any specified address (IP or hostname)."""

    name = "ping_address"
    description = "Ping a specified address to test reachability"
    osi_layer = "Network"

    async def run(
        self,
        host: str,
        count: int = 4,
    ) -> DiagnosticResult:
        """
        Ping a specified host.

        Args:
            host: IP address or hostname to ping
            count: Number of ping packets to send (default: 4)

        Returns:
            DiagnosticResult with ping results
        """
        if not host:
            return self._failure(
                error="Host address is required",
                suggestions=["Provide an IP address or hostname to ping"],
            )

        # Build platform-specific ping command
        if self.platform == Platform.WINDOWS:
            cmd = f"ping -n {count} -w 5000 {host}"
        else:
            # macOS and Linux
            cmd = f"ping -c {count} -W 5 {host}"

        result = await self.executor.run(cmd, shell=True, timeout=30)

        # Parse results
        ping_data = self._parse_ping_output(result.stdout)
        ping_data["host"] = host

        # Generate suggestions based on results
        suggestions = []
        if not ping_data["reachable"]:
            suggestions.extend([
                f"Host '{host}' is not responding to ping",
                "Verify the hostname or IP address is correct",
                "The host may be blocking ICMP ping requests",
                "Check if you have internet connectivity (run ping_dns)",
                "If this is a website, try test_dns_resolution instead",
            ])
        elif ping_data["packet_loss_percent"] > 0:
            suggestions.extend([
                f"Intermittent connectivity to {host} ({ping_data['packet_loss_percent']:.0f}% packet loss)",
                "Network congestion or unstable connection detected",
                "Consider running traceroute to identify the problem hop",
            ])
        elif ping_data["avg_time_ms"] and ping_data["avg_time_ms"] > 200:
            suggestions.append(
                f"High latency detected ({ping_data['avg_time_ms']:.1f}ms average)"
            )

        return self._success(
            data=ping_data,
            raw_output=result.stdout,
            suggestions=suggestions if suggestions else None,
        )

    def _parse_ping_output(self, output: str) -> dict[str, Any]:
        """Parse ping command output across platforms."""
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

                results.append({
                    "sequence": int(seq_match.group(1)) if seq_match else len(results),
                    "success": True,
                    "time_ms": float(time_match.group(1)) if time_match else None,
                    "ttl": int(ttl_match.group(1)) if ttl_match else None,
                })

            # Parse timeout lines
            elif "request timeout" in line.lower() or "request timed out" in line.lower():
                results.append({
                    "sequence": len(results),
                    "success": False,
                    "time_ms": None,
                    "ttl": None,
                })

            # Parse summary line
            elif "packets transmitted" in line.lower() or "packets: sent" in line.lower():
                sent_match = re.search(
                    r"(\d+)\s*(?:packets\s+)?(?:transmitted|sent)", line, re.IGNORECASE
                )
                recv_match = re.search(
                    r"(\d+)\s*(?:packets\s+)?received", line, re.IGNORECASE
                )
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
            packets_sent = len(results) if results else count if 'count' in dir() else 4
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


class Traceroute(BaseDiagnostic):
    """Trace the route to a destination host."""

    name = "traceroute"
    description = "Trace the network path to a destination"
    osi_layer = "Network"

    async def run(
        self,
        host: str,
        max_hops: int = 30,
    ) -> DiagnosticResult:
        """
        Trace route to destination.

        Args:
            host: Destination IP or hostname
            max_hops: Maximum number of hops to trace (default: 30)

        Returns:
            DiagnosticResult with traceroute results
        """
        if not host:
            return self._failure(
                error="Destination host is required",
                suggestions=["Provide an IP address or hostname to trace"],
            )

        # Build platform-specific traceroute command
        if self.platform == Platform.WINDOWS:
            cmd = f"tracert -h {max_hops} -w 3000 {host}"
            timeout = max_hops * 5  # Windows tracert can be slow
        else:
            # macOS and Linux use traceroute
            cmd = f"traceroute -m {max_hops} -w 3 {host}"
            timeout = max_hops * 4

        result = await self.executor.run(cmd, shell=True, timeout=timeout)

        # Parse traceroute output
        trace_data = self._parse_traceroute_output(result.stdout)
        trace_data["destination"] = host
        trace_data["max_hops_setting"] = max_hops

        # Generate suggestions
        suggestions = []
        if not trace_data["destination_reached"]:
            suggestions.extend([
                f"Could not reach destination '{host}'",
                "Check where the trace stops to identify the problem",
            ])
            if trace_data["hops"] and trace_data["hops"][-1].get("timed_out"):
                suggestions.append(
                    "The last hop timed out - may indicate firewall blocking"
                )
        elif trace_data["total_hops"] > 15:
            suggestions.append(
                f"Route has many hops ({trace_data['total_hops']}) - may affect latency"
            )

        # Check for high latency hops
        for hop in trace_data.get("hops", []):
            if hop.get("avg_time_ms") and hop["avg_time_ms"] > 100:
                suggestions.append(
                    f"Hop {hop['hop_number']} has high latency ({hop['avg_time_ms']:.1f}ms)"
                )
                break

        return self._success(
            data=trace_data,
            raw_output=result.stdout,
            suggestions=suggestions if suggestions else None,
        )

    def _parse_traceroute_output(self, output: str) -> dict[str, Any]:
        """Parse traceroute/tracert output across platforms."""
        hops: list[dict[str, Any]] = []
        destination_reached = False

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Skip header lines
            if line.startswith("traceroute") or line.startswith("Tracing route"):
                continue
            if "hops maximum" in line.lower() or "over a maximum" in line.lower():
                continue

            # Parse hop lines - format varies by platform
            # Windows: "  1    <1 ms    <1 ms    <1 ms  192.168.1.1"
            # macOS/Linux: " 1  192.168.1.1 (192.168.1.1)  0.505 ms  0.395 ms  0.378 ms"

            # Try to extract hop number
            hop_match = re.match(r"\s*(\d+)\s+", line)
            if not hop_match:
                continue

            hop_number = int(hop_match.group(1))

            # Check for timeout (asterisks)
            if "* * *" in line or line.count("*") >= 3:
                hops.append({
                    "hop_number": hop_number,
                    "timed_out": True,
                    "address": None,
                    "hostname": None,
                    "times_ms": [],
                    "avg_time_ms": None,
                })
                continue

            # Extract IP addresses
            ip_match = re.search(
                r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line
            )
            address = ip_match.group(1) if ip_match else None

            # Extract hostname (if present in parentheses or before IP)
            hostname = None
            hostname_match = re.search(r"(\S+)\s+\(" + re.escape(address or "") + r"\)", line)
            if hostname_match:
                hostname = hostname_match.group(1)

            # Extract times
            times = []
            time_matches = re.findall(r"(\d+\.?\d*)\s*ms", line, re.IGNORECASE)
            for t in time_matches:
                try:
                    times.append(float(t))
                except ValueError:
                    pass

            # Handle Windows "<1 ms" notation
            if "<1 ms" in line.lower():
                count = line.lower().count("<1 ms")
                times.extend([0.5] * count)

            avg_time = sum(times) / len(times) if times else None

            hops.append({
                "hop_number": hop_number,
                "timed_out": False,
                "address": address,
                "hostname": hostname,
                "times_ms": times,
                "avg_time_ms": avg_time,
            })

        # Check if destination was reached (last hop has an address)
        if hops:
            last_hop = hops[-1]
            if last_hop.get("address") and not last_hop.get("timed_out"):
                destination_reached = True

        return {
            "destination_reached": destination_reached,
            "total_hops": len(hops),
            "hops": hops,
        }


# Module-level functions for easy importing
async def ping_address(host: str, count: int = 4) -> DiagnosticResult:
    """Ping a specified address."""
    diag = PingAddress()
    return await diag.run(host=host, count=count)


async def traceroute(host: str, max_hops: int = 30) -> DiagnosticResult:
    """Trace route to destination."""
    diag = Traceroute()
    return await diag.run(host=host, max_hops=max_hops)

