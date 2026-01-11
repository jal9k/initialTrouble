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
