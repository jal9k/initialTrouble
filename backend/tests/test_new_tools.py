"""Tests for new diagnostic tools.

Tests for:
- ping_address
- traceroute  
- toggle_bluetooth
- ip_release
- ip_renew
- flush_dns
- robocopy (Windows only)
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.diagnostics.platform import Platform, CommandResult


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_command_result_success():
    """Create a successful command result."""
    def _create(stdout="", stderr="", return_code=0):
        return CommandResult(stdout=stdout, stderr=stderr, return_code=return_code)
    return _create


@pytest.fixture
def mock_executor():
    """Create a mock command executor."""
    executor = AsyncMock()
    return executor


# =============================================================================
# TestPingAddress
# =============================================================================

class TestPingAddress:
    """Tests for ping_address diagnostic."""

    @pytest.mark.asyncio
    async def test_ping_address_success(self):
        """Should parse successful ping output correctly."""
        from backend.diagnostics.reachability import PingAddress

        diag = PingAddress()

        mock_output = """PING google.com (142.250.80.46): 56 data bytes
64 bytes from 142.250.80.46: icmp_seq=0 ttl=117 time=12.3 ms
64 bytes from 142.250.80.46: icmp_seq=1 ttl=117 time=11.8 ms

--- google.com ping statistics ---
2 packets transmitted, 2 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 11.8/12.0/12.3/0.25 ms"""

        with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = CommandResult(
                stdout=mock_output, stderr="", return_code=0
            )
            
            result = await diag.run(host="google.com", count=2)
            
            assert result.success is True
            assert result.data["reachable"] is True
            assert result.data["packets_received"] == 2
            assert result.data["packet_loss_percent"] == 0.0
            assert result.data["host"] == "google.com"

    @pytest.mark.asyncio
    async def test_ping_address_unreachable(self):
        """Should detect unreachable host."""
        from backend.diagnostics.reachability import PingAddress

        diag = PingAddress()

        mock_output = """PING 192.168.255.255 (192.168.255.255): 56 data bytes
Request timeout for icmp_seq 0
Request timeout for icmp_seq 1

