"""
ISO cleaner module.

Removes duplicate, redundant, and unnecessary applications from the
extracted ISO to reduce size and improve boot/install speed.
"""

from __future__ import annotations

import fnmatch
import shutil
from pathlib import Path

from .config import AppConfig


# =============================================================================
# Tier 1: ISO Programs cleanup
# =============================================================================

# Apps to remove entirely (directories and their .lnk shortcuts)
DUPLICATE_APPS: list[str] = [
    # --- Duplicate partition managers (keep PartitionWizard + DiskGenius) ---
    "AOMEI Partition Assistant",
    "Bootice",
    "DMDE",
    "EaseUS Partition Master",
    "Victoria",
    "Macrorit Partition Expert",
    "Macrorit Partition Extender",
    # --- Duplicate remote desktop (keep AnyDesk) ---
    "Aero Admin",
    # --- Duplicate disk analyzer (keep WizTree) ---
    "TreeSize",
    # --- Duplicate image viewer (keep IrfanView) ---
    "FSViewer",
    # --- Duplicate system info (keep CPU-Z + GPU-Z + SystemInformer) ---
    "HWInfo",
    "Speccy",
    # --- Sysinternals duplicates (already in Sysinternals Suite/) ---
    "Autoruns",
    "TCPView",
    # --- Duplicate data recovery (keep Recuva) ---
    "Puran Data Recovery",
    "Puran File Recovery",
    "ReclaiMe Free RAID Recovery",
    "Unstoppable Copier",
    "Runtime DriveImage XML",
    "Lazesoft Recovery Suite",
    # --- Niche / built-in Windows tools ---
    "AquaKeyTest",
    "CDBurnerXP",
    "Defraggler",
    "WordPad",
    "Change Keyboard Layout",
    "ChkDskGUI",
    # --- Other redundant ---
    "DriveSnapshot",
    "ExamDiff",
    "HDDLLF",
    "HDDScan",
    "Registry Backup",
    "WesternDigital",
    "Windows Login Unlocker",
]

# Subdirectories to strip from remaining apps (languages, docs, unused archs)
LANGUAGE_TRIM: dict[str, list[str]] = {
    "VLC Media Player": ["locale", "languages", "hrtfs", "sdk", "msi"],
    "VeraCrypt": ["Languages", "docs"],
    "AOMEI Backupper": ["lang"],
    "WinMerge": ["Languages", "Docs"],
    "SoftMaker FreeOffice": [
        "pmFree_en.chm",
        "pmFreeManual_en.pdf",
        "prFree_en.chm",
        "prFreeManual_en.pdf",
        "tmFree_en.chm",
        "tmFreeManual_EN.pdf",
        "smash_de.chm",
        "smash_en.chm",
    ],
    "SystemInformer": ["i386", "arm64"],
}

# Documentation file patterns to remove across all apps
DOC_PATTERNS: list[str] = [
    "*.pdf",
    "*.chm",
    "*.url",
    "README*",
    "COPYING*",
    "LICENSE*",
    "EULA*",
    "NOTICE*",
    "CHANGELOG*",
    "Contributors*",
    "license*",
    "lizenz*",
]

# Installer/leftover script patterns
INSTALLER_PATTERNS: list[str] = [
    "install*.bat",
    "uninstall*.bat",
    "Register*.bat",
    "Unregister*.bat",
    "install*.cmd",
    "uninstall*.cmd",
]

# Debug file extensions
DEBUG_EXTENSIONS: list[str] = [".pdb", ".map", ".dbg"]

# Cache/temp file patterns
CACHE_PATTERNS: list[str] = ["*.tmp", "*.bak", "vlc-cache-gen.exe"]

# 32-bit files to remove when 64-bit equivalents exist
UNUSED_ARCH_FILES: dict[str, list[str]] = {
    "VeraCrypt": [
        "VeraCrypt.exe",
        "VeraCrypt Format.exe",
        "VeraCryptExpander.exe",
        "veracrypt.sys",
        "veracrypt.cat",
        "veracrypt.inf",
    ],
    "7-Zip": ["7z.exe", "7z.dll"],
    "CPU-Z": ["cpuz.exe", "cpuz.ini"],
}


