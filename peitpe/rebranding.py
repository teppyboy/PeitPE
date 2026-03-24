"""
Rebranding module.

Updates boot text, configuration files, and branding from HBCD PE to PeitPE.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .config import AppConfig


def update_pecmd_ini(mount_dir: Path) -> None:
    """
    Update pecmd.ini to change boot text and wallpaper references.

    Args:
        mount_dir: WIM mount directory
    """
    pecmd_ini = mount_dir / "Windows" / "System32" / "pecmd.ini"

    if not pecmd_ini.exists():
        print(f"    [WARN] pecmd.ini not found at {pecmd_ini}")
        return

    # Read file with mbcs encoding (Windows encoding)
    with open(pecmd_ini, "r", encoding="mbcs", errors="replace") as f:
        content = f.read()

    # Replace references
    replacements = [
        ("Initializing Hiren's BootCD PE...", "Initializing PeitPE..."),
        ("HBCD_PE.jpg", "PeitPE.jpg"),  # Wallpaper filename
        ("HBCD_PE.ini", "PeitPE.ini"),  # Config file reference
        ("Hiren's BootCD PE", "PeitPE"),
    ]

    modified = False
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            modified = True
            print(f"    Replaced: '{old}' -> '{new}'")

    if modified:
        # Backup original
        backup = pecmd_ini.with_suffix(".ini.bak")
        if not backup.exists():
            shutil.copy2(pecmd_ini, backup)

        # Write updated content
        with open(pecmd_ini, "w", encoding="mbcs", errors="replace") as f:
            f.write(content)

        print(f"    Updated: {pecmd_ini.relative_to(mount_dir)}")


def update_pecmdadmin_ini(mount_dir: Path) -> None:
    """
    Update PecmdAdmin.ini to change wallpaper reference.

    Args:
        mount_dir: WIM mount directory
    """
    ini_path = mount_dir / "Windows" / "System32" / "PecmdAdmin.ini"

    if not ini_path.exists():
        print(f"    [WARN] PecmdAdmin.ini not found at {ini_path}")
        return

    with open(ini_path, "r", encoding="mbcs", errors="replace") as f:
        content = f.read()

    if "HBCD_PE.jpg" in content:
        content = content.replace("HBCD_PE.jpg", "PeitPE.jpg")

        backup = ini_path.with_suffix(".ini.bak")
        if not backup.exists():
            shutil.copy2(ini_path, backup)

        with open(ini_path, "w", encoding="mbcs", errors="replace") as f:
            f.write(content)

        print(f"    Updated: {ini_path.relative_to(mount_dir)}")


def rename_wallpaper_file(mount_dir: Path) -> None:
    """
    Rename HBCD_PE.jpg to PeitPE.jpg.

    Args:
        mount_dir: WIM mount directory
    """
    old_path = mount_dir / "Windows" / "web" / "wallpaper" / "Windows" / "HBCD_PE.jpg"
    new_path = mount_dir / "Windows" / "web" / "wallpaper" / "Windows" / "PeitPE.jpg"

    if old_path.exists():
        if new_path.exists():
            new_path.unlink()
        old_path.rename(new_path)
        print(f"    Renamed: HBCD_PE.jpg -> PeitPE.jpg")


def set_computer_name(mount_dir: Path) -> None:
    """
    Set computer name to PEITPE by adding wpeutil command to pecmd.ini.

    Args:
        mount_dir: WIM mount directory
    """
    pecmd_ini = mount_dir / "Windows" / "System32" / "pecmd.ini"

    if not pecmd_ini.exists():
        return

    with open(pecmd_ini, "r", encoding="mbcs", errors="replace") as f:
        content = f.read()

    # Add computer name command at the beginning of OSInit subroutine
    if "wpeutil SetComputerName" not in content:
        # Find the OSInit subroutine and add the command after DISP line
        if "DISP W1280 H720 B32 F60" in content:
            content = content.replace(
                "DISP W1280 H720 B32 F60",
                "DISP W1280 H720 B32 F60\n\tEXEC !=wpeutil SetComputerName PEITPE",
            )

            with open(pecmd_ini, "w", encoding="mbcs", errors="replace") as f:
                f.write(content)

            print(f"    Added: SetComputerName PEITPE to pecmd.ini")


def update_y_drive_checker(mount_dir: Path) -> None:
    """
    Update Y_Drive_Checker.bat to use PeitPE.ini instead of HBCD_PE.ini.

    Args:
        mount_dir: WIM mount directory
    """
    bat_path = mount_dir / "Program Files" / "Y_Drive_Checker.bat"

    if not bat_path.exists():
        return

    with open(bat_path, "r", encoding="mbcs", errors="replace") as f:
        content = f.read()

    if "HBCD_PE.ini" in content:
        content = content.replace("HBCD_PE.ini", "PeitPE.ini")

        with open(bat_path, "w", encoding="mbcs", errors="replace") as f:
            f.write(content)

        print(f"    Updated: Y_Drive_Checker.bat")


def update_iso_files(iso_extract_dir: Path) -> None:
    """
    Update files in the ISO extract directory.

    Args:
        iso_extract_dir: ISO extract directory
    """
    # Update Version.txt
    version_txt = iso_extract_dir / "Version.txt"
    if version_txt.exists():
        with open(version_txt, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if "Hiren" in content:
            content = content.replace("Hiren's BootCD PE v1.0.8", "PeitPE v1.0.0")
            content = content.replace(
                "https://www.hirensbootcd.org/", "https://github.com/peitpe"
            )
            content = content.replace("info@hirensbootcd.org", "")

            with open(version_txt, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"    Updated: Version.txt")

    # Rename HBCD_PE.ini to PeitPE.ini
    old_ini = iso_extract_dir / "HBCD_PE.ini"
    new_ini = iso_extract_dir / "PeitPE.ini"

    if old_ini.exists() and not new_ini.exists():
        shutil.copy2(old_ini, new_ini)
        print(f"    Created: PeitPE.ini (copy of HBCD_PE.ini)")


def rebrand(config: AppConfig) -> None:
    """
    Perform all rebranding operations.

    Args:
        config: Application configuration
    """
    print("[*] Rebranding HBCD PE to PeitPE...")

    mount_dir = Path(config.mount_dir)
    iso_extract_dir = Path(config.iso_extract_dir)

    # Update WIM files (boot text and config)
    print("  Updating WIM files:")
    update_pecmd_ini(mount_dir)
    update_pecmdadmin_ini(mount_dir)
    rename_wallpaper_file(mount_dir)
    set_computer_name(mount_dir)
    update_y_drive_checker(mount_dir)

    # Update ISO files
    print("  Updating ISO files:")
    update_iso_files(iso_extract_dir)

    print("[OK] Rebranding complete.")
