"""
Archive extraction utilities.

Wraps 7-Zip command-line tool for archive extraction.
"""

from __future__ import annotations

import subprocess
import shutil
from pathlib import Path
from typing import Optional


def extract_archive(
    seven_zip_path: str,
    archive_path: Path,
    output_dir: Path,
) -> None:
    """
    Extract an archive using 7-Zip.

    Args:
        seven_zip_path: Path to 7z.exe
        archive_path: Path to archive file
        output_dir: Directory to extract to

    Raises:
        RuntimeError: If extraction fails
    """
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        seven_zip_path,
        "x",
        str(archive_path),
        f"-o{output_dir}",
        "-y",  # Assume Yes on all queries
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="mbcs",
        errors="replace",
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"7-Zip extraction failed (exit {result.returncode}):\n{result.stderr}"
        )


def extract_with_subdir(
    seven_zip_path: str,
    archive_path: Path,
    output_dir: Path,
    subdir_pattern: str = "",
) -> Path:
    """
    Extract archive and return path to contents (with optional subdir).

    Args:
        seven_zip_path: Path to 7z.exe
        archive_path: Path to archive file
        output_dir: Base extraction directory
        subdir_pattern: Optional subdirectory pattern (supports wildcards)

    Returns:
        Path to extracted contents

    Raises:
        RuntimeError: If extraction fails or subdir not found
    """
    extract_archive(seven_zip_path, archive_path, output_dir)

    if not subdir_pattern:
        return output_dir

    # Look for matching subdirectory
    matches = list(output_dir.glob(subdir_pattern))
    if matches:
        return matches[0]

    # Check if pattern contains wildcards
    if "*" in subdir_pattern or "?" in subdir_pattern:
        raise RuntimeError(
            f"extractSubDir pattern '{subdir_pattern}' not found inside extracted archive"
        )

    # Try as literal path
    subdir_path = output_dir / subdir_pattern
    if subdir_path.exists():
        return subdir_path

    raise RuntimeError(
        f"extractSubDir '{subdir_pattern}' not found inside extracted archive"
    )


def copy_contents(source_dir: Path, dest_dir: Path) -> None:
    """
    Copy all contents from source to destination directory.

    Args:
        source_dir: Source directory
        dest_dir: Destination directory
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    for item in source_dir.iterdir():
        dest_item = dest_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest_item, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest_item)


def clean_directory(dir_path: Path) -> None:
    """Remove all contents of a directory."""
    if dir_path.exists():
        shutil.rmtree(dir_path)
    dir_path.mkdir(parents=True, exist_ok=True)
