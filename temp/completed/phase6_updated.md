# Phase 6: Distribution (UPDATED)

## CHANGES FROM ORIGINAL

This document has been significantly restructured to remove duplication with Phase 4 and focus only on distribution-specific tasks.

| Change | Original | Updated | Reason |
|--------|----------|---------|--------|
| Tasks 6.1-6.4 | Full build scripts | Removed | Already in Phase 4 |
| Task numbering | 6.1-6.7 | 6.1-6.4 | Fewer tasks after removing duplicates |
| Prerequisites | Phases 1-5 | Phases 1-5 + Phase 4 build | Build must complete first |
| Focus | Build + Distribution | Distribution only | Separation of concerns |

### Removed Duplicate Content

The following were removed as they duplicate Phase 4:
- `scripts/download_ollama.py` (Phase 4 Task 4.2)
- `scripts/build_frontend.py` (Phase 4 Task 4.3)
- `scripts/build_app.py` (Phase 4 Task 4.5)
- `techtim.spec` (Phase 4 Task 4.4)

---

## Objective

Create distribution packages for macOS and Windows that can be shared with end users. This phase covers code signing, notarization, and installer creation.

**Note:** The build process (downloading Ollama, building frontend, running PyInstaller) is covered in **Phase 4**. This phase assumes a successful build already exists in `dist/`.

## Prerequisites

Before starting this phase, ensure you have:
- **Phases 1-5 completed**
- **Phase 4 build completed**: `dist/TechTime/` (or `dist/TechTime.app` on macOS) exists
- PyInstaller installed: `pip install pyinstaller`
- For macOS: Xcode command line tools (`xcode-select --install`)
- For Windows: Visual Studio Build Tools (for some Python packages)

### Verify Build Exists

Before proceeding, verify the build from Phase 4:

```bash
# Check build output exists
ls -la dist/

# On macOS, should see:
# - TechTime.app/
# - TechTime/

# On Windows, should see:
# - TechTime/
#   - TechTime.exe
```

If the build doesn't exist, run:
```bash
python scripts/build_app.py
```

---

## Task 6.1: Create macOS Distribution Script

### Purpose

Handle macOS-specific distribution tasks: code signing, notarization, and DMG creation.

### File: `scripts/distribute_macos.py`

