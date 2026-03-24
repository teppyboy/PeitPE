"""
Prerequisites checking and tool discovery.

Validates that required tools (oscdimg, 7-Zip, DISM) are available
and verifies source files exist.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import winreg
from pathlib import Path
from typing import Optional

from .config import AppConfig


def is_admin() -> bool:
    """Check if the current process is running as Administrator."""
    if platform.system() != "Windows":
        return os.geteuid() == 0

    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def find_oscdimg(config_path: str = "") -> Optional[str]:
    """Find oscdimg.exe through multiple discovery methods."""

    # 1. Check config path
    if config_path and Path(config_path).exists():
        return config_path

    # 2. Check Windows Registry
    reg_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows Kits\Installed Roots"),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Microsoft\Windows Kits\Installed Roots",
        ),
    ]

    for hive, key_path in reg_paths:
        try:
            with winreg.OpenKey(hive, key_path) as key:
                kits_root = winreg.QueryValueEx(key, "KitsRoot10")[0]
                candidate = (
                    Path(kits_root)
                    / "Assessment and Deployment Kit"
                    / "Deployment Tools"
                    / "amd64"
                    / "Oscdimg"
                    / "oscdimg.exe"
                )
                if candidate.exists():
                    return str(candidate)
        except (OSError, FileNotFoundError, KeyError):
            continue

    # 3. Search fixed drives
    for drive_letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        drive = f"{drive_letter}:\\"
        if not Path(drive).exists():
            continue

        for base in ["Program Files (x86)", "Program Files"]:
            candidate = (
                Path(drive)
                / base
                / "Windows Kits"
                / "10"
                / "Assessment and Deployment Kit"
                / "Deployment Tools"
                / "amd64"
                / "Oscdimg"
                / "oscdimg.exe"
            )
            if candidate.exists():
                return str(candidate)

    # 4. Check PATH
    found = shutil.which("oscdimg.exe")
    if found:
        return found

    return None


def find_seven_zip(config_path: str = "") -> Optional[str]:
    """Find 7z.exe through multiple discovery methods."""

    # 1. Check config path
    if config_path and Path(config_path).exists():
        return config_path

    # 2. Search fixed drives
    for drive_letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        drive = f"{drive_letter}:\\"
        if not Path(drive).exists():
            continue

        for base in ["Program Files", "Program Files (x86)"]:
            candidate = Path(drive) / base / "7-Zip" / "7z.exe"
            if candidate.exists():
                return str(candidate)

    # 3. Check PATH
    found = shutil.which("7z.exe")
    if found:
        return found

    return None


def find_dism() -> Optional[str]:
    """Find dism.exe."""
    system_root = os.environ.get("SystemRoot", "C:\\Windows")
    dism_path = Path(system_root) / "System32" / "dism.exe"

    if dism_path.exists():
        return str(dism_path)

    # Check PATH
    found = shutil.which("dism.exe")
    if found:
        return found

    return None


def check_source_iso(iso_path: str) -> bool:
    """Check if source ISO exists."""
    return Path(iso_path).exists()


def check_wallpaper(wallpaper_path: str) -> tuple[bool, str]:
    """
    Check if wallpaper file exists.

    Returns:
        tuple[bool, str]: (exists, resolved_path)
    """
    if not wallpaper_path:
        return False, ""

    path = Path(wallpaper_path)
    if path.exists():
        return True, str(path.resolve())

    return False, ""


def create_directories(config: AppConfig) -> None:
    """Create working directories if they don't exist."""
    directories = [
        config.work_dir,
        config.iso_extract_dir,
        config.mount_dir,
        config.download_cache_dir,
    ]

    for dir_path in directories:
        if dir_path:
            path = Path(dir_path)
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                print(f"  [+] Created directory: {dir_path}")


def verify_prerequisites(config: AppConfig) -> None:
    """
    Verify all prerequisites are met.

    Raises:
        RuntimeError: If a prerequisite is not satisfied.
    """
    print("[*] Checking prerequisites...")

    # Must run as Administrator
    if not is_admin():
        raise RuntimeError(
            "This script must be run as Administrator (required for DISM mount operations)."
        )
    print("  [OK] Running as Administrator")

    # DISM availability
    dism_path = find_dism()
    if not dism_path:
        raise RuntimeError("DISM not found. Ensure Windows ADK or DISM is installed.")
    print(f"  [OK] DISM found: {dism_path}")

    # oscdimg - dynamic discovery
    resolved_oscdimg = find_oscdimg(config.oscdimg_path)
    if not resolved_oscdimg:
        raise RuntimeError(
            "oscdimg.exe not found. Install Windows ADK (Deployment Tools feature) "
            "from https://learn.microsoft.com/windows-hardware/get-started/adk-install"
        )
    config.oscdimg_path = resolved_oscdimg
    print(f"  [OK] oscdimg found: {resolved_oscdimg}")

    # 7-Zip - dynamic discovery
    resolved_seven_zip = find_seven_zip(config.seven_zip_path)
    if not resolved_seven_zip:
        raise RuntimeError(
            "7-Zip (7z.exe) not found. Install 7-Zip from https://www.7-zip.org/"
        )
    config.seven_zip_path = resolved_seven_zip
    print(f"  [OK] 7-Zip found: {resolved_seven_zip}")

    # Source ISO exists
    if not check_source_iso(config.source_iso):
        raise RuntimeError(
            f"Source ISO not found: '{config.source_iso}'. "
            "Update SourceISO in config.json."
        )
    print(f"  [OK] Source ISO found: {config.source_iso}")

    # Wallpaper asset exists (if configured)
    if config.wallpaper_source:
        exists, resolved_path = check_wallpaper(config.wallpaper_source)
        if not exists:
            print(
                f"  [WARN] Wallpaper not found at '{config.wallpaper_source}'. "
                "Wallpaper update will be skipped."
            )
            config.skip_wallpaper = True
        else:
            print(f"  [OK] Wallpaper found: {resolved_path}")
            config.resolved_wallpaper_path = resolved_path

    # Create working directories
    create_directories(config)

    print("[OK] All prerequisites satisfied.")
