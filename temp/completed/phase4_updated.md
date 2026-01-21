# Phase 4: Build System (UPDATED)

## CHANGES FROM ORIGINAL

This document has been updated to match the actual TechTim(e) codebase structure.

| Task | Original | Updated | Reason |
|------|----------|---------|--------|
| 4.4 Entry Point | `['main.py']` | `['desktop_main.py']` | Desktop entry point from Phase 2 |
| 4.4 Prompts Path | `('backend/prompts', 'backend/prompts')` | `('prompts', 'prompts')` | Prompts are at project root |
| 4.4 Hidden Imports | Generic placeholder comments | Full list of 17 diagnostic modules | Ensure all tools are bundled |
| 4.4 Hidden Imports | Missing analytics | Added `analytics.*` modules | Analytics is top-level module |
| 4.4 Data Files | Missing analytics | Added analytics module path | Include analytics in bundle |

---

## Objective

Create the build infrastructure that downloads platform-specific Ollama binaries, builds the Next.js frontend as static files, and packages everything into a distributable application using PyInstaller.

## Prerequisites

Before starting this phase, ensure you have:
- Phases 1-3 completed
- Python 3.11+ with PyInstaller installed: `pip install pyinstaller`
- Node.js 18+ and npm for frontend builds
- Internet connection for downloading Ollama binaries

---

## Task 4.1: Create the Scripts Directory Structure

### Purpose

Organize all build-related scripts in a dedicated directory.

### Directory Structure

Create the following structure in your project root:

```
scripts/
├── __init__.py           # Makes scripts a Python package (optional)
├── download_ollama.py    # Downloads Ollama binaries
├── build_frontend.py     # Builds Next.js static export
└── build_app.py          # Master build orchestrator
```

### File: `scripts/__init__.py`

```python
"""
Build scripts for TechTim(e) Desktop Application.

These scripts handle:
- Downloading Ollama binaries for all platforms
- Building the Next.js frontend
- Creating PyInstaller bundles
"""
```

---

## Task 4.2: Create the Ollama Download Script

### Purpose

Download Ollama binaries for macOS (both ARM and Intel), Windows, and Linux. These binaries are bundled with the application so users don't need to install Ollama separately.

### File: `scripts/download_ollama.py`