```python
#!/usr/bin/env python3
"""
macOS distribution script for TechTim(e).

This script handles:
1. Code signing the application bundle
2. Notarizing with Apple (required for distribution)
3. Creating a DMG installer

Prerequisites:
- Apple Developer account ($99/year)
- Developer ID Application certificate installed
- App-specific password for notarization

Usage:
    python scripts/distribute_macos.py --sign
    python scripts/distribute_macos.py --notarize
    python scripts/distribute_macos.py --dmg
    python scripts/distribute_macos.py --all
"""
import subprocess
import sys
import os
import time
import json
from pathlib import Path


# =============================================================================
# Configuration - Update these for your account
# =============================================================================

SIGNING_IDENTITY = "Developer ID Application: Your Name (TEAMID)"
APPLE_ID = "your@email.com"
TEAM_ID = "YOUR_TEAM_ID"
APP_BUNDLE_ID = "com.techtim.desktop"


# =============================================================================
# Helper Functions
# =============================================================================

def run_command(command: list, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and optionally check for errors."""
    print(f"Running: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    
    if check and result.returncode != 0:
        print(f"ERROR: Command failed with code {result.returncode}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        sys.exit(1)
    
    return result


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


# =============================================================================
# Code Signing
# =============================================================================

def sign_app(app_path: Path) -> bool:
    """
    Code sign the application bundle.
    
    Args:
        app_path: Path to the .app bundle
    
    Returns:
        True if signing succeeded
    """
    print(f"\n{'='*60}")
    print(f"Signing: {app_path}")
    print('='*60)
    
    # Sign with hardened runtime (required for notarization)
    command = [
        'codesign',
        '--deep',
        '--force',
        '--verify',
        '--verbose',
        '--timestamp',
        '--options', 'runtime',
        '--sign', SIGNING_IDENTITY,
        str(app_path),
    ]
    
    result = run_command(command, check=False)
    
    if result.returncode != 0:
        print("ERROR: Code signing failed")
        print("Make sure you have a valid Developer ID certificate installed")
        print(f"Looking for: {SIGNING_IDENTITY}")
        return False
    
    # Verify signature
    print("\nVerifying signature...")
    verify_command = [
        'codesign',
        '--verify',
        '--verbose=4',
        str(app_path),
    ]
    
    verify_result = run_command(verify_command, check=False)
    
    if verify_result.returncode == 0:
        print("Signature verified successfully")
        return True
    else:
        print("WARNING: Signature verification failed")
        return False


# =============================================================================
# Notarization
# =============================================================================

def notarize_app(app_path: Path) -> bool:
    """
    Submit the app for Apple notarization.
    
    This requires an app-specific password stored in the keychain.
    Create one at appleid.apple.com and add it with:
        xcrun notarytool store-credentials "techtim-notarize" \\
            --apple-id "your@email.com" \\
            --team-id "TEAMID" \\
            --password "app-specific-password"
    
    Args:
        app_path: Path to the signed .app bundle
    
    Returns:
        True if notarization succeeded
    """
    print(f"\n{'='*60}")
    print(f"Notarizing: {app_path}")
    print('='*60)
    
    # Create a ZIP for notarization
    zip_path = app_path.parent / f"{app_path.stem}.zip"
    
    print(f"\nCreating ZIP: {zip_path}")
    run_command([
        'ditto',
        '-c', '-k', '--keepParent',
        str(app_path),
        str(zip_path),
    ])
    
    # Submit for notarization
    print("\nSubmitting for notarization (this may take several minutes)...")
    
    submit_command = [
        'xcrun', 'notarytool', 'submit',
        str(zip_path),
        '--keychain-profile', 'techtim-notarize',
        '--wait',
    ]
    
    result = run_command(submit_command, check=False)
    
    # Clean up ZIP
    zip_path.unlink()
    
    if result.returncode != 0:
        print("ERROR: Notarization failed")
        print("Make sure you have stored credentials with:")
        print('  xcrun notarytool store-credentials "techtim-notarize"')
        return False
    
    # Staple the notarization ticket
    print("\nStapling notarization ticket...")
    staple_result = run_command([
        'xcrun', 'stapler', 'staple',
        str(app_path),
    ], check=False)
    
    if staple_result.returncode == 0:
        print("Notarization complete and stapled")
        return True
    else:
        print("WARNING: Stapling failed (notarization may still be valid)")
        return False


# =============================================================================
# DMG Creation
# =============================================================================

def create_dmg(app_path: Path, output_path: Path = None) -> Path:
    """
    Create a DMG installer.
    
    Args:
        app_path: Path to the .app bundle
        output_path: Output DMG path (optional)
    
    Returns:
        Path to the created DMG
    """
    if output_path is None:
        output_path = app_path.parent / f"{app_path.stem}.dmg"
    
    # Remove existing DMG
    if output_path.exists():
        output_path.unlink()
    
    print(f"\n{'='*60}")
    print(f"Creating DMG: {output_path}")
    print('='*60)
    
    # Create DMG
    run_command([
        'hdiutil', 'create',
        '-volname', 'TechTime',
        '-srcfolder', str(app_path),
        '-ov',
        '-format', 'UDZO',
        str(output_path),
    ])
    
    print(f"\nDMG created: {output_path}")
    
    # Get size
    size = output_path.stat().st_size / (1024 * 1024)
    print(f"Size: {size:.1f} MB")
    
    return output_path


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Distribute TechTim(e) for macOS'
    )
    parser.add_argument('--sign', action='store_true', help='Code sign the app')
    parser.add_argument('--notarize', action='store_true', help='Notarize the app')
    parser.add_argument('--dmg', action='store_true', help='Create DMG installer')
    parser.add_argument('--all', action='store_true', help='Do all steps')
    parser.add_argument(
        '--app-path',
        type=Path,
        default=None,
        help='Path to .app bundle'
    )
    
    args = parser.parse_args()
    
    # Check we're on macOS
    if sys.platform != 'darwin':
        print("ERROR: This script is for macOS only")
        sys.exit(1)
    
    # Find app bundle
    if args.app_path:
        app_path = args.app_path
    else:
        project_root = get_project_root()
        app_path = project_root / 'dist' / 'TechTime.app'
    
    if not app_path.exists():
        print(f"ERROR: App bundle not found: {app_path}")
        print("\nRun Phase 4 build first:")
        print("  python scripts/build_app.py")
        sys.exit(1)
    
    print(f"App bundle: {app_path}")
    
    # Determine what to do
    do_sign = args.sign or args.all
    do_notarize = args.notarize or args.all
    do_dmg = args.dmg or args.all
    
    if not any([do_sign, do_notarize, do_dmg]):
        print("No action specified. Use --sign, --notarize, --dmg, or --all")
        sys.exit(1)
    
    # Execute steps
    if do_sign:
        if not sign_app(app_path):
            sys.exit(1)
    
    if do_notarize:
        if not notarize_app(app_path):
            sys.exit(1)
    
    if do_dmg:
        create_dmg(app_path)
    
    print(f"\n{'='*60}")
    print("Done!")
    print('='*60)


if __name__ == '__main__':
    main()
```

