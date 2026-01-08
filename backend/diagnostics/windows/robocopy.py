"""Windows Robocopy diagnostic - robust file copying with retry logic.

Windows-only tool for reliable file/folder copying operations.
"""

import re
from typing import Any

from ..base import BaseDiagnostic, DiagnosticResult
from ..platform import Platform


class Robocopy(BaseDiagnostic):
    """Run robocopy for robust file copying with retry logic."""

    name = "robocopy"
    description = "Robust file copy with retry logic (Windows only)"
    osi_layer = "Application"

    # Robocopy exit codes (0-7 are success, 8+ are errors)
    EXIT_CODES = {
        0: "No files copied. No failure.",
        1: "Files copied successfully.",
        2: "Extra files or directories detected.",
        3: "Files copied. Extra files detected.",
        4: "Mismatched files or directories detected.",
        5: "Files copied. Mismatched detected.",
        6: "Extra and mismatched detected.",
        7: "Files copied. Extra and mismatched detected.",
        8: "Some files could not be copied (copy errors).",
        16: "Serious error. No files copied.",
    }

    async def run(
        self,
        source: str,
        destination: str,
        files: str | None = None,
        retries: int = 3,
        wait: int = 10,
        mirror: bool = False,
        move: bool = False,
    ) -> DiagnosticResult:
        """
        Run robocopy to copy files.

        Args:
            source: Source directory path
            destination: Destination directory path
            files: File pattern to copy (e.g., "*.txt"). Default: all files
            retries: Number of retries on failure (default: 3)
            wait: Wait time between retries in seconds (default: 10)
            mirror: Use mirror mode (/MIR) - makes destination match source
            move: Move files instead of copy (/MOV)

        Returns:
            DiagnosticResult with copy results
        """
        # Check platform
        if self.platform != Platform.WINDOWS:
            return self._failure(
                error="Robocopy is only available on Windows",
                suggestions=[
                    "Use rsync on macOS/Linux for similar functionality",
                    "rsync -av source/ destination/",
                ],
            )

        # Validate inputs
        if not source:
            return self._failure(
                error="Source directory is required",
                suggestions=["Provide the source directory path"],
            )
        if not destination:
            return self._failure(
                error="Destination directory is required",
                suggestions=["Provide the destination directory path"],
            )

        # Build robocopy command
        cmd_parts = ["robocopy"]
        cmd_parts.append(f'"{source}"')
        cmd_parts.append(f'"{destination}"')

        if files:
            cmd_parts.append(f'"{files}"')

        # Add retry options
        cmd_parts.append(f"/R:{retries}")
        cmd_parts.append(f"/W:{wait}")

        # Add mode options
        if mirror:
            cmd_parts.append("/MIR")
        elif move:
            cmd_parts.append("/MOV")

        # Add common useful options
        cmd_parts.append("/NP")  # No progress - cleaner output
        cmd_parts.append("/NDL")  # No directory list
        cmd_parts.append("/NC")  # No class
        cmd_parts.append("/BYTES")  # Show sizes in bytes

        cmd = " ".join(cmd_parts)

        # Calculate timeout based on operation
        # Robocopy can take a long time for large copies
        timeout = 3600  # 1 hour max

        result = await self.executor.run(cmd, shell=True, timeout=timeout)

        # Parse robocopy output
        copy_data = self._parse_robocopy_output(result.stdout, result.return_code)
        copy_data["source"] = source
        copy_data["destination"] = destination
        copy_data["mode"] = "mirror" if mirror else ("move" if move else "copy")
        copy_data["file_pattern"] = files

        # Determine success based on exit code
        # Exit codes 0-7 are considered success
        success = result.return_code <= 7

        # Generate suggestions
        suggestions = []
        if not success:
            if result.return_code == 8:
                suggestions.extend([
                    "Some files could not be copied",
                    "Check if files are in use or locked",
                    "Verify you have read permissions on source",
                    "Verify you have write permissions on destination",
                ])
            elif result.return_code == 16:
                suggestions.extend([
                    "Serious error occurred - no files were copied",
                    "Verify source and destination paths are valid",
                    "Check if you have sufficient permissions",
                    "Ensure destination drive has enough space",
                ])
            else:
                suggestions.append(f"Robocopy exited with code {result.return_code}")
        else:
            if copy_data.get("files_copied", 0) > 0:
                suggestions.append(
                    f"Successfully copied {copy_data['files_copied']} file(s)"
                )
            if copy_data.get("dirs_created", 0) > 0:
                suggestions.append(
                    f"Created {copy_data['dirs_created']} director(ies)"
                )

        if mirror and success:
            suggestions.append("Mirror mode: destination now matches source")

        if move and success:
            suggestions.append("Move mode: original files have been removed")

        if success:
            return self._success(
                data=copy_data,
                raw_output=result.stdout,
                suggestions=suggestions if suggestions else None,
            )
        else:
            return self._failure(
                error=self.EXIT_CODES.get(result.return_code, f"Unknown error (code {result.return_code})"),
                data=copy_data,
                raw_output=result.stdout + "\n" + result.stderr,
                suggestions=suggestions,
            )

    def _parse_robocopy_output(self, output: str, exit_code: int) -> dict[str, Any]:
        """Parse robocopy command output."""
        data: dict[str, Any] = {
            "exit_code": exit_code,
            "exit_meaning": self.EXIT_CODES.get(exit_code, "Unknown"),
            "files_copied": 0,
            "files_skipped": 0,
            "files_failed": 0,
            "dirs_created": 0,
            "bytes_copied": 0,
            "speed_mbps": None,
        }

        # Parse the summary section
        # Look for lines like:
        #   Files :        10         5         3         0         2         0
        #   Dirs :          5         2         0         0         3         0

        for line in output.split("\n"):
            line = line.strip()

            # Parse Files line
            if line.startswith("Files :") or line.startswith("Files:"):
                numbers = re.findall(r"\d+", line)
                if len(numbers) >= 3:
                    data["files_total"] = int(numbers[0])
                    data["files_copied"] = int(numbers[1])
                    data["files_skipped"] = int(numbers[2])
                    if len(numbers) >= 5:
                        data["files_failed"] = int(numbers[4])

            # Parse Dirs line
            elif line.startswith("Dirs :") or line.startswith("Dirs:"):
                numbers = re.findall(r"\d+", line)
                if len(numbers) >= 2:
                    data["dirs_total"] = int(numbers[0])
                    data["dirs_created"] = int(numbers[1])

            # Parse Bytes line
            elif line.startswith("Bytes :") or line.startswith("Bytes:"):
                numbers = re.findall(r"\d+", line.replace(",", ""))
                if numbers:
                    data["bytes_copied"] = int(numbers[0]) if len(numbers) > 1 else int(numbers[0])

            # Parse Speed line
            elif "Speed :" in line or "Speed:" in line:
                speed_match = re.search(r"(\d+\.?\d*)\s*(?:Bytes|B)/s", line, re.IGNORECASE)
                if speed_match:
                    bytes_per_sec = float(speed_match.group(1))
                    data["speed_mbps"] = round(bytes_per_sec / (1024 * 1024), 2)

        return data


# Module-level function for easy importing
async def robocopy(
    source: str,
    destination: str,
    files: str | None = None,
    retries: int = 3,
    wait: int = 10,
    mirror: bool = False,
    move: bool = False,
) -> DiagnosticResult:
    """Run robocopy for robust file copying.
    
    Args:
        source: Source directory path
        destination: Destination directory path
        files: File pattern to copy (optional)
        retries: Number of retries on failure (default: 3)
        wait: Wait time between retries in seconds (default: 10)
        mirror: Use mirror mode (/MIR)
        move: Move files instead of copy (/MOV)
        
    Returns:
        DiagnosticResult with copy results
    """
    diag = Robocopy()
    return await diag.run(
        source=source,
        destination=destination,
        files=files,
        retries=retries,
        wait=wait,
        mirror=mirror,
        move=move,
    )