```python
#!/usr/bin/env python3
"""
Downloads Ollama binaries for all supported platforms.

This script fetches pre-built Ollama executables from the official
GitHub releases and places them in the resources/ollama/ directory,
organized by platform.

Run this before building the application:
    python scripts/download_ollama.py

The script is idempotent - it skips downloads for binaries that
already exist.
"""
import os
import sys
import stat
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


# =============================================================================
# Configuration
# =============================================================================

# Ollama version to download
OLLAMA_VERSION = '0.5.4'

# Platform configurations
# Each entry maps a platform identifier to its download URL and binary name
PLATFORMS = {
    'darwin-arm64': {
        'url': f'https://github.com/ollama/ollama/releases/download/v{OLLAMA_VERSION}/ollama-darwin',
        'filename': 'ollama',
        'description': 'macOS Apple Silicon (M1/M2/M3)',
    },
    'darwin-x64': {
        'url': f'https://github.com/ollama/ollama/releases/download/v{OLLAMA_VERSION}/ollama-darwin',
        'filename': 'ollama',
        'description': 'macOS Intel',
    },
    'win32-x64': {
        'url': f'https://github.com/ollama/ollama/releases/download/v{OLLAMA_VERSION}/ollama-windows-amd64.exe',
        'filename': 'ollama.exe',
        'description': 'Windows x64',
    },
    'linux-x64': {
        'url': f'https://github.com/ollama/ollama/releases/download/v{OLLAMA_VERSION}/ollama-linux-amd64',
        'filename': 'ollama',
        'description': 'Linux x64',
    },
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_project_root() -> Path:
    """Get the project root directory (parent of scripts/)."""
    return Path(__file__).parent.parent


def format_size(size_bytes: int) -> str:
    """Format byte size as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def download_with_progress(url: str, dest: Path) -> None:
    """
    Download a file with progress indication.
    
    Args:
        url: URL to download from
        dest: Destination file path
    """
    print(f"  Downloading from: {url}")
    print(f"  Saving to: {dest}")
    
    # Create request with user agent (some servers require it)
    request = urllib.request.Request(
        url,
        headers={'User-Agent': 'TechTime-Build/1.0'}
    )
    
    try:
        with urllib.request.urlopen(request) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            block_size = 8192
            
            with open(dest, 'wb') as f:
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    
                    downloaded += len(buffer)
                    f.write(buffer)
                    
                    # Show progress
                    if total_size > 0:
                        percent = downloaded * 100 // total_size
                        bar_width = 40
                        filled = int(bar_width * downloaded / total_size)
                        bar = '=' * filled + ' ' * (bar_width - filled)
                        size_str = f"{format_size(downloaded)}/{format_size(total_size)}"
                        sys.stdout.write(f'\r  [{bar}] {percent}% ({size_str})')
                        sys.stdout.flush()
            
            print()  # Newline after progress bar
            
    except urllib.error.HTTPError as e:
        print(f"\n  ERROR: HTTP {e.code} - {e.reason}")
        raise
    except urllib.error.URLError as e:
        print(f"\n  ERROR: {e.reason}")
        raise


def make_executable(path: Path) -> None:
    """
    Make a file executable on Unix systems.
    
    Args:
        path: Path to the file
    """
    if sys.platform != 'win32':
        current_mode = path.stat().st_mode
        path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"  Made executable: {path.name}")


def verify_file(path: Path, min_size: int = 1000000) -> bool:
    """
    Verify a downloaded file is valid.
    
    Args:
        path: Path to the file
        min_size: Minimum expected file size in bytes
    
    Returns:
        True if file appears valid
    """
    if not path.exists():
        return False
    
    size = path.stat().st_size
    if size < min_size:
        print(f"  WARNING: File seems too small ({format_size(size)})")
        return False
    
    return True


# =============================================================================
# Main Download Logic
# =============================================================================

def download_platform(platform: str, config: dict, resources_dir: Path) -> bool:
    """
    Download Ollama binary for a specific platform.
    
    Args:
        platform: Platform identifier (e.g., 'darwin-arm64')
        config: Platform configuration dict
        resources_dir: Base resources directory
    
    Returns:
        True if download succeeded or file already exists
    """
    platform_dir = resources_dir / platform
    platform_dir.mkdir(parents=True, exist_ok=True)
    
    dest_path = platform_dir / config['filename']
    
    # Check if already downloaded
    if dest_path.exists() and verify_file(dest_path):
        print(f"  Already exists: {dest_path}")
        print(f"  Size: {format_size(dest_path.stat().st_size)}")
        return True
    
    # Download
    try:
        download_with_progress(config['url'], dest_path)
        
        # Verify download
        if not verify_file(dest_path):
            print("  ERROR: Downloaded file verification failed")
            dest_path.unlink(missing_ok=True)
            return False
        
        # Make executable on Unix
        if not platform.startswith('win'):
            make_executable(dest_path)
        
        print(f"  SUCCESS: Downloaded {format_size(dest_path.stat().st_size)}")
        return True
        
    except Exception as e:
        print(f"  FAILED: {e}")
        dest_path.unlink(missing_ok=True)
        return False


def main():
    """Main entry point for the download script."""
    print("=" * 60)
    print("Ollama Binary Downloader")
    print(f"Version: {OLLAMA_VERSION}")
    print("=" * 60)
    
    project_root = get_project_root()
    resources_dir = project_root / 'resources' / 'ollama'
    
    print(f"\nProject root: {project_root}")
    print(f"Resources directory: {resources_dir}")
    
    # Track results
    results = {}
    
    # Download for each platform
    for platform, config in PLATFORMS.items():
        print(f"\n{'─' * 60}")
        print(f"Platform: {platform}")
        print(f"Description: {config['description']}")
        print('─' * 60)
        
        success = download_platform(platform, config, resources_dir)
        results[platform] = success
    
    # Summary
    print(f"\n{'=' * 60}")
    print("Download Summary")
    print('=' * 60)
    
    all_success = True
    for platform, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  {platform}: {status}")
        if not success:
            all_success = False
    
    print()
    
    if all_success:
        print("All downloads completed successfully!")
        print(f"\nOllama binaries are in: {resources_dir}")
        return 0
    else:
        print("WARNING: Some downloads failed. Check the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
```

### Verification Steps

Run the download script:

```bash
python scripts/download_ollama.py
```

Expected output:
- Creates `resources/ollama/` directory
- Downloads binaries for all platforms (~200MB each)
- Shows progress bars during download

