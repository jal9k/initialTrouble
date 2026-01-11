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