---

## Task 6.2: Create Windows Distribution Script

### Purpose

Create a Windows installer using Inno Setup.

### File: `scripts/distribute_windows.py`

```python
#!/usr/bin/env python3
"""
Windows distribution script for TechTim(e).

This script creates a Windows installer using Inno Setup.

Prerequisites:
- Inno Setup installed (https://jrsoftware.org/isinfo.php)
- ISCC.exe in PATH or specify with --iscc

Usage:
    python scripts/distribute_windows.py
    python scripts/distribute_windows.py --iscc "C:\\Program Files\\Inno Setup 6\\ISCC.exe"
"""
import subprocess
import sys
import shutil
from pathlib import Path


# =============================================================================
# Helper Functions
# =============================================================================

def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


def find_iscc() -> Path:
    """Find the Inno Setup compiler."""
    # Check PATH
    iscc = shutil.which('ISCC')
    if iscc:
        return Path(iscc)
    
    # Check common locations
    common_paths = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]
    
    for path in common_paths:
        if path.exists():
            return path
    
    return None


# =============================================================================
# Inno Setup Script Generation
# =============================================================================

def create_inno_script(project_root: Path, output_path: Path) -> Path:
    """
    Create an Inno Setup script.
    
    Args:
        project_root: Project root directory
        output_path: Where to write the .iss file
    
    Returns:
        Path to the created script
    """
    app_dir = project_root / 'dist' / 'TechTime'
    
    # Escape backslashes for Inno Setup
    app_dir_str = str(app_dir).replace('\\', '\\\\')
    dist_dir_str = str(project_root / 'dist').replace('\\', '\\\\')
    
    script_content = f'''
; TechTim(e) Inno Setup Script
; Generated by distribute_windows.py

#define MyAppName "TechTime"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "TechTim(e)"
#define MyAppURL "https://github.com/yourusername/techtim"
#define MyAppExeName "TechTime.exe"

[Setup]
AppId={{{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}}}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
AppPublisherURL={{#MyAppURL}}
AppSupportURL={{#MyAppURL}}
AppUpdatesURL={{#MyAppURL}}
DefaultDirName={{autopf}}\\{{#MyAppName}}
DefaultGroupName={{#MyAppName}}
AllowNoIcons=yes
OutputDir={dist_dir_str}
OutputBaseFilename=TechTime-Setup-{{#MyAppVersion}}
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked

[Files]
Source: "{app_dir_str}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"
Name: "{{group}}\\{{cm:UninstallProgram,{{#MyAppName}}}}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "{{cm:LaunchProgram,{{#StringChange(MyAppName, '&', '&&')}}}}"; Flags: nowait postinstall skipifsilent
'''
    
    output_path.write_text(script_content)
    print(f"Created Inno Setup script: {output_path}")
    
    return output_path


# =============================================================================
# Installer Building
# =============================================================================

def build_installer(iscc_path: Path, script_path: Path) -> bool:
    """
    Build the installer using Inno Setup.
    
    Args:
        iscc_path: Path to ISCC.exe
        script_path: Path to .iss script
    
    Returns:
        True if build succeeded
    """
    print(f"\n{'='*60}")
    print(f"Building installer")
    print('='*60)
    print(f"Compiler: {iscc_path}")
    print(f"Script: {script_path}")
    
    result = subprocess.run(
        [str(iscc_path), str(script_path)],
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"\nERROR: Installer build failed")
        print(result.stdout)
        print(result.stderr)
        return False
    
    print("\nInstaller built successfully!")
    return True


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Create Windows installer for TechTim(e)'
    )
    parser.add_argument(
        '--iscc',
        type=Path,
        default=None,
        help='Path to ISCC.exe'
    )
    parser.add_argument(
        '--skip-build',
        action='store_true',
        help='Only generate .iss script, do not build'
    )
    
    args = parser.parse_args()
    
    # Check we're on Windows (or allow generating script on other platforms)
    if sys.platform != 'win32' and not args.skip_build:
        print("WARNING: Not on Windows, will only generate .iss script")
        args.skip_build = True
    
    # Get project root
    project_root = get_project_root()
    
    # Check app directory exists
    app_dir = project_root / 'dist' / 'TechTime'
    if not app_dir.exists():
        print(f"ERROR: App directory not found: {app_dir}")
        print("\nRun Phase 4 build first:")
        print("  python scripts/build_app.py")
        sys.exit(1)
    
    # Create script
    script_path = project_root / 'techtim.iss'
    create_inno_script(project_root, script_path)
    
    if args.skip_build:
        print(f"\nInno Setup script created: {script_path}")
        print("Build manually with: ISCC.exe techtim.iss")
        return
    
    # Find Inno Setup
    iscc_path = args.iscc or find_iscc()
    
    if not iscc_path or not iscc_path.exists():
        print("ERROR: Inno Setup not found")
        print("Install from: https://jrsoftware.org/isinfo.php")
        print("Or specify path with --iscc")
        sys.exit(1)
    
    # Build installer
    if not build_installer(iscc_path, script_path):
        sys.exit(1)
    
    # Show result
    installer_path = project_root / 'dist' / 'TechTime-Setup-1.0.0.exe'
    if installer_path.exists():
        size = installer_path.stat().st_size / (1024 * 1024)
        print(f"\n{'='*60}")
        print("Distribution Complete")
        print('='*60)
        print(f"Installer: {installer_path}")
        print(f"Size: {size:.1f} MB")


if __name__ == '__main__':
    main()
```