---

## Task 4.3: Create the Frontend Build Script

### Purpose

Build the Next.js frontend as static files that can be loaded by PyWebView.

### File: `scripts/build_frontend.py`

```python
#!/usr/bin/env python3
"""
Builds the Next.js frontend as a static export.

This script:
1. Installs npm dependencies
2. Runs the Next.js build
3. Verifies the output

Run this before packaging the application:
    python scripts/build_frontend.py

The output will be in frontend/techtime/out/
"""
import subprocess
import sys
import shutil
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def run_command(cmd: list[str], cwd: Path, description: str) -> bool:
    """
    Run a command and handle errors.
    
    Args:
        cmd: Command and arguments
        cwd: Working directory
        description: Description for logging
    
    Returns:
        True if command succeeded
    """
    print(f"\n{description}...")
    print(f"  Command: {' '.join(cmd)}")
    print(f"  Directory: {cwd}")
    print()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            # Inherit stdout/stderr for real-time output
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Command failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"\nERROR: Command not found: {cmd[0]}")
        print("Make sure Node.js and npm are installed and in PATH")
        return False


def find_npm() -> str:
    """Find the npm executable."""
    # On Windows, npm might be npm.cmd
    if sys.platform == 'win32':
        npm = shutil.which('npm.cmd') or shutil.which('npm')
    else:
        npm = shutil.which('npm')
    
    if not npm:
        raise FileNotFoundError(
            "npm not found. Please install Node.js from https://nodejs.org"
        )
    
    return npm


def main():
    """Main entry point."""
    print("=" * 60)
    print("Frontend Build Script")
    print("=" * 60)
    
    project_root = get_project_root()
    frontend_dir = project_root / 'frontend' / 'techtime'
    
    # Verify frontend directory exists
    if not frontend_dir.exists():
        print(f"\nERROR: Frontend directory not found: {frontend_dir}")
        print("\nExpected structure:")
        print("  project_root/")
        print("    frontend/")
        print("      techtime/")
        print("        package.json")
        print("        next.config.ts")
        print("        ...")
        return 1
    
    if not (frontend_dir / 'package.json').exists():
        print(f"\nERROR: package.json not found in {frontend_dir}")
        return 1
    
    print(f"\nFrontend directory: {frontend_dir}")
    
    # Find npm
    try:
        npm = find_npm()
        print(f"Using npm: {npm}")
    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        return 1
    
    # Step 1: Install dependencies
    if not run_command(
        [npm, 'install'],
        frontend_dir,
        "Installing dependencies"
    ):
        return 1
    
    # Step 2: Build the frontend
    if not run_command(
        [npm, 'run', 'build'],
        frontend_dir,
        "Building frontend"
    ):
        return 1
    
    # Step 3: Verify output
    out_dir = frontend_dir / 'out'
    index_html = out_dir / 'index.html'
    
    if not index_html.exists():
        print(f"\nERROR: Build output not found at {index_html}")
        print("\nMake sure next.config.ts has:")
        print("  output: 'export'")
        return 1
    
    # Count output files
    file_count = sum(1 for _ in out_dir.rglob('*') if _.is_file())
    total_size = sum(f.stat().st_size for f in out_dir.rglob('*') if f.is_file())
    
    print(f"\n{'=' * 60}")
    print("Build Successful!")
    print('=' * 60)
    print(f"\nOutput directory: {out_dir}")
    print(f"Files generated: {file_count}")
    print(f"Total size: {total_size / 1024 / 1024:.2f} MB")
    
    # List key files
    print("\nKey files:")
    for pattern in ['index.html', '_next/static/**/*.js', '_next/static/**/*.css']:
        files = list(out_dir.glob(pattern))[:3]
        for f in files:
            rel_path = f.relative_to(out_dir)
            print(f"  {rel_path}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

### Verification Steps

Run the build script:

```bash
python scripts/build_frontend.py
```

Expected output:
- Installs npm dependencies
- Builds Next.js
- Creates `frontend/techtime/out/` with static files

---

## Task 4.4: Create the PyInstaller Spec File

### Purpose

Define how PyInstaller packages the application, including which files to bundle and platform-specific settings.

**IMPORTANT:** This spec file has been updated to use the correct paths and include all necessary modules.

### File: `techtim.spec` (in project root)

```python
# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification file for TechTim(e) Desktop Application.

