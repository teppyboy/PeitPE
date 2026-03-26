"""
UPX compression module for portable applications.

Compresses standalone .exe files in the ISO Programs directory.
NEVER touches system files, drivers, boot files, or WIM contents.
"""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

from .config import AppConfig
from .helpers.downloader import download_file

UPX_VERSION = "5.1.1"
UPX_DOWNLOAD_URL = (
    f"https://github.com/upx/upx/releases/download/"
    f"v{UPX_VERSION}/upx-{UPX_VERSION}-win64.zip"
)

# Executables that must NEVER be packed (boot-critical, driver loaders, etc.)
NEVER_PACK_EXES: set[str] = {
    # Boot configuration / sector tools
    "bcdedit.exe",
    "bcdboot.exe",
    "bootsect.exe",
    "booticex64.exe",
    "booticex86.exe",
    # WIM hosting
    "wimhost.exe",
    # Driver loaders
    "loaddrv.exe",
    "loaddrv_x64.exe",
    "loaddrv_x86.exe",
    "pedrv.exe",
    "pedrv64.exe",
    "adddrivers.exe",
    # Sysinternals kernel tools
    "ctrl2cap.exe",
    "notmyfault.exe",
    "notmyfault64.exe",
    "notmyfaultc64.exe",
}

# Files already known to be UPX-packed (re-packing will fail)
ALREADY_PACKED: set[str] = {
    "gpu-z.exe",
    "hwinfo64.exe",
    "rufus-4.4.exe",
    "snapshot64.exe",
    "chkdsk.exe",
    "unstopcpy.exe",
    # Renamed variants
    "hwinfo32.exe",
    "hwinfo.exe",
}

# .NET assembly indicators — large managed executables that break if UPX-packed
DOTNET_EXES: set[str] = {
    "reflect.exe",
    "diskrestore.exe",
    "redeploy.exe",
    "stinger64.exe",
    "treesizefree.exe",
    "linuxreader.exe",
    "linuxreader64.exe",
    "diskgenius.exe",
    "winscp.exe",
    "backupper.exe",
    "partassist.exe",
    "sumatrapdf-3.5.2-64.exe",
    "textmaker.exe",
    "planmaker.exe",
    "presentations.exe",
    "esetonlinescanner.exe",
    "wiztree64.exe",
    "wiztree.exe",
    "gpu-z.exe",
    "hwinfo64.exe",
    "recuva64.exe",
    "speccy64.exe",
    "veracrypt.exe",
    "veracrypt-x64.exe",
    "veracrypt-arm64.exe",
    "veracrypt format.exe",
    "veracrypt format-x64.exe",
    "veracrypt format-arm64.exe",
    "veracryptexpander.exe",
    "veracryptexpander-x64.exe",
    "veracryptexpander-arm64.exe",
    "winmergeu.exe",
    "showkeyplus.exe",
    # Installer-like / SFX
    "sumatrapdf-3.5.2-64.exe",
    "sfxhead.sfx",
}

# Combined skip set for fast lookup
_ALL_SKIP: set[str] = NEVER_PACK_EXES | ALREADY_PACKED | DOTNET_EXES


def _is_safe_exe(filepath: Path) -> bool:
    """Check if an .exe file is safe to UPX pack."""
    name_lower = filepath.name.lower()

    # Skip known unsafe/broken/already-packed files
    if name_lower in _ALL_SKIP:
        return False

    # Skip very small stubs (< 10 KB) — not worth compressing
    try:
        if filepath.stat().st_size < 10_240:
            return False
    except OSError:
        return False

    return True


