# Multi-OS Agent Architecture and Tool Expansion Plan

## Executive Summary

This document outlines the expansion of the Network Diagnostics CLI into a comprehensive system troubleshooting platform. The expansion introduces three major changes: a hierarchical agent architecture with OS-specific routing, new cross-platform diagnostic and remediation tools, and Windows-specific advanced troubleshooting capabilities. A future phase will add vision model integration for GUI-based automation.

The current system uses a single diagnostic agent that handles all troubleshooting regardless of operating system. While the underlying tools have platform-specific implementations, the agent itself doesn't specialize its reasoning or tool selection based on OS context. The new architecture introduces a Manager Agent that detects the operating system and delegates to specialized agents, each with access to tools relevant to their platform.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Agent Hierarchy Design](#agent-hierarchy-design)
3. [Cross-Platform Tools](#cross-platform-tools)
4. [Windows-Specific Tools](#windows-specific-tools)
5. [Implementation Phases](#implementation-phases)
6. [File Structure](#file-structure)
7. [Detailed Tool Specifications](#detailed-tool-specifications)
8. [Future: Vision Model Integration](#future-vision-model-integration)

---

## Architecture Overview

### Current Architecture

The existing system follows a flat structure where a single diagnostic agent receives all user queries and has access to all registered tools. The agent relies on its prompt to make decisions about which tools to use, but it has no awareness of OS-specific workflows or advanced remediation capabilities.

```
User Input
    │
    ▼
┌─────────────────────┐
│  Diagnostic Agent   │
│  (Single Prompt)    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   Tool Registry     │
│  (All Tools Mixed)  │
└─────────────────────┘
```

### Proposed Architecture

The new architecture introduces a Manager Agent that serves as the entry point for all user interactions. The Manager performs initial triage, detects the operating system, and delegates to the appropriate OS-specific agent. Each OS agent has specialized knowledge about its platform's quirks, common issues, and remediation workflows.

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                      MANAGER AGENT                          │
│                                                             │
│  Responsibilities:                                          │
│  • Detect operating system                                  │
│  • Perform initial triage (categorize issue type)          │
│  • Route to appropriate OS agent                           │
│  • Synthesize final response if multiple agents consulted  │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  macOS Agent    │ │  Windows Agent  │ │  Linux Agent    │
│                 │ │                 │ │                 │
│  Tools:         │ │  Tools:         │ │  Tools:         │
│  • Network      │ │  • Network      │ │  • Network      │
│  • Temp Files   │ │  • Temp Files   │ │  • Temp Files   │
│  • Process Mgmt │ │  • Process Mgmt │ │  • Process Mgmt │
│  • VPN Tests    │ │  • VPN Tests    │ │  • VPN Tests    │
│                 │ │  • Dell Audio   │ │                 │
│                 │ │  • O365 Repair  │ │                 │
│                 │ │  • DISM/SFC     │ │                 │
│                 │ │  • Log Review   │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Why This Architecture?

The single-agent approach works well for simple network diagnostics, but it struggles when the solution space expands to include OS-specific workflows. Consider the Dell audio driver fix: this involves removing a specific device driver from Device Manager and rebooting. A macOS agent should never suggest this, and a Linux agent would use completely different commands. By separating the agents, each one can be prompted with deep knowledge about its platform without confusing the model with irrelevant information.

Additionally, different operating systems have different "personalities" in troubleshooting. Windows troubleshooting often involves the registry, PowerShell cmdlets, and GUI-based repair tools. macOS troubleshooting involves Terminal commands, preference files, and occasionally Automator. Linux troubleshooting involves systemd, configuration files, and package managers. Each agent can be trained on these patterns independently.

---

## Agent Hierarchy Design

### Manager Agent

The Manager Agent is the first point of contact for user queries. It has three primary responsibilities: operating system detection, issue categorization, and agent routing. The Manager does not perform diagnostics itself; it delegates to specialized agents.

The Manager Agent's prompt should be concise and focused on routing logic rather than troubleshooting knowledge. Here is the proposed structure for the Manager Agent prompt:

```markdown
# Manager Agent

You are a triage coordinator for system troubleshooting. Your job is to understand the user's problem and route it to the correct specialist agent.

## Operating System Detection

The current operating system is: {detected_os}

If the OS could not be detected, ask the user: "What operating system are you using? (Windows, macOS, or Linux)"

## Issue Categories

Categorize the user's problem into one of these types:

| Category | Keywords | Route To |
|----------|----------|----------|
| NETWORK | internet, wifi, ethernet, connection, DNS, IP | {os}_network_agent |
| PERFORMANCE | slow, freeze, hang, crash, memory, CPU | {os}_performance_agent |
| APPLICATION | app, program, software, Office, browser | {os}_application_agent |
| SYSTEM | boot, startup, driver, update, repair | {os}_system_agent |
| STORAGE | disk, space, files, delete, cleanup | {os}_storage_agent |

## Your Response Format

After categorizing, respond with:

**Operating System**: {os}
**Issue Category**: {category}
**Routing To**: {agent_name}
**Initial Assessment**: {one sentence summary}

Then hand off to the appropriate agent by calling the route_to_agent tool.

## Rules

1. Do not attempt to solve the problem yourself
2. If the issue spans multiple categories, pick the primary one
3. If you cannot categorize the issue, ask one clarifying question
4. Always confirm the operating system before routing
```

### OS-Specific Agents

Each operating system has a dedicated agent with specialized knowledge. The agents share a common structure but differ in their tool access and platform-specific guidance.

#### macOS Agent Structure

The macOS agent understands Apple-specific concepts like System Preferences, Terminal, diskutil, networksetup, and the Apple ecosystem. Its prompt includes guidance on common macOS issues and the appropriate tools to diagnose them.

```markdown
# macOS Diagnostic Agent

You are a macOS troubleshooting specialist. You diagnose and fix problems on Apple computers running macOS.

## Platform Context

You are running on macOS. Use macOS-specific commands and tools. Never suggest Windows commands like ipconfig or PowerShell.

## Available Tools

### Network Diagnostics
- check_adapter_status: Check network interface status via ifconfig
- get_ip_config: Get IP configuration via ifconfig and networksetup
- ping_gateway: Test router connectivity
- ping_dns: Test internet connectivity
- test_dns_resolution: Test DNS via nslookup
- test_vpn_connectivity: Test VPN tunnel status

### System Maintenance
- cleanup_temp_files: Remove temporary files from ~/Library/Caches and /tmp
- kill_process: Terminate processes via kill or pkill
- get_system_info: Get macOS version, hardware info via system_profiler

## macOS-Specific Knowledge

- Network settings are in System Preferences > Network (or System Settings on Ventura+)
- DNS can be changed via: networksetup -setdnsservers Wi-Fi 8.8.8.8
- WiFi can be toggled via: networksetup -setairportpower en0 off/on
- The primary WiFi interface is typically en0
- Flush DNS cache: sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
- Check for macOS updates: softwareupdate -l
```

#### Windows Agent Structure

The Windows agent understands Windows-specific concepts like PowerShell, Device Manager, the Registry, Group Policy, and Windows services. It has access to advanced Windows-only tools for driver management, Office repair, and system file checking.

```markdown
# Windows Diagnostic Agent

You are a Windows troubleshooting specialist. You diagnose and fix problems on computers running Microsoft Windows.

## Platform Context

You are running on Windows. Use PowerShell commands and Windows tools. Never suggest macOS commands like networksetup or ifconfig.

## Available Tools

### Network Diagnostics
- check_adapter_status: Check network adapter status via Get-NetAdapter
- get_ip_config: Get IP configuration via Get-NetIPConfiguration
- ping_gateway: Test router connectivity
- ping_dns: Test internet connectivity
- test_dns_resolution: Test DNS resolution
- test_vpn_connectivity: Test VPN tunnel status

### System Maintenance
- cleanup_temp_files: Remove temporary files from %TEMP%, Windows\Temp
- kill_process: Terminate processes via Stop-Process
- get_system_info: Get Windows version, hardware info

### Windows-Specific Tools
- fix_dell_audio: Remove and reinstall Dell audio drivers
- repair_office365: Run Microsoft 365 repair (local or cloud)
- run_dism_sfc: Run DISM and SFC system file repair
- review_system_logs: Analyze Event Viewer, crash dumps, BSOD logs

## Windows-Specific Knowledge

- Network settings are in Settings > Network & Internet
- DNS can be changed via: Set-DnsClientServerAddress -InterfaceIndex X -ServerAddresses ("8.8.8.8","8.8.4.4")
- Flush DNS cache: ipconfig /flushdns
- Release/renew IP: ipconfig /release && ipconfig /renew
- Check for Windows updates: Settings > Windows Update
- Device Manager: devmgmt.msc
- Reliability Monitor: perfmon /rel
```

#### Linux Agent Structure

The Linux agent understands Linux-specific concepts like systemd, NetworkManager, ip/nmcli commands, and distribution-specific package managers.

```markdown
# Linux Diagnostic Agent

You are a Linux troubleshooting specialist. You diagnose and fix problems on computers running Linux distributions.

## Platform Context

You are running on Linux. Use Linux commands and tools. The specific distribution may affect available commands.

## Available Tools

### Network Diagnostics
- check_adapter_status: Check network interface status via ip link
- get_ip_config: Get IP configuration via ip addr and nmcli
- ping_gateway: Test router connectivity
- ping_dns: Test internet connectivity
- test_dns_resolution: Test DNS resolution
- test_vpn_connectivity: Test VPN tunnel status

### System Maintenance
- cleanup_temp_files: Remove temporary files from /tmp, /var/tmp, user caches
- kill_process: Terminate processes via kill or pkill
- get_system_info: Get Linux distribution, kernel version, hardware info

## Linux-Specific Knowledge

- Network management varies: NetworkManager (nmcli), systemd-networkd, or manual
- DNS configured in /etc/resolv.conf or via NetworkManager
- Flush DNS cache: sudo systemd-resolve --flush-caches (systemd-resolved)
- Check service status: systemctl status NetworkManager
- View logs: journalctl -u NetworkManager
```

---

## Cross-Platform Tools

These tools work on all three operating systems but have platform-specific implementations internally. They follow the existing pattern established by the network diagnostic tools.

### Tool 1: cleanup_temp_files

This tool removes temporary files that accumulate over time and can cause disk space issues or application problems. The tool is conservative by default, targeting only safe-to-delete locations.

**Purpose**: Free disk space and remove potentially corrupted temporary data that may cause application issues.

**Platforms**: macOS, Windows, Linux

**Parameters**:
- `aggressive` (boolean, default: false): If true, includes additional cache locations
- `dry_run` (boolean, default: false): If true, reports what would be deleted without deleting

**Platform-Specific Locations**:

| Platform | Standard Locations | Aggressive Locations |
|----------|-------------------|---------------------|
| macOS | ~/Library/Caches/*, /tmp/*, /var/folders/*/*/T/* | ~/Library/Logs/*, ~/Library/Application Support/*/Cache/* |
| Windows | %TEMP%/*, %LOCALAPPDATA%\Temp\*, C:\Windows\Temp\* | %LOCALAPPDATA%\Microsoft\Windows\INetCache\*, Recycle Bin |
| Linux | /tmp/*, /var/tmp/*, ~/.cache/* | ~/.local/share/Trash/*, /var/log/*.gz |

**Safety Considerations**:
- Never delete files currently in use (check file handles)
- Skip files modified within the last hour
- Exclude known critical directories
- Log everything deleted for potential recovery reference

**Output**: DiagnosticResult containing:
- `files_deleted`: Number of files removed
- `space_freed_mb`: Megabytes of space recovered
- `errors`: List of files that could not be deleted
- `skipped`: Files skipped due to safety rules

---

### Tool 2: kill_process

This tool terminates processes that may be hung, consuming excessive resources, or interfering with system operation. It includes safeguards against killing critical system processes.

**Purpose**: Terminate problematic processes that are causing system issues.

**Platforms**: macOS, Windows, Linux

**Parameters**:
- `process_name` (string, optional): Name of process to kill (e.g., "chrome", "Teams")
- `process_id` (integer, optional): Specific PID to terminate
- `force` (boolean, default: false): Use forceful termination (SIGKILL/-9 on Unix, /F on Windows)
- `include_children` (boolean, default: true): Also terminate child processes

**Platform-Specific Implementation**:

| Platform | Graceful Kill | Forceful Kill | List Processes |
|----------|--------------|---------------|----------------|
| macOS | kill -TERM {pid} | kill -9 {pid} | ps aux \| grep {name} |
| Windows | Stop-Process -Id {pid} | Stop-Process -Id {pid} -Force | Get-Process -Name {name} |
| Linux | kill -TERM {pid} | kill -9 {pid} | ps aux \| grep {name} |

**Protected Processes** (never kill):
- macOS: kernel_task, launchd, WindowServer, loginwindow
- Windows: System, smss.exe, csrss.exe, wininit.exe, services.exe, lsass.exe
- Linux: init, systemd, kthreadd

**Output**: DiagnosticResult containing:
- `killed`: List of processes terminated with their PIDs
- `failed`: List of processes that could not be terminated
- `protected_blocked`: List of protected processes that were requested but blocked

---

### Tool 3: test_vpn_connectivity

This tool checks VPN connection status and tests connectivity through the VPN tunnel. It can detect common VPN configurations and verify the tunnel is passing traffic correctly.

**Purpose**: Diagnose VPN connection issues and verify tunnel functionality.

**Platforms**: macOS, Windows, Linux

**Parameters**:
- `vpn_type` (string, optional): Type of VPN (auto-detect if not specified). Values: "wireguard", "openvpn", "ipsec", "cisco", "globalprotect", "corporate"
- `test_endpoint` (string, optional): Internal endpoint to test through VPN (if known)

**Detection Methods**:

| Platform | Detection Approach |
|----------|-------------------|
| macOS | Check for utun* interfaces (WireGuard), ipsec* interfaces, scutil --nc list |
| Windows | Get-VpnConnection, rasdial, check for virtual adapters |
| Linux | Check for tun*, wg* interfaces, nmcli connection show --active |

**Tests Performed**:
1. VPN interface exists and is up
2. VPN interface has an IP address assigned
3. Routing table includes VPN routes
4. DNS is configured to use VPN DNS servers (if applicable)
5. Test connectivity to VPN gateway
6. Test connectivity to internal endpoint (if provided)
7. Check for DNS leaks (queries going outside VPN)

**Output**: DiagnosticResult containing:
- `vpn_connected`: Boolean indicating if VPN is active
- `vpn_type`: Detected or specified VPN type
- `vpn_interface`: Interface name (e.g., utun3, Ethernet 2)
- `vpn_ip`: IP address assigned by VPN
- `routes_active`: Boolean indicating if VPN routes are present
- `dns_via_vpn`: Boolean indicating if DNS goes through VPN
- `internal_reachable`: Boolean if test_endpoint was reachable (null if not tested)
- `suggestions`: List of suggestions if issues detected

---

## Windows-Specific Tools

These tools are only available on Windows and leverage PowerShell for deep system integration.

### Tool 4: fix_dell_audio

Dell computers frequently experience audio driver issues where the Realtek or Waves MaxxAudio driver becomes corrupted or conflicts with Windows updates. The standard fix is to completely remove the audio device from Device Manager and let Windows reinstall it on reboot.

**Purpose**: Fix Dell audio driver issues by removing and reinstalling the audio device driver.

**Platform**: Windows only

**Parameters**:
- `confirm_reboot` (boolean, default: false): If true, automatically initiate reboot after driver removal
- `backup_driver` (boolean, default: true): Export current driver before removal

**Implementation Steps**:
1. Identify Dell audio devices via `Get-PnpDevice -Class AudioEndpoint` and `Get-PnpDevice -Class MEDIA`
2. Check for Realtek, Waves MaxxAudio, or Dell Audio device names
3. Optionally export current driver: `pnputil /export-driver`
4. Remove device: `pnputil /remove-device` with device instance ID
5. Remove driver package if corrupted: `pnputil /delete-driver`
6. Prompt or initiate reboot for Windows to reinstall generic driver

**Safety Considerations**:
- Verify Dell hardware before proceeding (check BIOS manufacturer)
- Create driver backup before removal
- Warn user that audio will be unavailable until reboot
- Do not force reboot without explicit confirmation

**Output**: DiagnosticResult containing:
- `devices_found`: List of Dell audio devices detected
- `devices_removed`: List of devices successfully removed
- `driver_backed_up`: Boolean and path to backup if created
- `reboot_required`: Always true after successful removal
- `reboot_initiated`: Boolean if auto-reboot was triggered

---

### Tool 5: repair_office365

Microsoft 365 applications can become corrupted, leading to crashes, missing features, or activation issues. The repair tool runs either a Quick Repair (local, faster) or Online Repair (downloads fresh components, more thorough).

**Purpose**: Repair Microsoft 365 installation to fix application issues.

**Platform**: Windows only

**Parameters**:
- `repair_type` (string): Either "quick" (local repair) or "online" (cloud repair)
- `apps_to_repair` (list, optional): Specific apps to target, or all if not specified

**Implementation Steps**:
1. Detect Office installation via registry: `HKLM\SOFTWARE\Microsoft\Office\ClickToRun\Configuration`
2. Verify Office is Click-to-Run (not MSI-based; MSI uses different repair method)
3. For Quick Repair: Execute `OfficeClickToRun.exe scenario=Repair`
4. For Online Repair: Execute `OfficeClickToRun.exe scenario=Repair platform=x64 RepairType=2`
5. Monitor repair progress via event logs or process status
6. Report completion status

**Alternative for MSI Installation**:
If Office is MSI-based (Office 2016/2019 volume license), use:
- `msiexec /fa {ProductCode}` for repair

**Output**: DiagnosticResult containing:
- `office_version`: Detected Office version (e.g., "Microsoft 365 Apps for Enterprise")
- `installation_type`: "ClickToRun" or "MSI"
- `repair_type_used`: "quick" or "online"
- `repair_initiated`: Boolean
- `repair_completed`: Boolean (if waited for completion)
- `errors`: Any errors encountered

---

### Tool 6: run_dism_sfc

Windows system files can become corrupted due to failed updates, malware, or disk errors. The DISM (Deployment Image Servicing and Management) and SFC (System File Checker) tools repair the Windows component store and system files respectively.

**Purpose**: Repair Windows system file corruption using DISM and SFC.

**Platform**: Windows only

**Parameters**:
- `run_dism` (boolean, default: true): Run DISM /RestoreHealth first
- `run_sfc` (boolean, default: true): Run SFC /scannow after DISM
- `check_only` (boolean, default: false): Only scan for issues, don't repair

**Implementation Steps**:
1. Check for Administrator privileges (required for both tools)
2. If not admin, return error with instructions to run as Administrator
3. Run DISM first (repairs component store):
   - `DISM /Online /Cleanup-Image /CheckHealth` (quick check)
   - `DISM /Online /Cleanup-Image /ScanHealth` (thorough scan)
   - `DISM /Online /Cleanup-Image /RestoreHealth` (repair)
4. Run SFC after DISM completes:
   - `sfc /scannow`
5. Parse output logs for results:
   - DISM: `%WINDIR%\Logs\DISM\dism.log`
   - SFC: `%WINDIR%\Logs\CBS\CBS.log`

**Output**: DiagnosticResult containing:
- `dism_result`: "healthy", "repaired", "unrepairable", or "error"
- `dism_issues_found`: Number of issues detected
- `dism_issues_fixed`: Number of issues repaired
- `sfc_result`: "no_violations", "repaired", "unrepairable", or "error"
- `sfc_files_repaired`: List of files that were repaired
- `reboot_required`: Boolean if repairs require reboot
- `logs`: Paths to relevant log files

---

### Tool 7: review_system_logs

This tool analyzes Windows logs to identify the cause of crashes, blue screens, and system errors. It consolidates information from multiple sources into an actionable report.

**Purpose**: Analyze Windows system logs to diagnose crashes and errors.

**Platform**: Windows only

**Parameters**:
- `log_types` (list): Which logs to analyze. Options: "event_viewer", "crash_dumps", "bsod", "reliability"
- `time_range_hours` (integer, default: 72): How far back to search
- `severity_filter` (string, default: "error"): Minimum severity. Options: "info", "warning", "error", "critical"

**Log Sources and Analysis**:

**Event Viewer** (`event_viewer`):
- System log: `Get-WinEvent -LogName System -MaxEvents 100`
- Application log: `Get-WinEvent -LogName Application -MaxEvents 100`
- Filter by level: Error (2), Critical (1)
- Look for patterns: repeated errors, service failures, driver crashes

**Crash Dumps** (`crash_dumps`):
- Location: `%LOCALAPPDATA%\CrashDumps\`, `%WINDIR%\Minidump\`
- Parse with: `Get-WinEvent -FilterHashtable @{LogName='Application'; ID=1000,1001}`
- Extract faulting module, exception code, timestamp

**BSOD Analysis** (`bsod`):
- Check for minidump files in `C:\Windows\Minidump\`
- Parse BSOD error codes from Event Viewer (Event ID 1001, BugCheck)
- Common codes: DRIVER_IRQL_NOT_LESS_OR_EQUAL, PAGE_FAULT_IN_NONPAGED_AREA, etc.
- Map error codes to likely causes

**Reliability Monitor** (`reliability`):
- `Get-WinEvent -ProviderName 'Microsoft-Windows-Reliability-Analysis-Engine'`
- Shows application crashes, Windows failures, miscellaneous failures
- Calculates stability index

**Output**: DiagnosticResult containing:
- `analysis_period`: Time range analyzed
- `critical_events`: List of critical errors with timestamps and details
- `error_events`: List of error events with timestamps and details
- `crash_dumps_found`: Number and details of crash dumps
- `bsod_events`: List of blue screen events with error codes and likely causes
- `reliability_score`: Windows stability index (1-10)
- `top_issues`: Ranked list of most frequent/severe issues
- `recommendations`: Suggested actions based on findings

---

## Implementation Phases

The expansion should be implemented in phases to allow testing and validation at each step.

### Phase 1: Agent Infrastructure (Week 1-2)

**Objective**: Implement the Manager Agent and routing infrastructure without adding new tools.

**Tasks**:
1. Create the agent routing system in `backend/agents/`
2. Implement Manager Agent prompt and routing logic
3. Create OS-specific agent prompts (macOS, Windows, Linux)
4. Add `route_to_agent` tool for Manager to delegate
5. Modify CLI to use Manager Agent as entry point
6. Test routing logic with existing network diagnostic tools

**Deliverables**:
- `backend/agents/manager.py`: Manager Agent implementation
- `backend/agents/macos.py`: macOS Agent implementation
- `backend/agents/windows.py`: Windows Agent implementation
- `backend/agents/linux.py`: Linux Agent implementation
- `prompts/manager_agent.md`: Manager Agent prompt
- `prompts/macos_agent.md`: macOS Agent prompt
- `prompts/windows_agent.md`: Windows Agent prompt
- `prompts/linux_agent.md`: Linux Agent prompt

### Phase 2: Cross-Platform Tools (Week 3-4)

**Objective**: Implement the three cross-platform tools.

**Tasks**:
1. Implement `cleanup_temp_files` with platform-specific paths
2. Implement `kill_process` with protected process lists
3. Implement `test_vpn_connectivity` with VPN detection
4. Add tools to appropriate OS agent tool registries
5. Write unit tests for each tool on each platform
6. Integration testing with agent routing

**Deliverables**:
- `backend/diagnostics/temp_files.py`: Temp file cleanup tool
- `backend/diagnostics/process_mgmt.py`: Process management tool
- `backend/diagnostics/vpn.py`: VPN connectivity tool
- Test files for each tool

### Phase 3: Windows-Specific Tools (Week 5-7)

**Objective**: Implement Windows-only advanced troubleshooting tools.

**Tasks**:
1. Implement `fix_dell_audio` with driver management
2. Implement `repair_office365` with Click-to-Run detection
3. Implement `run_dism_sfc` with admin privilege checking
4. Implement `review_system_logs` with log parsing
5. Register tools only on Windows Agent
6. Test on various Windows versions (10, 11)
7. Test with various Dell models for audio fix

**Deliverables**:
- `backend/diagnostics/windows/dell_audio.py`: Dell audio fix tool
- `backend/diagnostics/windows/office_repair.py`: Office 365 repair tool
- `backend/diagnostics/windows/system_repair.py`: DISM/SFC tool
- `backend/diagnostics/windows/log_analysis.py`: Log review tool
- Windows-specific test suite

### Phase 4: Integration and Polish (Week 8)

**Objective**: Full integration testing and user experience improvements.

**Tasks**:
1. End-to-end testing of all agent flows
2. Prompt tuning based on test results
3. Add progress indicators for long-running tools
4. Implement tool result caching where appropriate
5. Documentation updates
6. Performance optimization

**Deliverables**:
- Updated documentation
- Performance benchmarks
- Release candidate

---

## File Structure

The expanded project structure organizes agents and tools by platform.

```
network-diagnostics/
├── backend/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py              # Base agent class
│   │   ├── manager.py           # Manager Agent (routes to OS agents)
│   │   ├── macos.py             # macOS Agent
│   │   ├── windows.py           # Windows Agent
│   │   └── linux.py             # Linux Agent
│   │
│   ├── diagnostics/
│   │   ├── __init__.py          # Registration (existing + new)
│   │   ├── base.py              # BaseDiagnostic (existing)
│   │   ├── platform.py          # Platform detection (existing)
│   │   │
│   │   │── # Existing network tools
│   │   ├── adapter.py
│   │   ├── connectivity.py
│   │   ├── dns.py
│   │   ├── ip_config.py
│   │   ├── wifi.py
│   │   │
│   │   │── # New cross-platform tools
│   │   ├── temp_files.py        # cleanup_temp_files
│   │   ├── process_mgmt.py      # kill_process
│   │   ├── vpn.py               # test_vpn_connectivity
│   │   │
│   │   │── # Windows-specific tools
│   │   └── windows/
│   │       ├── __init__.py
│   │       ├── dell_audio.py    # fix_dell_audio
│   │       ├── office_repair.py # repair_office365
│   │       ├── system_repair.py # run_dism_sfc
│   │       └── log_analysis.py  # review_system_logs
│   │
│   ├── llm/                     # Existing LLM infrastructure
│   ├── tools/                   # Existing tool registry
│   └── cli.py                   # Updated to use Manager Agent
│
├── prompts/
│   ├── manager_agent.md         # Manager Agent prompt
│   ├── macos_agent.md           # macOS Agent prompt
│   ├── windows_agent.md         # Windows Agent prompt
│   ├── linux_agent.md           # Linux Agent prompt
│   └── # Existing prompts (can be retired or kept as fallback)
│
└── tests/
    ├── test_agents/
    │   ├── test_manager.py
    │   ├── test_routing.py
    │   └── test_os_agents.py
    │
    └── test_diagnostics/
        ├── test_temp_files.py
        ├── test_process_mgmt.py
        ├── test_vpn.py
        └── test_windows/
            ├── test_dell_audio.py
            ├── test_office_repair.py
            ├── test_system_repair.py
            └── test_log_analysis.py
```

---

## Detailed Tool Specifications

This section provides implementation-ready specifications for each new tool.

### cleanup_temp_files Specification

```python
"""Temporary file cleanup diagnostic.

Removes temporary files from standard cache and temp locations.
"""

from typing import Any
from pathlib import Path
import shutil
import os
import time

from .base import BaseDiagnostic, DiagnosticResult
from .platform import Platform


class CleanupTempFiles(BaseDiagnostic):
    """Clean up temporary files to free disk space."""

    name = "cleanup_temp_files"
    description = "Remove temporary files to free disk space"
    osi_layer = "Application"

    # Files modified within this many seconds are skipped
    MIN_AGE_SECONDS = 3600  # 1 hour

    # Platform-specific paths
    PATHS = {
        Platform.MACOS: {
            "standard": [
                "~/Library/Caches",
                "/tmp",
                "/var/folders/*/*/T",
            ],
            "aggressive": [
                "~/Library/Logs",
                "~/.Trash",
            ],
        },
        Platform.WINDOWS: {
            "standard": [
                "%TEMP%",
                "%LOCALAPPDATA%\\Temp",
                "C:\\Windows\\Temp",
            ],
            "aggressive": [
                "%LOCALAPPDATA%\\Microsoft\\Windows\\INetCache",
                "C:\\$Recycle.Bin",
            ],
        },
        Platform.LINUX: {
            "standard": [
                "/tmp",
                "/var/tmp",
                "~/.cache",
            ],
            "aggressive": [
                "~/.local/share/Trash",
            ],
        },
    }

    async def run(
        self,
        aggressive: bool = False,
        dry_run: bool = False,
    ) -> DiagnosticResult:
        """
        Clean up temporary files.

        Args:
            aggressive: Include additional cache locations
            dry_run: Report what would be deleted without deleting

        Returns:
            DiagnosticResult with cleanup statistics
        """
        paths = self._get_paths(aggressive)
        
        files_deleted = 0
        space_freed = 0
        errors = []
        skipped = []

        for path_pattern in paths:
            expanded = self._expand_path(path_pattern)
            
            for path in expanded:
                if not path.exists():
                    continue
                
                result = await self._clean_directory(
                    path, dry_run, errors, skipped
                )
                files_deleted += result["files"]
                space_freed += result["bytes"]

        return self._success(
            data={
                "files_deleted": files_deleted,
                "space_freed_mb": round(space_freed / (1024 * 1024), 2),
                "errors": errors[:10],  # Limit error list
                "skipped_count": len(skipped),
                "dry_run": dry_run,
                "mode": "aggressive" if aggressive else "standard",
            },
            suggestions=self._generate_suggestions(space_freed, errors),
        )

    def _get_paths(self, aggressive: bool) -> list[str]:
        """Get list of paths to clean for current platform."""
        platform_paths = self.PATHS.get(self.platform, self.PATHS[Platform.LINUX])
        paths = platform_paths["standard"].copy()
        if aggressive:
            paths.extend(platform_paths["aggressive"])
        return paths

    def _expand_path(self, path_pattern: str) -> list[Path]:
        """Expand environment variables and globs in path."""
        # Expand ~ and environment variables
        expanded = os.path.expanduser(os.path.expandvars(path_pattern))
        
        # Handle glob patterns
        if "*" in expanded:
            from glob import glob
            return [Path(p) for p in glob(expanded)]
        
        return [Path(expanded)]

    async def _clean_directory(
        self,
        directory: Path,
        dry_run: bool,
        errors: list,
        skipped: list,
    ) -> dict[str, int]:
        """Clean a single directory, returning stats."""
        files_deleted = 0
        bytes_freed = 0
        
        try:
            for item in directory.rglob("*"):
                if item.is_file():
                    # Skip recently modified files
                    try:
                        mtime = item.stat().st_mtime
                        if time.time() - mtime < self.MIN_AGE_SECONDS:
                            skipped.append(str(item))
                            continue
                        
                        size = item.stat().st_size
                        
                        if not dry_run:
                            item.unlink()
                        
                        files_deleted += 1
                        bytes_freed += size
                        
                    except PermissionError:
                        errors.append(f"Permission denied: {item}")
                    except Exception as e:
                        errors.append(f"{item}: {e}")
                        
        except PermissionError:
            errors.append(f"Cannot access directory: {directory}")
        
        return {"files": files_deleted, "bytes": bytes_freed}

    def _generate_suggestions(
        self, space_freed: int, errors: list
    ) -> list[str] | None:
        """Generate suggestions based on results."""
        suggestions = []
        
        if space_freed > 500 * 1024 * 1024:  # > 500MB
            suggestions.append(
                "Significant space recovered. Consider running cleanup regularly."
            )
        
        if errors:
            suggestions.append(
                f"Some files could not be deleted ({len(errors)} errors). "
                "Run as administrator for full cleanup."
            )
        
        return suggestions if suggestions else None


async def cleanup_temp_files(
    aggressive: bool = False,
    dry_run: bool = False,
) -> DiagnosticResult:
    """Clean up temporary files."""
    diag = CleanupTempFiles()
    return await diag.run(aggressive=aggressive, dry_run=dry_run)
```

### kill_process Specification

```python
"""Process management diagnostic.

Terminates problematic processes with safety guards.
"""

from typing import Any
import asyncio

from .base import BaseDiagnostic, DiagnosticResult
from .platform import Platform


class KillProcess(BaseDiagnostic):
    """Terminate problematic processes."""

    name = "kill_process"
    description = "Terminate hung or problematic processes"
    osi_layer = "Application"

    # Processes that should never be killed
    PROTECTED = {
        Platform.MACOS: {
            "kernel_task", "launchd", "WindowServer", "loginwindow",
            "opendirectoryd", "securityd", "diskarbitrationd",
        },
        Platform.WINDOWS: {
            "System", "smss.exe", "csrss.exe", "wininit.exe",
            "services.exe", "lsass.exe", "svchost.exe", "winlogon.exe",
            "dwm.exe", "explorer.exe",  # explorer can be killed but usually shouldn't
        },
        Platform.LINUX: {
            "init", "systemd", "kthreadd", "dbus-daemon",
            "NetworkManager", "gdm", "sddm", "lightdm",
        },
    }

    async def run(
        self,
        process_name: str | None = None,
        process_id: int | None = None,
        force: bool = False,
        include_children: bool = True,
    ) -> DiagnosticResult:
        """
        Kill a process by name or PID.

        Args:
            process_name: Name of process to kill (e.g., "chrome")
            process_id: Specific PID to terminate
            force: Use forceful termination (SIGKILL/-9)
            include_children: Also kill child processes

        Returns:
            DiagnosticResult with termination results
        """
        if not process_name and not process_id:
            return self._failure(
                error="Must specify either process_name or process_id",
                suggestions=["Provide a process name like 'chrome' or a PID"],
            )

        # Find matching processes
        processes = await self._find_processes(process_name, process_id)
        
        if not processes:
            return self._failure(
                error=f"No matching processes found",
                data={"search_name": process_name, "search_pid": process_id},
                suggestions=["Check the process name spelling", "Use 'ps aux' or Task Manager to find the correct name"],
            )

        # Filter out protected processes
        protected = self.PROTECTED.get(self.platform, set())
        killable = []
        blocked = []
        
        for proc in processes:
            if proc["name"].lower() in {p.lower() for p in protected}:
                blocked.append(proc)
            else:
                killable.append(proc)

        # Kill the processes
        killed = []
        failed = []
        
        for proc in killable:
            success = await self._kill_process(
                proc["pid"], force, include_children
            )
            if success:
                killed.append(proc)
            else:
                failed.append(proc)

        return self._success(
            data={
                "killed": killed,
                "failed": failed,
                "protected_blocked": blocked,
                "force_used": force,
            },
            suggestions=self._generate_suggestions(killed, failed, blocked),
        )

    async def _find_processes(
        self,
        name: str | None,
        pid: int | None,
    ) -> list[dict[str, Any]]:
        """Find processes matching criteria."""
        if self.platform == Platform.WINDOWS:
            return await self._find_windows(name, pid)
        else:
            return await self._find_unix(name, pid)

    async def _find_unix(
        self,
        name: str | None,
        pid: int | None,
    ) -> list[dict[str, Any]]:
        """Find processes on Unix systems."""
        if pid:
            cmd = f"ps -p {pid} -o pid,comm"
        else:
            cmd = f"ps aux | grep -i '{name}' | grep -v grep"
        
        result = await self.executor.run(cmd, shell=True)
        processes = []
        
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    processes.append({
                        "pid": int(parts[0]) if parts[0].isdigit() else int(parts[1]),
                        "name": parts[-1].split("/")[-1],
                    })
                except (ValueError, IndexError):
                    continue
        
        return processes

    async def _find_windows(
        self,
        name: str | None,
        pid: int | None,
    ) -> list[dict[str, Any]]:
        """Find processes on Windows."""
        if pid:
            cmd = f"Get-Process -Id {pid} | Select-Object Id, ProcessName | ConvertTo-Json"
        else:
            cmd = f"Get-Process -Name '*{name}*' | Select-Object Id, ProcessName | ConvertTo-Json"
        
        result = await self.executor.run(cmd, shell=True)
        
        try:
            import json
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]
            return [{"pid": p["Id"], "name": p["ProcessName"]} for p in data]
        except (json.JSONDecodeError, KeyError):
            return []

    async def _kill_process(
        self,
        pid: int,
        force: bool,
        include_children: bool,
    ) -> bool:
        """Terminate a single process."""
        if self.platform == Platform.WINDOWS:
            force_flag = "-Force" if force else ""
            cmd = f"Stop-Process -Id {pid} {force_flag}"
        else:
            signal = "-9" if force else "-TERM"
            cmd = f"kill {signal} {pid}"
        
        result = await self.executor.run(cmd, shell=True)
        return result.success

    def _generate_suggestions(
        self,
        killed: list,
        failed: list,
        blocked: list,
    ) -> list[str] | None:
        """Generate suggestions based on results."""
        suggestions = []
        
        if blocked:
            suggestions.append(
                f"Blocked {len(blocked)} protected system processes for safety"
            )
        
        if failed:
            suggestions.append(
                "Some processes could not be killed. Try with force=True or run as administrator."
            )
        
        if killed:
            suggestions.append(
                f"Successfully terminated {len(killed)} process(es)"
            )
        
        return suggestions if suggestions else None


async def kill_process(
    process_name: str | None = None,
    process_id: int | None = None,
    force: bool = False,
    include_children: bool = True,
) -> DiagnosticResult:
    """Kill a process by name or PID."""
    diag = KillProcess()
    return await diag.run(
        process_name=process_name,
        process_id=process_id,
        force=force,
        include_children=include_children,
    )
```

---

## Future: Vision Model Integration

The future phase introduces vision model capabilities for GUI-based troubleshooting that cannot be automated through command-line tools alone. This is particularly relevant for Office 365 delegation setup, which requires navigating through the Outlook GUI.

### Architecture for Vision Integration

```
User Request: "Help me add a delegate to my Outlook"
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                      MANAGER AGENT                          │
│  Detects: GUI-based task, requires vision                   │
│  Routes to: Vision-Guided Agent                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   VISION-GUIDED AGENT                       │
│                                                             │
│  1. Capture screenshot                                      │
│  2. Send to vision model for analysis                       │
│  3. Generate instruction for user OR                        │
│  4. Execute mouse click at coordinates (with confirmation)  │
└─────────────────────────────────────────────────────────────┘
```

### Vision Tools (Future Implementation)

**capture_screenshot**: Capture the current screen or a specific window.

**analyze_screen**: Send screenshot to vision model with a prompt, receive structured analysis of UI elements.

**guide_user**: Display step-by-step instructions with highlighted regions of the screen.

**execute_click**: Move mouse to coordinates and click (requires explicit user confirmation).

### Office 365 Delegate Workflow Example

This workflow demonstrates how vision integration would handle the Outlook delegate scenario:

1. User says: "Help me add a delegate in Outlook"
2. Vision agent captures Outlook window
3. Vision model identifies current state (Outlook open? Which view?)
4. Agent provides instruction: "Click on File in the top left corner"
5. User clicks (or agent clicks with permission)
6. Agent captures new screenshot, identifies File menu
7. Agent provides instruction: "Click on Account Settings, then Delegate Access"
8. Process continues until delegate dialog is open
9. Agent guides user through adding the delegate email and permissions

This approach balances automation with user control, ensuring the user understands and approves each action.

---

## Summary

This plan transforms the Network Diagnostics CLI from a focused network troubleshooting tool into a comprehensive system diagnostic platform. The key architectural changes are the introduction of a Manager Agent for OS-aware routing, OS-specific agents with specialized knowledge and tool access, and a modular tool structure that cleanly separates cross-platform and OS-specific capabilities.

The implementation is phased to allow incremental testing and validation. Phase 1 establishes the agent infrastructure, Phase 2 adds cross-platform tools, Phase 3 adds Windows-specific advanced tools, and Phase 4 focuses on integration and polish. The future vision integration phase is deliberately scoped separately to allow the core platform to stabilize first.

Each tool specification includes platform-specific implementation details, safety considerations, and expected output formats. The specifications follow the existing patterns established by the network diagnostic tools, ensuring consistency across the codebase.

The end result is a system that can handle requests ranging from simple network diagnostics to complex Windows driver troubleshooting, with intelligent routing ensuring the user always interacts with the most appropriate specialist agent for their problem.