def _match_any(name: str, patterns: list[str]) -> bool:
    """Check if a filename matches any of the given glob patterns."""
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def remove_duplicate_apps(iso_extract_dir: Path) -> int:
    """Remove duplicate and unnecessary apps from the ISO Programs directory."""
    programs_dir = iso_extract_dir / "Programs"

    if not programs_dir.exists():
        print("    [WARN] Programs directory not found. Skipping.")
        return 0

    removed = 0
    for app_name in DUPLICATE_APPS:
        app_dir = programs_dir / app_name
        lnk_file = programs_dir / f"{app_name}.lnk"

        if app_dir.exists():
            shutil.rmtree(app_dir)
            print(f"    [-] {app_name}/")
            removed += 1

        if lnk_file.exists():
            lnk_file.unlink()
            print(f"    [-] {app_name}.lnk")
            removed += 1

    return removed


def trim_languages(iso_extract_dir: Path) -> int:
    """Remove unnecessary language files and documentation from specific apps."""
    programs_dir = iso_extract_dir / "Programs"

    if not programs_dir.exists():
        return 0

    removed = 0
    for app_name, items in LANGUAGE_TRIM.items():
        app_dir = programs_dir / app_name

        if not app_dir.exists():
            continue

        for item_name in items:
            item_path = app_dir / item_name

            if item_path.is_dir():
                shutil.rmtree(item_path)
                print(f"    [-] {app_name}/{item_name}/")
                removed += 1
            elif item_path.exists():
                item_path.unlink()
                print(f"    [-] {app_name}/{item_name}")
                removed += 1

    return removed


def trim_documentation(iso_extract_dir: Path) -> int:
    """Remove documentation files (PDFs, CHMs, READMEs, LICENSEs) from all apps."""
    programs_dir = iso_extract_dir / "Programs"

    if not programs_dir.exists():
        return 0

    removed = 0
    for app_dir in programs_dir.iterdir():
        if not app_dir.is_dir():
            continue

        for item in app_dir.rglob("*"):
            if item.is_file() and _match_any(item.name, DOC_PATTERNS):
                try:
                    item.unlink()
                    print(f"    [-] {item.relative_to(programs_dir)}")
                    removed += 1
                except OSError:
                    pass

    return removed


def trim_installer_leftovers(iso_extract_dir: Path) -> int:
    """Remove installer/uninstaller scripts from all apps."""
    programs_dir = iso_extract_dir / "Programs"

    if not programs_dir.exists():
        return 0

    removed = 0
    for app_dir in programs_dir.iterdir():
        if not app_dir.is_dir():
            continue

        for item in app_dir.iterdir():
            if item.is_file() and _match_any(item.name, INSTALLER_PATTERNS):
                try:
                    item.unlink()
                    print(f"    [-] {item.relative_to(programs_dir)}")
                    removed += 1
                except OSError:
                    pass

    return removed


def trim_debug_files(iso_extract_dir: Path) -> int:
    """Remove debug files (.pdb, .map, .dbg) from all apps."""
    programs_dir = iso_extract_dir / "Programs"

    if not programs_dir.exists():
        return 0

    removed = 0
    for ext in DEBUG_EXTENSIONS:
        for item in programs_dir.rglob(f"*{ext}"):
            try:
                item.unlink()
                print(f"    [-] {item.relative_to(programs_dir)}")
                removed += 1
            except OSError:
                pass

    return removed


def trim_cache_files(iso_extract_dir: Path) -> int:
    """Remove temporary and cache files from all apps."""
    programs_dir = iso_extract_dir / "Programs"

    if not programs_dir.exists():
        return 0

    removed = 0
    for app_dir in programs_dir.iterdir():
        if not app_dir.is_dir():
            continue

        for item in app_dir.iterdir():
            if item.is_file() and _match_any(item.name, CACHE_PATTERNS):
                try:
                    item.unlink()
                    print(f"    [-] {item.relative_to(programs_dir)}")
                    removed += 1
                except OSError:
                    pass

    return removed