---

## Task 6.3: Create Application Icons Guide

### Purpose

Provide instructions for creating application icons.

### File: `resources/icons/README.md`

```markdown
# Application Icons

This directory should contain application icons for different platforms.

## Required Files

### macOS
- `icon.icns` - macOS icon file (required for .app bundle)

Create from a 1024x1024 PNG:
```bash
# Create iconset directory
mkdir icon.iconset

# Generate all required sizes
sips -z 16 16 icon.png --out icon.iconset/icon_16x16.png
sips -z 32 32 icon.png --out icon.iconset/icon_16x16@2x.png
sips -z 32 32 icon.png --out icon.iconset/icon_32x32.png
sips -z 64 64 icon.png --out icon.iconset/icon_32x32@2x.png
sips -z 128 128 icon.png --out icon.iconset/icon_128x128.png
sips -z 256 256 icon.png --out icon.iconset/icon_128x128@2x.png
sips -z 256 256 icon.png --out icon.iconset/icon_256x256.png
sips -z 512 512 icon.png --out icon.iconset/icon_256x256@2x.png
sips -z 512 512 icon.png --out icon.iconset/icon_512x512.png
sips -z 1024 1024 icon.png --out icon.iconset/icon_512x512@2x.png

# Convert to icns
iconutil -c icns icon.iconset
```

### Windows
- `icon.ico` - Windows icon file (multi-resolution)

Create from PNG using ImageMagick:
```bash
convert icon.png -define icon:auto-resize=256,128,64,48,32,16 icon.ico
```

Or use an online converter like https://icoconvert.com/

### Linux
- `icon.png` - PNG icon (512x512 recommended)

Used in desktop files and application launchers.

## Placeholder Icons

If you don't have icons yet, the build will proceed without them. You can add them later by:
1. Creating the icon files
2. Placing them in this directory
3. Rebuilding the application with Phase 4
```

