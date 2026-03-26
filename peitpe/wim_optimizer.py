"""
WIM optimization module.

Re-exports boot.wim with maximum LZX compression to reduce ISO size.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from .config import AppConfig


def compress_wim(config: AppConfig) -> None:
    """
    Compress boot.wim using DISM maximum LZX compression.

    Exports the WIM to a temporary file with maximum compression,
    then replaces the original with the compressed version.

    Args:
        config: Application configuration

    Raises:
        RuntimeError: If DISM export fails
    """
    import subprocess

    wim_path = Path(config.iso_extract_dir) / config.wim_file
    temp_wim = wim_path.with_suffix(".wim.opt")

    if not wim_path.exists():
        raise RuntimeError(f"boot.wim not found at: {wim_path}")

    original_size = wim_path.stat().st_size
    original_mb = original_size / (1024 * 1024)
    print(f"    Source: {wim_path}")
    print(f"    Size  : {original_mb:,.0f} MB")

    # Clean up any leftover temp file
    if temp_wim.exists():
        temp_wim.unlink()

    cmd = [
        "dism",
        "/Export-Image",
        f"/SourceImageFile:{wim_path}",
        f"/SourceIndex:{config.wim_index}",
        f"/DestinationImageFile:{temp_wim}",
        "/Compress:maximum",
    ]

    print("    Compressing (this may take several minutes)...")

    start = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="mbcs",
            errors="replace",
        )
    except FileNotFoundError:
        raise RuntimeError(
            "DISM not found. Ensure you are running as Administrator on Windows."
        )

    elapsed = time.time() - start

    if result.returncode != 0:
        output = result.stdout + result.stderr
        if temp_wim.exists():
            temp_wim.unlink()
        raise RuntimeError(f"DISM export failed (exit {result.returncode}):\n{output}")

    if not temp_wim.exists():
        raise RuntimeError("DISM export completed but output file not found.")

    compressed_size = temp_wim.stat().st_size
    compressed_mb = compressed_size / (1024 * 1024)
    saved_mb = (original_size - compressed_size) / (1024 * 1024)
    saved_pct = (1 - compressed_size / original_size) * 100

    # Replace original with compressed version
    wim_path.unlink()
    temp_wim.rename(wim_path)

    print(f"    Output: {wim_path}")
    print(f"    Size  : {compressed_mb:,.0f} MB")
    print(f"    Saved : {saved_mb:,.0f} MB ({saved_pct:.0f}%)")
    print(f"    Time  : {elapsed:.0f}s")