def trim_unused_architectures(iso_extract_dir: Path) -> int:
    """Remove 32-bit executables when 64-bit equivalents exist."""
    programs_dir = iso_extract_dir / "Programs"

    if not programs_dir.exists():
        return 0

    removed = 0
    for app_name, files in UNUSED_ARCH_FILES.items():
        app_dir = programs_dir / app_name

        if not app_dir.exists():
            continue

        for filename in files:
            # Only remove if a 64-bit variant exists
            x64_name = filename.replace(".exe", "-x64.exe")
            x64_path = app_dir / x64_name
            item_path = app_dir / filename

            if item_path.exists() and x64_path.exists():
                try:
                    item_path.unlink()
                    print(f"    [-] {app_name}/{filename} (x64 exists)")
                    removed += 1
                except OSError:
                    pass

    return removed


def clean_iso(config: AppConfig) -> None:
    """
    Clean the extracted ISO by removing duplicate apps, languages,
    documentation, debug files, and other unnecessary files.

    Args:
        config: Application configuration
    """
    iso_extract_dir = Path(config.iso_extract_dir)

    total = 0

    print("[*] Removing duplicate applications...")
    n = remove_duplicate_apps(iso_extract_dir)
    print(f"    Removed {n} items")
    total += n

    print("[*] Trimming language files...")
    n = trim_languages(iso_extract_dir)
    print(f"    Removed {n} items")
    total += n

    print("[*] Trimming documentation files...")
    n = trim_documentation(iso_extract_dir)
    print(f"    Removed {n} items")
    total += n

    print("[*] Trimming installer leftovers...")
    n = trim_installer_leftovers(iso_extract_dir)
    print(f"    Removed {n} items")
    total += n

    print("[*] Trimming debug files...")
    n = trim_debug_files(iso_extract_dir)
    print(f"    Removed {n} items")
    total += n

    print("[*] Trimming cache/temp files...")
    n = trim_cache_files(iso_extract_dir)
    print(f"    Removed {n} items")
    total += n

    print("[*] Trimming unused architectures...")
    n = trim_unused_architectures(iso_extract_dir)
    print(f"    Removed {n} items")
    total += n

    print(f"[OK] ISO cleanup complete. {total} items removed.")


# =============================================================================
# Tier 2: WIM cleanup (runs while WIM is mounted)
# =============================================================================

# Log file patterns inside the WIM
WIM_LOG_PATTERNS: list[Path] = [
    Path("Windows") / "INF",
    Path("Windows") / "Logs",
    Path("Windows") / "Microsoft.NET" / "Framework" / "v4.0.30319" / "ngen.log",
    Path("Windows") / "Microsoft.NET" / "Framework64" / "v4.0.30319" / "ngen.log",
]

# Font files to remove from WIM
WIM_FONT_REMOVE: list[str] = [
    # Emoji
    "seguiemj.ttf",
]

# Duplicate apps to remove from WIM's Program Files
WIM_DUPLICATE_APPS: list[str] = [
    # Duplicate browser (keep Chrome)
    "Mozilla Firefox",
    # Duplicate image viewer (keep IrfanView from ISO Programs)
    "FSViewer",
    # Duplicate/redundant tools
    "HDDScan",
    "Lazesoft Recovery Suite",
    "Macrorit Partition Expert",
    "Macrorit Partition Extender",
    "Victoria",
]


def remove_wim_apps(mount_dir: Path) -> int:
    """Remove duplicate applications from the WIM's Program Files directory."""
    program_files = mount_dir / "Program Files"

    if not program_files.exists():
        return 0

    removed = 0
    for app_name in WIM_DUPLICATE_APPS:
        app_dir = program_files / app_name

        if app_dir.exists():
            try:
                shutil.rmtree(app_dir)
                print(f"    [-] Program Files/{app_name}/")
                removed += 1
            except OSError as e:
                print(f"    [WARN] Failed to remove {app_name}: {e}")

    return removed


