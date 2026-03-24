"""
ISO extraction module.

Extracts the Windows PE ISO using 7-Zip.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .config import AppConfig
from .helpers.archiver import extract_archive


def extract_iso(config: AppConfig) -> None:
    """
    Extract the source ISO to the working directory.

    Args:
        config: Application configuration
    """
    extract_dir = Path(config.iso_extract_dir)
    seven_zip = config.seven_zip_path
    source_iso = Path(config.source_iso)

    # Check if extract dir already has files
    if extract_dir.exists() and any(extract_dir.iterdir()):
        print(f"  [WARN] Extract directory '{extract_dir}' is not empty.")
        answer = (
            input("  Re-extract ISO? This will DELETE the existing contents. [y/N] ")
            .strip()
            .lower()
        )

        if answer != "y":
            print("[*] Skipping ISO extraction - using existing files.")
            return

        # Clean extract directory
        shutil.rmtree(extract_dir)

    extract_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Extracting ISO: {source_iso}")
    print(f"    -> {extract_dir}")

    extract_archive(seven_zip, source_iso, extract_dir)

    # Verify boot.wim exists after extraction
    wim_path = extract_dir / config.wim_file
    if not wim_path.exists():
        raise RuntimeError(
            f"boot.wim not found at expected location '{wim_path}' after extraction. "
            "Check WimFile in config.json."
        )

    print(f"[OK] ISO extracted successfully. boot.wim at: {wim_path}")
