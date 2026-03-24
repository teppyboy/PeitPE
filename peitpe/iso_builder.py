"""
ISO building module.

Rebuilds the bootable ISO from the modified extracted ISO directory
using oscdimg.
"""

from __future__ import annotations

import subprocess
from enum import Enum
from pathlib import Path

from .config import AppConfig


class BootMode(Enum):
    """Boot mode for ISO building."""

    DUAL = "dual"  # BIOS + UEFI
    BIOS = "bios"  # BIOS only
    UEFI = "uefi"  # UEFI only
    NONE = "none"  # No boot files


def locate_boot_files(source_dir: Path) -> tuple[Path | None, Path | None]:
    """
    Locate BIOS and UEFI boot files.

    Args:
        source_dir: Extracted ISO directory

    Returns:
        tuple of (etfsboot_path, efisys_path) - either may be None
    """
    etfsboot = source_dir / "boot" / "etfsboot.com"
    efisys = source_dir / "efi" / "microsoft" / "boot" / "efisys.bin"

    etfsboot = etfsboot if etfsboot.exists() else None
    efisys = efisys if efisys.exists() else None

    return etfsboot, efisys


def determine_boot_mode(etfsboot: Path | None, efisys: Path | None) -> BootMode:
    """Determine boot mode based on available boot files."""
    if etfsboot and efisys:
        return BootMode.DUAL
    elif etfsboot:
        return BootMode.BIOS
    elif efisys:
        return BootMode.UEFI
    else:
        return BootMode.NONE


def build_iso_args(
    oscdimg_path: str,
    source_dir: Path,
    output_iso: Path,
    boot_mode: BootMode,
    etfsboot: Path | None = None,
    efisys: Path | None = None,
) -> list[str]:
    """
    Build oscdimg command arguments.

    Args:
        oscdimg_path: Path to oscdimg.exe
        source_dir: Source directory
        output_iso: Output ISO path
        boot_mode: Boot mode
        etfsboot: BIOS boot file path
        efisys: UEFI boot file path

    Returns:
        Command arguments list
    """
    args = [oscdimg_path, "-m", "-o", "-u2"]

    if boot_mode == BootMode.DUAL:
        args.append("-udfver102")
        boot_data = f"2#p0,e,b{etfsboot}#pEF,e,b{efisys}"
        args.append(f"-bootdata:{boot_data}")

    elif boot_mode == BootMode.BIOS:
        args.append(f"-b{etfsboot}")

    elif boot_mode == BootMode.UEFI:
        args.extend(["-udfver102", "-pEF"])
        args.append(f"-b{efisys}")

    args.extend([str(source_dir), str(output_iso)])

    return args


def build_iso(config: AppConfig) -> None:
    """
    Build bootable ISO using oscdimg.

    Args:
        config: Application configuration
    """
    oscdimg = config.oscdimg_path
    source_dir = Path(config.iso_extract_dir)
    output_iso = Path(config.output_iso)

    # Ensure output directory exists
    output_dir = output_iso.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Locate boot files
    etfsboot, efisys = locate_boot_files(source_dir)
    boot_mode = determine_boot_mode(etfsboot, efisys)

    print("[*] Building ISO...")
    print(f"    Source : {source_dir}")
    print(f"    Output : {output_iso}")
    print(f"    BIOS   : {'Yes' if etfsboot else 'No - etfsboot.com not found'}")
    print(f"    UEFI   : {'Yes' if efisys else 'No - efisys.bin not found'}")

    if boot_mode == BootMode.NONE:
        raise RuntimeError(
            "Neither etfsboot.com nor efisys.bin found in the extracted ISO. "
            "Cannot create a bootable ISO."
        )

    # Build arguments
    args = build_iso_args(
        oscdimg,
        source_dir,
        output_iso,
        boot_mode,
        etfsboot,
        efisys,
    )

    mode_names = {
        BootMode.DUAL: "Dual-boot (BIOS + UEFI)",
        BootMode.BIOS: "BIOS only",
        BootMode.UEFI: "UEFI only",
    }
    print(f"    Mode   : {mode_names[boot_mode]}")

    # Execute oscdimg
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="mbcs",
        errors="replace",
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError(
            f"oscdimg failed (exit {result.returncode}). See output above."
        )

    # Get output file size
    iso_size = output_iso.stat().st_size
    iso_size_mb = iso_size / (1024 * 1024)

    print(f"[OK] ISO built: {output_iso} ({iso_size_mb:,.0f} MB)")