def trim_wim_logs(mount_dir: Path) -> int:
    """Remove log files from the mounted WIM."""
    if not mount_dir.exists():
        return 0

    removed = 0

    # Remove setupapi*.log files from INF directory
    inf_dir = mount_dir / "Windows" / "INF"
    if inf_dir.exists():
        for item in inf_dir.glob("setupapi*.log"):
            try:
                item.unlink()
                print(f"    [-] {item.relative_to(mount_dir)}")
                removed += 1
            except OSError:
                pass

    # Remove DISM logs
    logs_dir = mount_dir / "Windows" / "Logs" / "DISM"
    if logs_dir.exists():
        for item in logs_dir.glob("*.log"):
            try:
                item.unlink()
                print(f"    [-] {item.relative_to(mount_dir)}")
                removed += 1
            except OSError:
                pass

    # Remove ngen logs
    for ngen_log in [
        mount_dir
        / "Windows"
        / "Microsoft.NET"
        / "Framework"
        / "v4.0.30319"
        / "ngen.log",
        mount_dir
        / "Windows"
        / "Microsoft.NET"
        / "Framework64"
        / "v4.0.30319"
        / "ngen.log",
    ]:
        if ngen_log.exists():
            try:
                ngen_log.unlink()
                print(f"    [-] {ngen_log.relative_to(mount_dir)}")
                removed += 1
            except OSError:
                pass

    return removed


def trim_wim_fonts(mount_dir: Path) -> int:
    """Remove unnecessary fonts from the mounted WIM."""
    fonts_dir = mount_dir / "Windows" / "Fonts"

    if not fonts_dir.exists():
        return 0

    removed = 0

    # Remove legacy .fon files (DOS-era bitmap fonts)
    for item in fonts_dir.glob("*.fon"):
        try:
            item.unlink()
            removed += 1
        except OSError:
            pass
    if removed:
        print(f"    [-] Removed {removed} legacy .fon fonts")

    # Remove specific large unnecessary fonts
    for font_name in WIM_FONT_REMOVE:
        font_path = fonts_dir / font_name
        if font_path.exists():
            try:
                font_path.unlink()
                print(f"    [-] Windows/Fonts/{font_name}")
                removed += 1
            except OSError:
                pass

    return removed


def trim_duplicate_firmware(mount_dir: Path) -> int:
    """Remove duplicate firmware files from the WIM."""
    removed = 0

    # Check for duplicate firmware (DriverStore copy vs Firmware directory)
    fw_store = mount_dir / "Windows" / "System32" / "DriverStore" / "FileRepository"
    fw_dir = mount_dir / "Windows" / "Firmware"

    if fw_store.exists() and fw_dir.exists():
        # Find firmware files in DriverStore that also exist in Firmware dir
        for item in fw_store.rglob("*.flz"):
            name = item.name
            if (fw_dir / name).exists():
                try:
                    item.unlink()
                    print(f"    [-] {item.relative_to(mount_dir)} (duplicate)")
                    removed += 1
                except OSError:
                    pass

    return removed


def clean_wim(config: AppConfig) -> None:
    """
    Clean the mounted WIM by removing duplicate apps, logs,
    unnecessary fonts, and duplicate firmware.

    Args:
        config: Application configuration
    """
    mount_dir = Path(config.mount_dir)

    if not mount_dir.exists():
        print("    [WARN] WIM mount directory not found. Skipping.")
        return

    total = 0

    print("[*] Removing duplicate apps from WIM Program Files...")
    n = remove_wim_apps(mount_dir)
    print(f"    Removed {n} items")
    total += n

    print("[*] Trimming WIM log files...")
    n = trim_wim_logs(mount_dir)
    print(f"    Removed {n} items")
    total += n

    print("[*] Trimming WIM fonts...")
    n = trim_wim_fonts(mount_dir)
    print(f"    Removed {n} items")
    total += n

    print("[*] Trimming duplicate firmware...")
    n = trim_duplicate_firmware(mount_dir)
    print(f"    Removed {n} items")
    total += n

    print(f"[OK] WIM cleanup complete. {total} items removed.")
