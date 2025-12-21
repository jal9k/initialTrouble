"""Tests for diagnostic functions."""

import pytest
from unittest.mock import AsyncMock, patch

from backend.diagnostics.adapter import CheckAdapterStatus, check_adapter_status
from backend.diagnostics.connectivity import PingGateway, ping_gateway
from backend.diagnostics.dns import test_dns_resolution


class TestCheckAdapterStatus:
    """Tests for check_adapter_status diagnostic."""

    @pytest.mark.asyncio
    async def test_parses_macos_ifconfig(self):
        """Should parse macOS ifconfig output correctly."""
        diag = CheckAdapterStatus()

        mock_output = """
en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
\tether a4:83:e7:12:34:56
\tinet 192.168.1.100 netmask 0xffffff00 broadcast 192.168.1.255
\tstatus: active
lo0: flags=8049<UP,LOOPBACK,RUNNING,MULTICAST> mtu 16384
\tinet 127.0.0.1 netmask 0xff000000
"""

        with patch.object(diag, "platform") as mock_platform:
            mock_platform.value = "macos"
            mock_platform.__eq__ = lambda self, other: str(self) == str(other)

            adapters = diag._parse_macos_ifconfig(mock_output)

            # Should find en0 with IP
            en0 = next((a for a in adapters if a["name"] == "en0"), None)
            assert en0 is not None
            assert en0["status"] == "up"
            assert en0["has_ip"] is True
            assert en0["mac_address"] == "a4:83:e7:12:34:56"


class TestPingGateway:
    """Tests for ping_gateway diagnostic."""

    def test_parses_macos_ping_output(self):
        """Should parse macOS ping output correctly."""
        diag = PingGateway()

        mock_output = """
PING 192.168.1.1 (192.168.1.1): 56 data bytes
64 bytes from 192.168.1.1: icmp_seq=0 ttl=64 time=1.234 ms
64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=1.456 ms

--- 192.168.1.1 ping statistics ---
2 packets transmitted, 2 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 1.234/1.345/1.456/0.111 ms
"""

        result = diag._parse_ping_output(mock_output)

        assert result["reachable"] is True
        assert result["packets_sent"] == 2
        assert result["packets_received"] == 2
        assert result["packet_loss_percent"] == 0.0
        assert len(result["results"]) == 2

    def test_parses_timeout_output(self):
        """Should detect timeout correctly."""
        diag = PingGateway()

        mock_output = """
PING 192.168.1.1 (192.168.1.1): 56 data bytes
Request timeout for icmp_seq 0
Request timeout for icmp_seq 1

--- 192.168.1.1 ping statistics ---
2 packets transmitted, 0 packets received, 100.0% packet loss
"""

        result = diag._parse_ping_output(mock_output)

        assert result["reachable"] is False
        assert result["packet_loss_percent"] == 100.0


class TestDNSResolutionDiagnostic:
    """Tests for test_dns_resolution diagnostic."""

    def test_parses_nslookup_success(self):
        """Should parse successful nslookup output."""
        from backend.diagnostics.dns import TestDNSResolution as DNSResolutionDiag
        diag = DNSResolutionDiag()

        mock_output = """
Server:\t\t192.168.1.1
Address:\t192.168.1.1#53

Non-authoritative answer:
Name:\tgoogle.com
Address: 142.250.80.46
"""

        result = diag._parse_nslookup("google.com", mock_output, "")

        assert result["resolved"] is True
        assert "142.250.80.46" in result["ip_addresses"]
        assert result["dns_server_used"] == "192.168.1.1"

    def test_parses_nslookup_nxdomain(self):
        """Should detect NXDOMAIN errors."""
        from backend.diagnostics.dns import TestDNSResolution as DNSResolutionDiag
        diag = DNSResolutionDiag()

        mock_output = """
Server:\t\t192.168.1.1
Address:\t192.168.1.1#53

** server can't find nonexistent.invalid: NXDOMAIN
"""

        result = diag._parse_nslookup("nonexistent.invalid", mock_output, "")

        assert result["resolved"] is False
        assert "NXDOMAIN" in result["error"]

