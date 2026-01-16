#!/usr/bin/env python3
"""Validate that frontend fallbackTools matches backend tool registry.

This script compares the tools registered in the backend diagnostics
with the fallback tools defined in the frontend chat page.
"""

import re
import sys
from pathlib import Path


def get_backend_tools() -> set[str]:
    """Extract tool names from backend __init__.py registrations."""
    init_path = Path(__file__).parent.parent / "backend" / "diagnostics" / "__init__.py"
    
    if not init_path.exists():
        print(f"Warning: Backend file not found: {init_path}")
        return set()
    
    content = init_path.read_text()
    # Match registry.register(name="tool_name", ...)
    return set(re.findall(r'registry\.register\(\s*name="(\w+)"', content))


def get_frontend_tools() -> set[str]:
    """Extract tool names from frontend fallbackTools."""
    page_path = Path(__file__).parent.parent / "frontend" / "techtime" / "app" / "chat" / "page.tsx"
    
    if not page_path.exists():
        print(f"Warning: Frontend file not found: {page_path}")
        return set()
    
    content = page_path.read_text()
    
    # Find the fallbackTools array and extract only top-level tool names
    # Tool names are followed by displayName on the next property
    # This distinguishes them from parameter names
    tools = set()
    
    # Match pattern: name: 'tool_name', followed by displayName on next line
    pattern = r"^\s*name:\s*['\"](\w+)['\"],?\s*$\s*displayName:"
    matches = re.findall(pattern, content, re.MULTILINE)
    
    if matches:
        tools.update(matches)
    else:
        # Fallback: Look for tool names that look like snake_case diagnostic tools
        # These are the actual tool names (check_adapter_status, get_ip_config, etc.)
        all_names = re.findall(r"name:\s*['\"](\w+)['\"]", content)
        # Filter to only snake_case names that contain underscore (tool convention)
        tools = {n for n in all_names if "_" in n and n.islower()}
    
    return tools


def get_script_tools() -> dict[str, set[str]]:
    """Get tools available as shell scripts per platform."""
    base_path = Path(__file__).parent.parent / "backend" / "diagnostics"
    
    result = {}
    for platform in ["macos", "linux", "windows_scripts"]:
        platform_path = base_path / platform
        if platform_path.exists():
            scripts = set()
            for ext in [".sh", ".ps1"]:
                for script in platform_path.glob(f"*{ext}"):
                    if script.name != f"common{ext}":
                        scripts.add(script.stem)
            result[platform] = scripts
    
    return result


def main():
    """Run validation and report results."""
    backend = get_backend_tools()
    frontend = get_frontend_tools()
    scripts = get_script_tools()
    
    print("=" * 60)
    print("Tool Sync Validation Report")
    print("=" * 60)
    
    # Script inventory
    print("\n📦 Shell Scripts Inventory:")
    for platform, tools in sorted(scripts.items()):
        print(f"   {platform}: {len(tools)} scripts")
    
    # Check all scripts are present on all platforms (except Windows-only)
    all_scripts = set()
    for tools in scripts.values():
        all_scripts |= tools
    
    windows_only = {"fix_dell_audio", "repair_office365", "run_dism_sfc", "review_system_logs", "robocopy"}
    cross_platform = all_scripts - windows_only
    
    print(f"\n   Cross-platform scripts: {len(cross_platform)}")
    print(f"   Windows-only scripts: {len(windows_only)}")
    
    # Frontend vs Scripts comparison
    print("\n📋 Frontend vs Scripts:")
    print(f"   Frontend fallbackTools: {len(frontend)} tools")
    print(f"   Available scripts: {len(all_scripts)} scripts")
    
    missing_in_frontend = all_scripts - frontend
    extra_in_frontend = frontend - all_scripts
    
    issues = False
    
    if missing_in_frontend:
        print(f"\n❌ Scripts missing from frontend ({len(missing_in_frontend)}):")
        for tool in sorted(missing_in_frontend):
            print(f"   - {tool}")
        issues = True
    
    if extra_in_frontend:
        print(f"\n⚠️  Frontend tools without scripts ({len(extra_in_frontend)}):")
        for tool in sorted(extra_in_frontend):
            print(f"   - {tool}")
        issues = True
    
    # Backend comparison (if backend tools exist)
    if backend:
        print(f"\n📋 Backend Registry: {len(backend)} tools")
        
        missing_scripts = backend - all_scripts
        if missing_scripts:
            print(f"\n⚠️  Backend tools without scripts ({len(missing_scripts)}):")
            for tool in sorted(missing_scripts):
                print(f"   - {tool}")
    
    # Summary
    print("\n" + "=" * 60)
    if not issues:
        print(f"✅ All {len(frontend)} frontend tools have corresponding scripts!")
        return 0
    else:
        print(f"❌ Found sync issues - review the report above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
