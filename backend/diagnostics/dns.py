"""DNS resolution diagnostic.

See docs/functions/test_dns_resolution.md for full specification.
"""

import re
import time
from typing import Any

from .base import BaseDiagnostic, DiagnosticResult
from .platform import Platform


class TestDNSResolution(BaseDiagnostic):
    """Test DNS name resolution."""

    name = "test_dns_resolution"
    description = "Test DNS resolution"
    osi_layer = "Application"

    # Default hostnames to test
    DEFAULT_HOSTS = ["google.com", "cloudflare.com"]

    async def run(
        self,
        hostnames: list[str] | None = None,
        dns_server: str | None = None,
    ) -> DiagnosticResult:
        """
        Test DNS resolution.

        Args:
            hostnames: Hostnames to resolve (default: google.com, cloudflare.com)
            dns_server: Specific DNS server to use (optional)

        Returns:
            DiagnosticResult with resolution results
        """
        hosts = hostnames or self.DEFAULT_HOSTS
        results = []
        total_time = 0.0
        resolved_count = 0

        for hostname in hosts:
            start = time.monotonic()
            result = await self._resolve_hostname(hostname, dns_server)
            elapsed = (time.monotonic() - start) * 1000  # ms

            result["resolution_time_ms"] = elapsed if result["resolved"] else None
            results.append(result)

            if result["resolved"]:
                resolved_count += 1
                total_time += elapsed

        # Calculate averages
        avg_time = total_time / resolved_count if resolved_count > 0 else None
        dns_working = resolved_count > 0

        # Determine DNS server used
        dns_used = dns_server
        if not dns_used and results and results[0].get("dns_server_used"):
            dns_used = results[0]["dns_server_used"]

        # Generate suggestions
        suggestions = []
        if not dns_working:
            suggestions.extend(
                [
                    "DNS resolution is not working",
                    "If ping_dns succeeded, this is a DNS-specific issue",
                    "Try changing DNS server to 8.8.8.8 or 1.1.1.1",
                ]
            )
            if self.platform == Platform.MACOS:
                suggestions.append(
                    "On macOS: System Preferences > Network > Advanced > DNS"
                )
            else:
                suggestions.append(
                    "On Windows: Network adapter settings > IPv4 > DNS server addresses"
                )
        elif resolved_count < len(hosts):
            failed = [r["hostname"] for r in results if not r["resolved"]]
            suggestions.append(
                f"DNS works but some domains failed: {', '.join(failed)}"
            )
            suggestions.append("These domains may not exist or may be blocked")

        return self._success(
            data={
                "hosts_tested": len(hosts),
                "hosts_resolved": resolved_count,
                "dns_working": dns_working,
                "results": results,
                "avg_resolution_time_ms": avg_time,
                "dns_server": dns_used,
            },
            raw_output="",
            suggestions=suggestions if suggestions else None,
        )

    async def _resolve_hostname(
        self, hostname: str, dns_server: str | None
    ) -> dict[str, Any]:
        """Resolve a single hostname."""
        # Build nslookup command
        if dns_server:
            cmd = f"nslookup {hostname} {dns_server}"
        else:
            cmd = f"nslookup {hostname}"

        result = await self.executor.run(cmd, shell=True, timeout=10)

        return self._parse_nslookup(hostname, result.stdout, result.stderr)

    def _parse_nslookup(
        self, hostname: str, stdout: str, stderr: str
    ) -> dict[str, Any]:
        """Parse nslookup output."""
        output = stdout + "\n" + stderr
        result = {
            "hostname": hostname,
            "resolved": False,
            "ip_addresses": [],
            "dns_server_used": None,
            "record_type": None,
            "error": None,
        }

        # Check for errors
        if "server can't find" in output.lower() or "nxdomain" in output.lower():
            result["error"] = "NXDOMAIN - domain not found"
            return result

        if "timed out" in output.lower() or "no response" in output.lower():
            result["error"] = "DNS request timed out"
            return result

        # Parse server
        server_match = re.search(r"Server:\s*(\S+)", output)
        if server_match:
            result["dns_server_used"] = server_match.group(1)

        # Parse addresses (after "Non-authoritative answer" or "Name:")
        in_answer = False
        for line in output.split("\n"):
            if "non-authoritative answer" in line.lower() or "name:" in line.lower():
                in_answer = True
                continue

            if in_answer:
                # Match "Address: x.x.x.x" or "Addresses: x.x.x.x"
                addr_match = re.search(r"Address(?:es)?:\s*(\d+\.\d+\.\d+\.\d+)", line)
                if addr_match:
                    ip = addr_match.group(1)
                    # Skip the DNS server address
                    if ip != result["dns_server_used"]:
                        result["ip_addresses"].append(ip)
                        result["resolved"] = True
                        result["record_type"] = "A"

        return result


async def test_dns_resolution(
    hostnames: list[str] | None = None,
    dns_server: str | None = None,
) -> DiagnosticResult:
    """Test DNS resolution."""
    diag = TestDNSResolution()
    return await diag.run(hostnames=hostnames, dns_server=dns_server)


