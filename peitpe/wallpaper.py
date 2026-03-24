"""
Wallpaper replacement module.

Replaces the WinPE wallpaper files inside the mounted WIM.
Handles file ownership and permission requirements.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .config import AppConfig


def run_command(cmd: list[str]) -> tuple[int, str]:
    """
    Run a command and return exit code and output.

    Args:
        cmd: Command and arguments

    Returns:
        tuple of (exit_code, output)
    """
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="mbcs",
        errors="replace",
    )
    output = result.stdout + result.stderr
    return result.returncode, output


def take_ownership(file_path: Path) -> None:
    """
    Take ownership of a file using takeown command.

    Args:
        file_path: Path to file

    Raises:
        RuntimeError: If takeown fails
    """
    print(f"    Taking ownership of {file_path.name}...")
    exit_code, output = run_command(["takeown", "/F", str(file_path)])

    if exit_code != 0:
        raise RuntimeError(f"takeown failed: {output}")


def grant_permissions(file_path: Path) -> None:
    """
    Grant Administrators full control using icacls command.

    Args:
        file_path: Path to file

    Raises:
        RuntimeError: If icacls fails
    """
    exit_code, output = run_command(
        ["icacls", str(file_path), "/grant", "Administrators:F"]
    )

    if exit_code != 0:
        raise RuntimeError(f"icacls failed: {output}")


def convert_to_jpeg(source: Path, dest: Path, quality: int = 95) -> None:
    """
    Convert an image file to JPEG format.

    Args:
        source: Source image file
        dest: Destination JPEG file
        quality: JPEG quality (1-100)
    """
    from PIL import Image

    img = Image.open(source)
    # Convert to RGB if necessary (PNG might have alpha channel)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")
    img.save(dest, "JPEG", quality=quality)


def replace_wallpaper_file(source: Path, dest: Path, convert: bool = False) -> None:
    """
    Replace a single wallpaper file.

    Args:
        source: Source image file
        dest: Destination wallpaper file
        convert: Whether to convert to JPEG format
    """
    # Take ownership if file exists
    if dest.exists():
        take_ownership(dest)
        grant_permissions(dest)

    # Ensure destination directory exists
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Copy or convert the file
    if convert:
        try:
            convert_to_jpeg(source, dest)
        except ImportError:
            print("    [WARN] Pillow not installed. Copying as-is.")
            shutil.copy2(source, dest)
        except Exception as e:
            print(f"    [WARN] Conversion failed: {e}. Copying as-is.")
            shutil.copy2(source, dest)
    else:
        shutil.copy2(source, dest)

    print(f"    Replaced: {dest.relative_to(dest.parent.parent.parent)}")


def replace_wallpaper(config: AppConfig) -> None:
    """
    Replace the WinPE wallpaper with a custom image.

    Args:
        config: Application configuration
    """
    if config.skip_wallpaper:
        print("[*] Skipping wallpaper update (asset not found).")
        return

    mount_dir = Path(config.mount_dir)

    # Use resolved path if available, otherwise use wallpaper_source
    wallpaper_src = (
        Path(config.resolved_wallpaper_path)
        if config.resolved_wallpaper_path
        else Path(config.wallpaper_source)
    )

    if not wallpaper_src.exists():
        print(f"  [WARN] Wallpaper source not found: {wallpaper_src}. Skipping.")
        return

    print("[*] Replacing wallpaper...")
    print(f"    Source: {wallpaper_src}")

    # Wallpaper locations to update (PeitPE.jpg after rebranding)
    wallpaper_locations = [
        mount_dir / "Windows" / "System32" / "winpe.jpg",
        mount_dir / "Windows" / "web" / "wallpaper" / "Windows" / "PeitPE.jpg",
        mount_dir
        / "Program Files"
        / "WinXShell"
        / "wallpaper.jpg",  # Desktop wallpaper
    ]

    src_ext = wallpaper_src.suffix.lower()
    needs_convert = src_ext == ".png"

    for dest in wallpaper_locations:
        try:
            replace_wallpaper_file(wallpaper_src, dest, convert=needs_convert)
        except Exception as e:
            print(f"    [FAIL] Failed to replace {dest.name}: {e}")

    print("[OK] Wallpaper replaced.")