This file defines:
- What Python modules to include
- What data files to bundle
- Platform-specific configurations
- Application metadata

Build the application with:
    pyinstaller techtim.spec --clean

The output will be in the dist/ directory.

UPDATED: Entry point changed to desktop_main.py, prompts path corrected,
all diagnostic modules explicitly listed.
"""
import sys
import platform
from pathlib import Path

# Get the spec file directory (project root)
SPEC_DIR = Path(SPECPATH)

# =============================================================================
# Platform Detection
# =============================================================================

def get_platform_config():
    """
    Get platform-specific configuration.
    
    Returns:
        Tuple of (ollama_dir, icon_file, extra_binaries)
    """
    if sys.platform == 'darwin':
        # macOS - detect ARM vs Intel
        arch = 'arm64' if platform.machine() == 'arm64' else 'x64'
        return (
            f'darwin-{arch}',
            'resources/icons/icon.icns',
            [],
        )
    elif sys.platform == 'win32':
        return (
            'win32-x64',
            'resources/icons/icon.ico',
            [],
        )
    else:
        # Linux
        return (
            'linux-x64',
            None,  # No icon on Linux (uses desktop file)
            [],
        )


OLLAMA_DIR, ICON_FILE, EXTRA_BINARIES = get_platform_config()

# Resolve icon path
if ICON_FILE:
    icon_path = SPEC_DIR / ICON_FILE
    if not icon_path.exists():
        print(f"Warning: Icon file not found: {icon_path}")
        ICON_FILE = None
    else:
        ICON_FILE = str(icon_path)

# =============================================================================
# Data Files
# =============================================================================

# Files and directories to include in the bundle
# Format: (source_path, destination_path_in_bundle)
datas = [
    # UPDATED: Prompts are at project root, not backend/prompts
    ('prompts', 'prompts'),
    
    # Frontend static files
    ('frontend/techtime/out', 'frontend/out'),
    
    # Ollama binary (platform-specific)
    (f'resources/ollama/{OLLAMA_DIR}', f'resources/ollama/{OLLAMA_DIR}'),
    
    # UPDATED: Include analytics module data if any
    # (Analytics is a Python module, included via hiddenimports)
]

# Verify data files exist
for src, _ in datas:
    src_path = SPEC_DIR / src
    if not src_path.exists():
        print(f"Warning: Data path not found: {src_path}")

# =============================================================================
# Hidden Imports
# =============================================================================

# Modules that PyInstaller might miss during analysis
# UPDATED: Complete list of all modules based on actual codebase
hiddenimports = [
    # =========================================================================
    # PyWebView dependencies
    # =========================================================================
    'webview',
    
    # =========================================================================
    # HTTP client
    # =========================================================================
    'httpx',
    'httpx._transports',
    'httpx._transports.default',
    'httpcore',
    'h11',
    'certifi',
    'sniffio',
    'anyio',
    'anyio._backends',
    'anyio._backends._asyncio',
    
    # =========================================================================
    # Pydantic
    # =========================================================================
    'pydantic',
    'pydantic.deprecated',
    'pydantic.deprecated.decorator',
    'pydantic_settings',
    
    # =========================================================================
    # UPDATED: Analytics module (top-level, not backend.analytics)
    # =========================================================================
    'analytics',
    'analytics.collector',
    'analytics.storage',
    'analytics.models',
    'analytics.cost',
    'analytics.patterns',
    'analytics.api',
    
    # =========================================================================
    # Backend core modules
    # =========================================================================
    'backend',
    'backend.config',
    'backend.prompts',
    'backend.chat_service',
    'backend.logging_config',
    
    # =========================================================================
    # Backend LLM modules
    # =========================================================================
    'backend.llm',
    'backend.llm.base',
    'backend.llm.router',
    'backend.llm.ollama_client',
    'backend.llm.openai_client',
    
    # =========================================================================
    # Backend tools modules
    # =========================================================================
    'backend.tools',
    'backend.tools.api',
    'backend.tools.registry',
    'backend.tools.schemas',
    
    # =========================================================================
    # UPDATED: All diagnostic modules (complete list)
    # =========================================================================
    'backend.diagnostics',
    'backend.diagnostics.base',
    'backend.diagnostics.platform',
    'backend.diagnostics.adapter',
    'backend.diagnostics.bluetooth',
    'backend.diagnostics.connectivity',
    'backend.diagnostics.dns',
    'backend.diagnostics.ip_config',
    'backend.diagnostics.ip_reset',
    'backend.diagnostics.process_mgmt',
    'backend.diagnostics.reachability',
    'backend.diagnostics.temp_files',
    'backend.diagnostics.vpn',
    'backend.diagnostics.wifi',
    
    # =========================================================================
    # UPDATED: Windows-specific diagnostic modules
    # =========================================================================
    'backend.diagnostics.windows',
    'backend.diagnostics.windows.dell_audio',
    'backend.diagnostics.windows.log_analysis',
    'backend.diagnostics.windows.office_repair',
    'backend.diagnostics.windows.robocopy',
    'backend.diagnostics.windows.system_repair',
    
    # =========================================================================
    # Desktop modules
    # =========================================================================
    'desktop',
    'desktop.api',
    'desktop.ollama_manager',
    'desktop.exceptions',
    
    # =========================================================================
    # Async support
    # =========================================================================
    'asyncio',
    'concurrent.futures',
]

# Platform-specific hidden imports
if sys.platform == 'darwin':
    hiddenimports.extend([
        'webview.platforms.cocoa',
        'Foundation',
        'AppKit',
        'WebKit',
    ])
elif sys.platform == 'win32':
    hiddenimports.extend([
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
        'clr',
        'pythonnet',
    ])
else:
    hiddenimports.extend([
        'webview.platforms.gtk',
        'gi',
        'gi.repository',
    ])

# =============================================================================
# Excluded Modules
# =============================================================================

# Large modules we don't need
excludes = [
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'PIL',
    'tkinter',
    'test',
    'unittest',
    'xmlrpc',
    'pydoc',
]

# =============================================================================
# Analysis
# =============================================================================

a = Analysis(
    # UPDATED: Entry point is desktop_main.py, not main.py
    ['desktop_main.py'],
    
    # Additional paths to search for imports
    pathex=[str(SPEC_DIR)],
    
    # Binary files to include
    binaries=EXTRA_BINARIES,
    
    # Data files
    datas=datas,
    
    # Hidden imports
    hiddenimports=hiddenimports,
    
    # Hook directories (custom PyInstaller hooks)
    hookspath=[],
    
    # Additional hook configuration
    hooksconfig={},
    
    # Runtime hooks (executed at startup)
    runtime_hooks=[],
    
    # Modules to exclude
    excludes=excludes,
    
    # Windows-specific
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    
    # Encryption (None = no encryption)
    cipher=None,
    
    # Don't archive Python modules (easier debugging)
    noarchive=False,
)

# =============================================================================
# PYZ Archive
# =============================================================================

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,
)

# =============================================================================
# Executable
# =============================================================================

exe = EXE(
    pyz,
    a.scripts,
    [],  # Don't include binaries in EXE (use COLLECT instead)
    exclude_binaries=True,
    name='TechTime',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress with UPX if available
    console=False,  # No console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_FILE,
)

# =============================================================================
# Collect Files
# =============================================================================

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TechTime',
)

# =============================================================================
# macOS App Bundle
# =============================================================================

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='TechTime.app',
        icon=ICON_FILE,
        bundle_identifier='com.techtim.desktop',
        version='1.0.0',
        info_plist={
            'CFBundleName': 'TechTime',
            'CFBundleDisplayName': 'TechTim(e)',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleExecutable': 'TechTime',
            'CFBundleIdentifier': 'com.techtim.desktop',
            'CFBundlePackageType': 'APPL',
            'CFBundleSignature': '????',
            'LSMinimumSystemVersion': '10.15.0',
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,  # Support dark mode
            'LSApplicationCategoryType': 'public.app-category.utilities',
        },
    )
```

---

## Task 4.5: Create the Master Build Script

### Purpose

Orchestrate the entire build process: download binaries, build frontend, run PyInstaller.

### File: `scripts/build_app.py`

```python
#!/usr/bin/env python3
"""
Master build script for TechTim(e) Desktop Application.