--- 192.168.255.255 ping statistics ---
2 packets transmitted, 0 packets received, 100.0% packet loss"""

        with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = CommandResult(
                stdout=mock_output, stderr="", return_code=1
            )
            
            result = await diag.run(host="192.168.255.255")
            
            assert result.data["reachable"] is False
            assert result.data["packet_loss_percent"] == 100.0

    @pytest.mark.asyncio
    async def test_ping_address_missing_host(self):
        """Should fail if host is not provided."""
        from backend.diagnostics.reachability import PingAddress

        diag = PingAddress()
        result = await diag.run(host="")
        
        assert result.success is False
        assert "Host address is required" in result.error

    @pytest.mark.asyncio
    async def test_ping_address_custom_count(self):
        """Should use custom ping count."""
        from backend.diagnostics.reachability import PingAddress

        diag = PingAddress()

        with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = CommandResult(
                stdout="", stderr="", return_code=0
            )
            
            await diag.run(host="8.8.8.8", count=10)
            
            # Verify count was passed to command
            call_args = mock_run.call_args[0][0]
            assert "-c 10" in call_args or "-n 10" in call_args


# =============================================================================
# TestTraceroute
# =============================================================================

class TestTraceroute:
    """Tests for traceroute diagnostic."""

    @pytest.mark.asyncio
    async def test_traceroute_success(self):
        """Should parse successful traceroute output."""
        from backend.diagnostics.reachability import Traceroute

        diag = Traceroute()

        mock_output = """traceroute to google.com (142.250.80.46), 30 hops max, 60 byte packets
 1  192.168.1.1 (192.168.1.1)  0.505 ms  0.395 ms  0.378 ms
 2  10.0.0.1 (10.0.0.1)  5.234 ms  5.123 ms  5.456 ms
 3  142.250.80.46 (142.250.80.46)  12.345 ms  12.234 ms  12.123 ms"""

        with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = CommandResult(
                stdout=mock_output, stderr="", return_code=0
            )
            
            result = await diag.run(host="google.com")
            
            assert result.success is True
            assert result.data["destination_reached"] is True
            assert result.data["total_hops"] == 3
            assert len(result.data["hops"]) == 3

    @pytest.mark.asyncio
    async def test_traceroute_timeout(self):
        """Should handle hop timeouts."""
        from backend.diagnostics.reachability import Traceroute

        diag = Traceroute()

        mock_output = """traceroute to 10.255.255.1, 30 hops max
 1  192.168.1.1 (192.168.1.1)  0.5 ms  0.4 ms  0.3 ms
 2  * * *
 3  * * *"""

        with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = CommandResult(
                stdout=mock_output, stderr="", return_code=0
            )
            
            result = await diag.run(host="10.255.255.1")
            
            assert result.data["destination_reached"] is False
            # Check that timed out hops are detected
            timed_out_hops = [h for h in result.data["hops"] if h.get("timed_out")]
            assert len(timed_out_hops) >= 1

    @pytest.mark.asyncio
    async def test_traceroute_max_hops(self):
        """Should respect max_hops parameter."""
        from backend.diagnostics.reachability import Traceroute

        diag = Traceroute()

        with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = CommandResult(
                stdout="", stderr="", return_code=0
            )
            
            await diag.run(host="google.com", max_hops=15)
            
            call_args = mock_run.call_args[0][0]
            assert "-m 15" in call_args or "-h 15" in call_args

    @pytest.mark.asyncio
    async def test_traceroute_missing_host(self):
        """Should fail if host not provided."""
        from backend.diagnostics.reachability import Traceroute

        diag = Traceroute()
        result = await diag.run(host="")
        
        assert result.success is False
        assert "Destination host is required" in result.error


# =============================================================================
# TestToggleBluetooth
# =============================================================================

class TestToggleBluetooth:
    """Tests for toggle_bluetooth diagnostic."""

    @pytest.mark.asyncio
    async def test_bluetooth_status_macos(self):
        """Should get Bluetooth status on macOS."""
        from backend.diagnostics.bluetooth import ToggleBluetooth

        diag = ToggleBluetooth()

        with patch.object(diag, 'platform', Platform.MACOS):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                # First call checks for blueutil, second gets status
                mock_run.side_effect = [
                    CommandResult(stdout="/usr/local/bin/blueutil", stderr="", return_code=0),
                    CommandResult(stdout="1", stderr="", return_code=0),
                ]
                
                result = await diag.run(action="status")
                
                assert result.success is True
                assert result.data["bluetooth_enabled"] is True
                assert result.data["state"] == "on"

    @pytest.mark.asyncio
    async def test_bluetooth_enable_macos(self):
        """Should enable Bluetooth on macOS."""
        from backend.diagnostics.bluetooth import ToggleBluetooth

        diag = ToggleBluetooth()

        with patch.object(diag, 'platform', Platform.MACOS):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.side_effect = [
                    CommandResult(stdout="/usr/local/bin/blueutil", stderr="", return_code=0),
                    CommandResult(stdout="0", stderr="", return_code=0),  # Currently off
                    CommandResult(stdout="", stderr="", return_code=0),   # Enable command
                    CommandResult(stdout="1", stderr="", return_code=0),  # Verify it's on
                ]
                
                result = await diag.run(action="on")
                
                assert result.success is True
                assert result.data["changed"] is True
                assert result.data["previous_state"] == "off"

    @pytest.mark.asyncio
    async def test_bluetooth_disable_macos(self):
        """Should disable Bluetooth on macOS."""
        from backend.diagnostics.bluetooth import ToggleBluetooth

        diag = ToggleBluetooth()

        with patch.object(diag, 'platform', Platform.MACOS):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.side_effect = [
                    CommandResult(stdout="/usr/local/bin/blueutil", stderr="", return_code=0),
                    CommandResult(stdout="1", stderr="", return_code=0),  # Currently on
                    CommandResult(stdout="", stderr="", return_code=0),   # Disable command
                    CommandResult(stdout="0", stderr="", return_code=0),  # Verify it's off
                ]
                
                result = await diag.run(action="off")
                
                assert result.success is True
                assert result.data["changed"] is True

    @pytest.mark.asyncio
    async def test_bluetooth_already_enabled(self):
        """Should handle already enabled state."""
        from backend.diagnostics.bluetooth import ToggleBluetooth

        diag = ToggleBluetooth()

        with patch.object(diag, 'platform', Platform.MACOS):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.side_effect = [
                    CommandResult(stdout="/usr/local/bin/blueutil", stderr="", return_code=0),
                    CommandResult(stdout="1", stderr="", return_code=0),  # Already on
                ]
                
                result = await diag.run(action="on")
                
                assert result.success is True
                assert result.data["changed"] is False

    @pytest.mark.asyncio
    async def test_bluetooth_invalid_action(self):
        """Should reject invalid action."""
        from backend.diagnostics.bluetooth import ToggleBluetooth

        diag = ToggleBluetooth()
        
        result = await diag.run(action="invalid")
        
        assert result.success is False
        assert "Invalid action" in result.error

    @pytest.mark.asyncio
    async def test_bluetooth_linux_status(self):
        """Should get Bluetooth status on Linux using rfkill."""
        from backend.diagnostics.bluetooth import ToggleBluetooth

        diag = ToggleBluetooth()

        with patch.object(diag, 'platform', Platform.LINUX):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = CommandResult(
                    stdout="0: hci0: Bluetooth\n\tSoft blocked: no\n\tHard blocked: no",
                    stderr="", return_code=0
                )
                
                result = await diag.run(action="status")
                
                assert result.success is True
                assert result.data["bluetooth_enabled"] is True


# =============================================================================
# TestIpRelease
# =============================================================================

class TestIpRelease:
    """Tests for ip_release diagnostic."""

    @pytest.mark.asyncio
    async def test_ip_release_success_windows(self):
        """Should release IP on Windows."""
        from backend.diagnostics.ip_reset import IpRelease

        diag = IpRelease()

        with patch.object(diag, 'platform', Platform.WINDOWS):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = CommandResult(
                    stdout="Windows IP Configuration\n\nEthernet adapter released",
                    stderr="", return_code=0
                )
                
                result = await diag.run()
                
                assert result.success is True
                assert result.data["released"] is True

    @pytest.mark.asyncio
    async def test_ip_release_with_interface(self):
        """Should release IP for specific interface."""
        from backend.diagnostics.ip_reset import IpRelease

        diag = IpRelease()

        with patch.object(diag, 'platform', Platform.WINDOWS):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = CommandResult(
                    stdout="Released", stderr="", return_code=0
                )
                
                result = await diag.run(interface="Ethernet")
                
                assert result.success is True
                call_args = mock_run.call_args[0][0]
                assert "Ethernet" in call_args

    @pytest.mark.asyncio
    async def test_ip_release_requires_admin(self):
        """Should detect when admin privileges are required."""
        from backend.diagnostics.ip_reset import IpRelease

        diag = IpRelease()

        with patch.object(diag, 'platform', Platform.WINDOWS):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = CommandResult(
                    stdout="", stderr="requires elevation", return_code=1
                )
                
                result = await diag.run()
                
                assert result.success is False
                assert "Administrator privileges required" in result.error


# =============================================================================
# TestIpRenew
# =============================================================================

class TestIpRenew:
    """Tests for ip_renew diagnostic."""

    @pytest.mark.asyncio
    async def test_ip_renew_success_windows(self):
        """Should renew IP on Windows."""
        from backend.diagnostics.ip_reset import IpRenew

        diag = IpRenew()

        mock_output = """Windows IP Configuration