def find_upx() -> str | None:
    """Find UPX executable on the system."""
    # 1. Check PATH
    found = shutil.which("upx.exe")
    if found:
        return found

    # 2. Check common install locations
    candidates = [
        Path("C:/Program Files/UPX/upx.exe"),
        Path("C:/Program Files (x86)/UPX/upx.exe"),
        Path.home() / "scoop" / "apps" / "upx" / "current" / "upx.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)

    return None


def download_upx(cache_dir: Path) -> str:
    """
    Download UPX from GitHub releases and extract upx.exe.

    Args:
        cache_dir: Directory to store the downloaded tool.

    Returns:
        Path to the extracted upx.exe.

    Raises:
        RuntimeError: If download or extraction fails.
    """
    tools_dir = cache_dir / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    upx_path = tools_dir / "upx.exe"

    if upx_path.exists():
        print(f"    [OK] Using cached UPX: {upx_path}")
        return str(upx_path)

    zip_path = tools_dir / f"upx-{UPX_VERSION}-win64.zip"

    print(f"    [*] Downloading UPX v{UPX_VERSION}...")
    download_file(UPX_DOWNLOAD_URL, zip_path, resume=False)

    print("    [*] Extracting upx.exe...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        # Find upx.exe inside the zip (may be in a subdirectory)
        for name in zf.namelist():
            if name.lower().endswith("upx.exe"):
                # Extract to tools_dir directly
                with zf.open(name) as src, open(upx_path, "wb") as dst:
                    dst.write(src.read())
                break
        else:
            raise RuntimeError("upx.exe not found inside downloaded archive")

    # Clean up zip
    zip_path.unlink(missing_ok=True)

    print(f"    [OK] UPX ready: {upx_path}")
    return str(upx_path)


def ensure_upx(config: AppConfig) -> str:
    """
    Ensure UPX is available, downloading if necessary.

    Returns:
        Path to upx.exe.

    Raises:
        RuntimeError: If UPX cannot be obtained.
    """
    # Try system first
    found = find_upx()
    if found:
        return found

    # Auto-download into cache
    cache_dir = Path(config.download_cache_dir)
    return download_upx(cache_dir)


def _pack_file(upx_path: str, filepath: Path, timeout: int = 300) -> bool:
    """
    Pack a single file with UPX.

    Returns True if packing succeeded (file was actually compressed).
    """
    original_size = filepath.stat().st_size

    cmd = [upx_path, "--best", "-q", str(filepath)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="mbcs",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return False

    # UPX returns 0 on success, 1 on error, 2 on warning
    if result.returncode > 1:
        return False

    # Verify the file actually shrank (some files don't compress well)
    try:
        new_size = filepath.stat().st_size
    except OSError:
        return False

    if new_size >= original_size:
        # File didn't compress — undo by decompressing
        subprocess.run(
            [upx_path, "-d", "-q", filepath],
            capture_output=True,
            timeout=60,
        )
        return False

    return True


def compress_apps(config: AppConfig) -> None:
    """
    Compress all safe .exe files in the ISO Programs directory with UPX.

    Only touches user-mode portable applications. Never touches:
    - boot-related executables
    - driver loaders
    - .NET assemblies
    - already-packed files
    - .sys, .efi, .dll, or any non-.exe files
    - Anything inside the WIM
    """
    programs_dir = Path(config.iso_extract_dir) / "Programs"

    if not programs_dir.exists():
        print("    [WARN] Programs directory not found. Skipping UPX.")
        return

    # Discover or download UPX
    upx_path = ensure_upx(config)
    print(f"    UPX: {upx_path}")

    # Collect all .exe files
    all_exes = sorted(programs_dir.rglob("*.exe"))
    safe_exes = [f for f in all_exes if _is_safe_exe(f)]

    skipped = len(all_exes) - len(safe_exes)

    print(f"    Found {len(all_exes)} .exe files")
    print(f"    Skipping {skipped} (already packed / .NET / boot-critical)")
    print(f"    Compressing {len(safe_exes)} files...")
    print()

    packed = 0
    failed = 0
    original_total = 0
    compressed_total = 0

    for i, exe_path in enumerate(safe_exes, 1):
        rel_path = exe_path.relative_to(programs_dir)
        size_before = exe_path.stat().st_size
        original_total += size_before

        size_mb = size_before / (1024 * 1024)
        print(
            f"    [{i}/{len(safe_exes)}] {rel_path} ({size_mb:.1f} MB)...",
            end=" ",
            flush=True,
        )

        if _pack_file(upx_path, exe_path):
            size_after = exe_path.stat().st_size
            compressed_total += size_after
            ratio = (1 - size_after / size_before) * 100
            saved = (size_before - size_after) / (1024 * 1024)
            print(f"-{saved:.1f} MB ({ratio:.0f}%)")
            packed += 1
        else:
            compressed_total += size_before
            print("skipped")
            failed += 1

    # Also count skipped files in compressed_total
    for f in all_exes:
        if not _is_safe_exe(f):
            try:
                compressed_total += f.stat().st_size
            except OSError:
                pass

    saved_mb = (original_total - compressed_total) / (1024 * 1024)

    print()
    print(f"    [OK] UPX compression complete")
    print(f"         Packed:  {packed} files")
    print(f"         Failed:  {failed} files")
    print(f"         Skipped: {skipped} files (already packed / .NET / boot-critical)")
    print(f"         Saved:   {saved_mb:.1f} MB from executable compression")