---

## Task 6.4: Create Distribution Documentation

### File: `docs/DISTRIBUTION.md`

```markdown
# TechTim(e) Distribution Guide

## Overview

This guide covers distributing TechTim(e) to end users on macOS and Windows.

## Prerequisites

1. Complete Phase 4 build:
   ```bash
   python scripts/build_app.py
   ```

2. Verify build output exists:
   - macOS: `dist/TechTime.app/`
   - Windows: `dist/TechTime/TechTime.exe`

## macOS Distribution

### Without Code Signing (Development)

For testing or internal distribution:

1. Create a DMG:
   ```bash
   python scripts/distribute_macos.py --dmg
   ```

2. Users may need to bypass Gatekeeper:
   - Right-click the app and choose "Open"
   - Or run: `xattr -cr /path/to/TechTime.app`

### With Code Signing (Production)

For public distribution:

1. Install Apple Developer certificate
2. Configure signing identity in `distribute_macos.py`
3. Run full distribution:
   ```bash
   python scripts/distribute_macos.py --all
   ```

### Notarization Requirements

- Apple Developer account ($99/year)
- Developer ID Application certificate
- App-specific password for notarization

Store credentials:
```bash
xcrun notarytool store-credentials "techtim-notarize" \
    --apple-id "your@email.com" \
    --team-id "TEAMID"
```

## Windows Distribution

### Create Installer

1. Install Inno Setup: https://jrsoftware.org/isinfo.php

2. Run distribution script:
   ```bash
   python scripts/distribute_windows.py
   ```

3. Output: `dist/TechTime-Setup-1.0.0.exe`

### Code Signing (Optional)

For trusted distribution, sign with a code signing certificate:
```bash
signtool sign /f certificate.pfx /p password dist/TechTime-Setup-1.0.0.exe
```

## Troubleshooting

### macOS: "App is damaged"

Run: `xattr -cr /path/to/TechTime.app`

### macOS: Notarization fails

Check credentials:
```bash
xcrun notarytool history --keychain-profile "techtim-notarize"
```

### Windows: Antivirus blocks installer

This is common for unsigned executables. Solutions:
- Sign with a code signing certificate
- Whitelist in antivirus software
- Use Microsoft SmartScreen submission
```

---

## Acceptance Criteria

Phase 6 is complete when:

1. **macOS distribution works**:
   ```bash
   python scripts/distribute_macos.py --dmg
   # Creates dist/TechTime.dmg
   ```

2. **Windows distribution works**:
   ```bash
   python scripts/distribute_windows.py
   # Creates dist/TechTime-Setup-1.0.0.exe
   ```

3. **Documentation exists**:
   - `resources/icons/README.md`
   - `docs/DISTRIBUTION.md`

4. **DMG can be mounted and app runs** (macOS)

5. **Installer runs and installs app** (Windows)

---

## Files Created Summary

| File | Description |
|------|-------------|
| `scripts/distribute_macos.py` | macOS signing, notarization, DMG |
| `scripts/distribute_windows.py` | Windows Inno Setup installer |
| `resources/icons/README.md` | Icon creation instructions |
| `docs/DISTRIBUTION.md` | Distribution guide |

---

## Quick Reference

### macOS Commands

```bash
# Create DMG only (no signing)
python scripts/distribute_macos.py --dmg

# Sign only
python scripts/distribute_macos.py --sign

# Full distribution (sign + notarize + DMG)
python scripts/distribute_macos.py --all
```

### Windows Commands

```bash
# Create installer
python scripts/distribute_windows.py

# Generate .iss script only
python scripts/distribute_windows.py --skip-build
```

---

## Troubleshooting

### macOS App Won't Open

**"App is damaged and can't be opened":**
```bash
xattr -cr dist/TechTime.app
```

**"Developer cannot be verified":**
Right-click the app and choose "Open" to bypass Gatekeeper.

### Windows Antivirus Issues

PyInstaller executables are often flagged by antivirus. Solutions:
1. Sign with a code signing certificate
2. Submit to Microsoft SmartScreen
3. Whitelist in antivirus

### Build Missing

If distribution scripts fail with "App not found":
```bash
# Run Phase 4 build first
python scripts/build_app.py
```