Ethernet adapter Ethernet:

   IPv4 Address. . . . . . . . . . . : 192.168.1.100
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . : 192.168.1.1"""

        with patch.object(diag, 'platform', Platform.WINDOWS):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = CommandResult(
                    stdout=mock_output, stderr="", return_code=0
                )
                
                result = await diag.run()
                
                assert result.success is True
                assert result.data["renewed"] is True
                assert result.data["new_ip"] == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_ip_renew_with_interface(self):
        """Should renew IP for specific interface."""
        from backend.diagnostics.ip_reset import IpRenew

        diag = IpRenew()

        with patch.object(diag, 'platform', Platform.WINDOWS):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = CommandResult(
                    stdout="Renewed", stderr="", return_code=0
                )
                
                result = await diag.run(interface="Wi-Fi")
                
                call_args = mock_run.call_args[0][0]
                assert "Wi-Fi" in call_args

    @pytest.mark.asyncio
    async def test_ip_renew_dhcp_failure(self):
        """Should handle DHCP server unreachable."""
        from backend.diagnostics.ip_reset import IpRenew

        diag = IpRenew()

        with patch.object(diag, 'platform', Platform.WINDOWS):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = CommandResult(
                    stdout="", stderr="Unable to contact DHCP server", return_code=1
                )
                
                result = await diag.run()
                
                assert result.success is False
                assert "DHCP server" in result.error


# =============================================================================
# TestFlushDns
# =============================================================================

class TestFlushDns:
    """Tests for flush_dns diagnostic."""

    @pytest.mark.asyncio
    async def test_flush_dns_success_windows(self):
        """Should flush DNS on Windows."""
        from backend.diagnostics.ip_reset import FlushDns

        diag = FlushDns()

        with patch.object(diag, 'platform', Platform.WINDOWS):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = CommandResult(
                    stdout="Windows IP Configuration\n\nSuccessfully flushed the DNS Resolver Cache.",
                    stderr="", return_code=0
                )
                
                result = await diag.run()
                
                assert result.success is True
                assert result.data["flushed"] is True

    @pytest.mark.asyncio
    async def test_flush_dns_success_macos(self):
        """Should flush DNS on macOS."""
        from backend.diagnostics.ip_reset import FlushDns

        diag = FlushDns()

        with patch.object(diag, 'platform', Platform.MACOS):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = CommandResult(
                    stdout="", stderr="", return_code=0
                )
                
                result = await diag.run()
                
                assert result.success is True
                assert result.data["flushed"] is True

    @pytest.mark.asyncio
    async def test_flush_dns_requires_admin(self):
        """Should handle permission denied."""
        from backend.diagnostics.ip_reset import FlushDns

        diag = FlushDns()

        with patch.object(diag, 'platform', Platform.WINDOWS):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = CommandResult(
                    stdout="", stderr="requires elevation", return_code=1
                )
                
                result = await diag.run()
                
                assert result.success is False


# =============================================================================
# TestRobocopy
# =============================================================================

class TestRobocopy:
    """Tests for robocopy diagnostic (Windows only)."""

    @pytest.mark.asyncio
    async def test_robocopy_basic_copy(self):
        """Should perform basic copy operation."""
        from backend.diagnostics.windows.robocopy import Robocopy

        diag = Robocopy()

        mock_output = """-------------------------------------------------------------------------------
   ROBOCOPY     ::     Robust File Copy for Windows
