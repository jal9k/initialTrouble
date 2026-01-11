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
- Submit to Microsoft SmartScreen
- Whitelist in antivirus software

### Build Missing

If distribution scripts fail with "App not found":
```bash
# Run Phase 4 build first
python scripts/build_app.py
```

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
