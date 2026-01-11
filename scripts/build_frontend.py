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