-------------------------------------------------------------------------------

  Started : Tuesday, December 24, 2024 10:00:00 AM
   Source : C:\\Source\\
     Dest : D:\\Dest\\

    Files : *.*

  Options : /R:3 /W:10

------------------------------------------------------------------------------

                           Total    Copied   Skipped  Mismatch    FAILED    Extras
    Dirs :         5         2         3         0         0         0
   Files :        10         8         2         0         0         0
   Bytes :     1.5 m     1.2 m   300.0 k         0         0         0"""

        with patch.object(diag, 'platform', Platform.WINDOWS):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = CommandResult(
                    stdout=mock_output, stderr="", return_code=1  # Exit code 1 = success
                )
                
                result = await diag.run(source="C:\\Source", destination="D:\\Dest")
                
                assert result.success is True
                assert result.data["files_copied"] == 8
                assert result.data["source"] == "C:\\Source"

    @pytest.mark.asyncio
    async def test_robocopy_with_retries(self):
        """Should include retry options in command."""
        from backend.diagnostics.windows.robocopy import Robocopy

        diag = Robocopy()

        with patch.object(diag, 'platform', Platform.WINDOWS):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = CommandResult(
                    stdout="", stderr="", return_code=0
                )
                
                await diag.run(
                    source="C:\\Source",
                    destination="D:\\Dest",
                    retries=5,
                    wait=15
                )
                
                call_args = mock_run.call_args[0][0]
                assert "/R:5" in call_args
                assert "/W:15" in call_args

    @pytest.mark.asyncio
    async def test_robocopy_mirror_mode(self):
        """Should use mirror mode when specified."""
        from backend.diagnostics.windows.robocopy import Robocopy

        diag = Robocopy()

        with patch.object(diag, 'platform', Platform.WINDOWS):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = CommandResult(
                    stdout="", stderr="", return_code=0
                )
                
                await diag.run(
                    source="C:\\Source",
                    destination="D:\\Dest",
                    mirror=True
                )
                
                call_args = mock_run.call_args[0][0]
                assert "/MIR" in call_args

    @pytest.mark.asyncio
    async def test_robocopy_move_mode(self):
        """Should use move mode when specified."""
        from backend.diagnostics.windows.robocopy import Robocopy

        diag = Robocopy()

        with patch.object(diag, 'platform', Platform.WINDOWS):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = CommandResult(
                    stdout="", stderr="", return_code=0
                )
                
                await diag.run(
                    source="C:\\Source",
                    destination="D:\\Dest",
                    move=True
                )
                
                call_args = mock_run.call_args[0][0]
                assert "/MOV" in call_args

    @pytest.mark.asyncio
    async def test_robocopy_non_windows_platform(self):
        """Should fail on non-Windows platforms."""
        from backend.diagnostics.windows.robocopy import Robocopy

        diag = Robocopy()

        with patch.object(diag, 'platform', Platform.MACOS):
            result = await diag.run(source="/source", destination="/dest")
            
            assert result.success is False
            assert "only available on Windows" in result.error
            assert "rsync" in str(result.suggestions)

    @pytest.mark.asyncio
    async def test_robocopy_missing_source(self):
        """Should fail if source is missing."""
        from backend.diagnostics.windows.robocopy import Robocopy

        diag = Robocopy()

        with patch.object(diag, 'platform', Platform.WINDOWS):
            result = await diag.run(source="", destination="D:\\Dest")
            
            assert result.success is False
            assert "Source directory is required" in result.error

    @pytest.mark.asyncio
    async def test_robocopy_error_exit_code(self):
        """Should detect error exit codes (8+)."""
        from backend.diagnostics.windows.robocopy import Robocopy

        diag = Robocopy()

        with patch.object(diag, 'platform', Platform.WINDOWS):
            with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = CommandResult(
                    stdout="Some files could not be copied",
                    stderr="Access denied",
                    return_code=8  # Copy errors
                )
                
                result = await diag.run(source="C:\\Source", destination="D:\\Dest")
                
                assert result.success is False
                assert result.data["exit_code"] == 8


# =============================================================================
# Integration Tests - Module-level Functions
# =============================================================================

class TestModuleLevelFunctions:
    """Tests for module-level convenience functions."""

    @pytest.mark.asyncio
    async def test_ping_address_function(self):
        """Should call ping_address correctly."""
        from backend.diagnostics.reachability import ping_address

        with patch('backend.diagnostics.reachability.PingAddress') as MockClass:
            mock_instance = AsyncMock()
            mock_instance.run.return_value = MagicMock(success=True)
            MockClass.return_value = mock_instance

            await ping_address(host="google.com", count=3)

            mock_instance.run.assert_called_once_with(host="google.com", count=3)

    @pytest.mark.asyncio
    async def test_traceroute_function(self):
        """Should call traceroute correctly."""
        from backend.diagnostics.reachability import traceroute

        with patch('backend.diagnostics.reachability.Traceroute') as MockClass:
            mock_instance = AsyncMock()
            mock_instance.run.return_value = MagicMock(success=True)
            MockClass.return_value = mock_instance

            await traceroute(host="google.com", max_hops=15)

            mock_instance.run.assert_called_once_with(host="google.com", max_hops=15)

    @pytest.mark.asyncio
    async def test_toggle_bluetooth_function(self):
        """Should call toggle_bluetooth correctly."""
        from backend.diagnostics.bluetooth import toggle_bluetooth

        with patch('backend.diagnostics.bluetooth.ToggleBluetooth') as MockClass:
            mock_instance = AsyncMock()
            mock_instance.run.return_value = MagicMock(success=True)
            MockClass.return_value = mock_instance

            await toggle_bluetooth(action="status")

            mock_instance.run.assert_called_once_with(action="status", interface=None)

    @pytest.mark.asyncio
    async def test_ip_release_function(self):
        """Should call ip_release correctly."""
        from backend.diagnostics.ip_reset import ip_release

        with patch('backend.diagnostics.ip_reset.IpRelease') as MockClass:
            mock_instance = AsyncMock()
            mock_instance.run.return_value = MagicMock(success=True)
            MockClass.return_value = mock_instance

            await ip_release(interface="en0")

            mock_instance.run.assert_called_once_with(interface="en0")

    @pytest.mark.asyncio
    async def test_ip_renew_function(self):
        """Should call ip_renew correctly."""
        from backend.diagnostics.ip_reset import ip_renew

        with patch('backend.diagnostics.ip_reset.IpRenew') as MockClass:
            mock_instance = AsyncMock()
            mock_instance.run.return_value = MagicMock(success=True)
            MockClass.return_value = mock_instance

            await ip_renew(interface="eth0")

            mock_instance.run.assert_called_once_with(interface="eth0")

    @pytest.mark.asyncio
    async def test_flush_dns_function(self):
        """Should call flush_dns correctly."""
        from backend.diagnostics.ip_reset import flush_dns

        with patch('backend.diagnostics.ip_reset.FlushDns') as MockClass:
            mock_instance = AsyncMock()
            mock_instance.run.return_value = MagicMock(success=True)
            MockClass.return_value = mock_instance

            await flush_dns()

            mock_instance.run.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_robocopy_function(self):
        """Should call robocopy correctly."""
        from backend.diagnostics.windows.robocopy import robocopy

        with patch('backend.diagnostics.windows.robocopy.Robocopy') as MockClass:
            mock_instance = AsyncMock()
            mock_instance.run.return_value = MagicMock(success=True)
            MockClass.return_value = mock_instance

            await robocopy(
                source="C:\\Source",
                destination="D:\\Dest",
                mirror=True
            )

            mock_instance.run.assert_called_once_with(
                source="C:\\Source",
                destination="D:\\Dest",
                files=None,
                retries=3,
                wait=10,
                mirror=True,
                move=False,
            )