This script orchestrates the complete build process:
1. Downloads Ollama binaries (if not present)
2. Builds the Next.js frontend
3. Runs PyInstaller to create the bundle

Usage:
    python scripts/build_app.py              # Full build
    python scripts/build_app.py --skip-deps  # Skip Ollama download
    python scripts/build_app.py --clean      # Clean before building

The output will be in the dist/ directory.
"""
import argparse
import subprocess
import sys
import shutil
from pathlib import Path
from datetime import datetime


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def print_header(text: str):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f" {text}")
    print('=' * 60)


def print_step(number: int, text: str):
    """Print a step indicator."""
    print(f"\n[Step {number}] {text}")
    print('-' * 40)


def run_script(script_name: str) -> bool:
    """
    Run a Python script from the scripts directory.
    
    Args:
        script_name: Name of the script file
    
    Returns:
        True if script succeeded
    """
    script_path = get_project_root() / 'scripts' / script_name
    
    if not script_path.exists():
        print(f"ERROR: Script not found: {script_path}")
        return False
    
    result = subprocess.run([sys.executable, str(script_path)])
    return result.returncode == 0


def run_pyinstaller() -> bool:
    """
    Run PyInstaller with the spec file.
    
    Returns:
        True if build succeeded
    """
    project_root = get_project_root()
    spec_file = project_root / 'techtim.spec'
    
    if not spec_file.exists():
        print(f"ERROR: Spec file not found: {spec_file}")
        return False
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print(f"Using PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("ERROR: PyInstaller not installed")
        print("Run: pip install pyinstaller")
        return False
    
    # Run PyInstaller
    result = subprocess.run(
        [
            sys.executable, '-m', 'PyInstaller',
            str(spec_file),
            '--clean',
            '--noconfirm',
        ],
        cwd=project_root,
    )
    
    return result.returncode == 0


def clean_build_artifacts():
    """Remove build artifacts from previous builds."""
    project_root = get_project_root()
    
    dirs_to_clean = [
        project_root / 'build',
        project_root / 'dist',
        project_root / '__pycache__',
    ]
    
    for dir_path in dirs_to_clean:
        if dir_path.exists():
            print(f"Removing: {dir_path}")
            shutil.rmtree(dir_path)
    
    # Clean .pyc files
    for pyc in project_root.rglob('*.pyc'):
        pyc.unlink()


def verify_prerequisites() -> bool:
    """
    Verify all prerequisites are met.
    
    Returns:
        True if all prerequisites are available
    """
    errors = []
    
    # Check Python version
    if sys.version_info < (3, 11):
        errors.append(f"Python 3.11+ required, found {sys.version}")
    
    # Check PyInstaller
    try:
        import PyInstaller
    except ImportError:
        errors.append("PyInstaller not installed (pip install pyinstaller)")
    
    # Check npm
    npm = shutil.which('npm') or shutil.which('npm.cmd')
    if not npm:
        errors.append("npm not found (install Node.js)")
    
    # Check spec file
    spec_file = get_project_root() / 'techtim.spec'
    if not spec_file.exists():
        errors.append(f"Spec file not found: {spec_file}")
    
    # UPDATED: Check desktop_main.py entry point
    entry_point = get_project_root() / 'desktop_main.py'
    if not entry_point.exists():
        errors.append(f"Entry point not found: {entry_point}")
    
    if errors:
        print("Prerequisites check failed:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("All prerequisites satisfied")
    return True


def get_build_output_info() -> dict:
    """Get information about the build output."""
    project_root = get_project_root()
    dist_dir = project_root / 'dist'
    
    info = {
        'exists': dist_dir.exists(),
        'path': dist_dir,
        'items': [],
    }
    
    if info['exists']:
        for item in dist_dir.iterdir():
            item_info = {
                'name': item.name,
                'path': item,
                'is_dir': item.is_dir(),
            }
            
            if item.is_dir():
                # Calculate directory size
                total_size = sum(
                    f.stat().st_size
                    for f in item.rglob('*')
                    if f.is_file()
                )
                item_info['size'] = total_size
            else:
                item_info['size'] = item.stat().st_size
            
            info['items'].append(item_info)
    
    return info


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Build TechTim(e) Desktop Application'
    )
    parser.add_argument(
        '--skip-deps',
        action='store_true',
        help='Skip downloading Ollama binaries'
    )
    parser.add_argument(
        '--skip-frontend',
        action='store_true',
        help='Skip building the frontend'
    )
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Clean build artifacts before building'
    )
    
    args = parser.parse_args()
    
    start_time = datetime.now()
    
    print_header("TechTim(e) Desktop Application Build")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Platform: {sys.platform}")
    print(f"Python: {sys.version}")
    
    # Clean if requested
    if args.clean:
        print_step(0, "Cleaning build artifacts")
        clean_build_artifacts()
    
    # Verify prerequisites
    print_step(1, "Checking prerequisites")
    if not verify_prerequisites():
        return 1
    
    # Download Ollama binaries
    if not args.skip_deps:
        print_step(2, "Downloading Ollama binaries")
        if not run_script('download_ollama.py'):
            print("\nERROR: Failed to download Ollama binaries")
            return 1
    else:
        print_step(2, "Skipping Ollama download (--skip-deps)")
    
    # Build frontend
    if not args.skip_frontend:
        print_step(3, "Building frontend")
        if not run_script('build_frontend.py'):
            print("\nERROR: Failed to build frontend")
            return 1
    else:
        print_step(3, "Skipping frontend build (--skip-frontend)")
    
    # Run PyInstaller
    print_step(4, "Running PyInstaller")
    if not run_pyinstaller():
        print("\nERROR: PyInstaller build failed")
        return 1
    
    # Build summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    print_header("Build Complete!")
    print(f"\nDuration: {duration}")
    
    # Show output info
    output_info = get_build_output_info()
    if output_info['exists']:
        print(f"\nBuild output: {output_info['path']}")
        print("\nContents:")
        for item in output_info['items']:
            size_mb = item['size'] / 1024 / 1024
            icon = 'DIR' if item['is_dir'] else 'FILE'
            print(f"  [{icon}] {item['name']} ({size_mb:.1f} MB)")
        
        # Platform-specific instructions
        if sys.platform == 'darwin':
            app_path = output_info['path'] / 'TechTime.app'
            if app_path.exists():
                print(f"\nTo run the app:")
                print(f"  open {app_path}")
        elif sys.platform == 'win32':
            exe_path = output_info['path'] / 'TechTime' / 'TechTime.exe'
            if exe_path.exists():
                print(f"\nTo run the app:")
                print(f"  {exe_path}")
        else:
            exe_path = output_info['path'] / 'TechTime' / 'TechTime'
            if exe_path.exists():
                print(f"\nTo run the app:")
                print(f"  {exe_path}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

---

## Task 4.6: Create Application Icons (Optional)

### Purpose

Provide application icons for different platforms.

### Directory: `resources/icons/`

Create placeholder icons or use your own:

```
resources/
└── icons/
    ├── icon.icns    # macOS (1024x1024, can include multiple sizes)
    ├── icon.ico     # Windows (256x256, can include multiple sizes)
    └── icon.png     # Linux/general use (512x512)
```

For development, you can create simple placeholder icons using online tools or skip this step (the application will use default icons).

---

## Acceptance Criteria

Phase 4 is complete when:

1. **Ollama downloads work**: Running `python scripts/download_ollama.py` successfully downloads binaries to `resources/ollama/`

2. **Frontend builds**: Running `python scripts/build_frontend.py` creates `frontend/techtime/out/` with static files

3. **PyInstaller spec is valid**: Running `pyinstaller techtim.spec --clean` completes without errors

4. **Master build works**: Running `python scripts/build_app.py` orchestrates the full build process

5. **Output is created**: After build, `dist/TechTime/` (or `dist/TechTime.app` on macOS) exists and contains the application

---

## Files Created Summary

| File | Description |
|------|-------------|
| `scripts/__init__.py` | Package marker |
| `scripts/download_ollama.py` | Ollama binary downloader |
| `scripts/build_frontend.py` | Next.js build script |
| `scripts/build_app.py` | Master build orchestrator |
| `techtim.spec` | PyInstaller configuration (UPDATED) |
| `resources/icons/` | Application icons (optional) |

---

## Troubleshooting

### PyInstaller can't find modules

Add missing modules to `hiddenimports` in `techtim.spec`:

```python
hiddenimports = [
    ...
    'missing_module_name',
]
```

### Build output is too large

Add unnecessary modules to `excludes` in `techtim.spec`:

```python
excludes = [
    ...
    'large_unused_module',
]
```

### macOS app won't open

Check Console.app for errors. Common issues:
- Missing code signature (run codesign)
- Quarantine flag (run `xattr -cr dist/TechTime.app`)

---

## Next Phase

After completing Phase 4, proceed to **Phase 5: Testing**, which covers testing the built application and creating automated tests.

