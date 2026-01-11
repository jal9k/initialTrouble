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

