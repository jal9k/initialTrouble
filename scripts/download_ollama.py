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
import tarfile
import zipfile
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


# =============================================================================
# Configuration
# =============================================================================

# Ollama version to download (use stable release with new archive format)
OLLAMA_VERSION = '0.13.5'

# Platform configurations
# Each entry maps a platform identifier to its download URL and extraction info
PLATFORMS = {
    'darwin-arm64': {
        'url': f'https://github.com/ollama/ollama/releases/download/v{OLLAMA_VERSION}/ollama-darwin.tgz',
        'archive_type': 'tgz',
        'binary_path': 'ollama',  # Path inside archive
        'output_filename': 'ollama',
        'description': 'macOS Apple Silicon (M1/M2/M3)',
    },
    'darwin-x64': {
        'url': f'https://github.com/ollama/ollama/releases/download/v{OLLAMA_VERSION}/ollama-darwin.tgz',
        'archive_type': 'tgz',
        'binary_path': 'ollama',
        'output_filename': 'ollama',
        'description': 'macOS Intel',
    },
    'win32-x64': {
        'url': f'https://github.com/ollama/ollama/releases/download/v{OLLAMA_VERSION}/ollama-windows-amd64.zip',
        'archive_type': 'zip',
        'binary_path': 'ollama.exe',  # Path inside zip
        'output_filename': 'ollama.exe',
        'description': 'Windows x64',
    },
    'linux-x64': {
        'url': f'https://github.com/ollama/ollama/releases/download/v{OLLAMA_VERSION}/ollama-linux-amd64.tgz',
        'archive_type': 'tgz',
        'binary_path': 'bin/ollama',  # Path inside archive
        'output_filename': 'ollama',
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


def extract_from_tgz(archive_path: Path, binary_path: str, output_path: Path) -> bool:
    """
    Extract a specific file from a .tgz archive.
    
    Args:
        archive_path: Path to the .tgz file
        binary_path: Path to the binary inside the archive
        output_path: Where to save the extracted binary
    
    Returns:
        True if extraction succeeded
    """
    print(f"  Extracting {binary_path} from archive...")
    try:
        with tarfile.open(archive_path, 'r:gz') as tar:
            # List members to find the binary
            members = tar.getnames()
            
            # Try exact path first
            if binary_path in members:
                member = tar.getmember(binary_path)
            else:
                # Try finding the binary with a different prefix
                matching = [m for m in members if m.endswith(binary_path) or m.endswith(f'/{binary_path}')]
                if matching:
                    member = tar.getmember(matching[0])
                else:
                    print(f"  ERROR: Binary not found in archive. Available: {members[:10]}...")
                    return False
            
            # Extract to output path
            with tar.extractfile(member) as src:
                if src is None:
                    print(f"  ERROR: Could not read {binary_path} from archive")
                    return False
                with open(output_path, 'wb') as dst:
                    dst.write(src.read())
            
            print(f"  Extracted: {output_path}")
            return True
            
    except Exception as e:
        print(f"  ERROR extracting: {e}")
        return False


def extract_from_zip(archive_path: Path, binary_path: str, output_path: Path) -> bool:
    """
    Extract a specific file from a .zip archive.
    
    Args:
        archive_path: Path to the .zip file
        binary_path: Path to the binary inside the archive
        output_path: Where to save the extracted binary
    
    Returns:
        True if extraction succeeded
    """
    print(f"  Extracting {binary_path} from archive...")
    try:
        with zipfile.ZipFile(archive_path, 'r') as zf:
            # List members to find the binary
            members = zf.namelist()
            
            # Try exact path first
            if binary_path in members:
                target = binary_path
            else:
                # Try finding the binary with a different prefix
                matching = [m for m in members if m.endswith(binary_path) or m.endswith(f'/{binary_path}')]
                if matching:
                    target = matching[0]
                else:
                    print(f"  ERROR: Binary not found in archive. Available: {members[:10]}...")
                    return False
            
            # Extract to output path
            with zf.open(target) as src:
                with open(output_path, 'wb') as dst:
                    dst.write(src.read())
            
            print(f"  Extracted: {output_path}")
            return True
            
    except Exception as e:
        print(f"  ERROR extracting: {e}")
        return False


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
    
    output_path = platform_dir / config['output_filename']
    
    # Check if already downloaded and extracted
    if output_path.exists() and verify_file(output_path):
        print(f"  Already exists: {output_path}")
        print(f"  Size: {format_size(output_path.stat().st_size)}")
        return True
    
    # Download archive
    archive_ext = 'tgz' if config['archive_type'] == 'tgz' else 'zip'
    archive_path = platform_dir / f'ollama-archive.{archive_ext}'
    
    try:
        download_with_progress(config['url'], archive_path)
        
        # Extract binary from archive
        if config['archive_type'] == 'tgz':
            success = extract_from_tgz(archive_path, config['binary_path'], output_path)
        else:
            success = extract_from_zip(archive_path, config['binary_path'], output_path)
        
        if not success:
            return False
        
        # Verify extraction
        if not verify_file(output_path):
            print("  ERROR: Extracted file verification failed")
            output_path.unlink(missing_ok=True)
            return False
        
        # Make executable on Unix
        if not platform.startswith('win'):
            make_executable(output_path)
        
        # Clean up archive
        archive_path.unlink(missing_ok=True)
        
        print(f"  SUCCESS: Extracted {format_size(output_path.stat().st_size)}")
        return True
        
    except Exception as e:
        print(f"  FAILED: {e}")
        archive_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
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
