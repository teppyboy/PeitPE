"""
WIM mount/unmount operations.

Manages DISM operations for mounting and unmounting boot.wim.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .config import AppConfig


def run_dism(*args: str) -> tuple[int, str]:
    """
    Run a DISM command and return exit code and output.

    Args:
        args: DISM arguments

    Returns:
        tuple of (exit_code, output)
    """
    cmd = ["dism"] + list(args)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="mbcs",
        errors="replace",
    )

    output = result.stdout + result.stderr
    return result.returncode, output


def is_wim_mounted(mount_dir: str) -> bool:
    """Check if a WIM is currently mounted at the given directory."""
    exit_code, output = run_dism("/Get-MountedImageInfo")
    return mount_dir in output


def unmount_wim_discard(mount_dir: str) -> None:
    """Unmount a WIM and discard changes."""
    print("[*] Discarding existing mount...")
    exit_code, output = run_dism(
        "/Unmount-Image",
        f"/MountDir:{mount_dir}",
        "/discard",
    )
    if exit_code != 0:
        print(f"  [WARN] Unmount discard failed: {output}")


def mount_wim(config: AppConfig) -> None:
    """
    Mount boot.wim for modification.

    Args:
        config: Application configuration
    """
    wim_path = Path(config.iso_extract_dir) / config.wim_file
    mount_dir = config.mount_dir
    index = config.wim_index

    # Check if already mounted
    if is_wim_mounted(mount_dir):
        print(f"  [WARN] WIM appears to already be mounted at '{mount_dir}'.")
        answer = input("  Unmount (discard) and re-mount? [y/N] ").strip().lower()

        if answer != "y":
            print("[*] Using existing mounted WIM.")
            return

        unmount_wim_discard(mount_dir)

    # Ensure mount dir is empty
    mount_path = Path(mount_dir)
    if mount_path.exists() and any(mount_path.iterdir()):
        import shutil

        shutil.rmtree(mount_path)
        mount_path.mkdir(parents=True, exist_ok=True)

    print(f"[*] Mounting WIM (index {index})...")
    print(f"    WIM : {wim_path}")
    print(f"    -> {mount_dir}")

    exit_code, output = run_dism(
        "/Mount-Image",
        f"/ImageFile:{wim_path}",
        f"/index:{index}",
        f"/MountDir:{mount_dir}",
    )

    if exit_code != 0:
        raise RuntimeError(f"DISM mount failed (exit {exit_code}):\n{output}")

    print(f"[OK] WIM mounted at: {mount_dir}")


def unmount_wim(config: AppConfig, commit: bool = True) -> None:
    """
    Unmount boot.wim and optionally commit changes.

    Args:
        config: Application configuration
        commit: Whether to commit changes (True) or discard (False)
    """
    mount_dir = config.mount_dir

    print("[*] Unmounting WIM and committing changes...")
    print("    This may take several minutes.")

    action = "/commit" if commit else "/discard"
    exit_code, output = run_dism(
        "/Unmount-Image",
        f"/MountDir:{mount_dir}",
        action,
    )

    if exit_code != 0:
        print(f"  [ERROR] DISM unmount failed (exit {exit_code}):\n{output}")
        print("")
        print("  To recover, try one of:")
        print(f'    dism /Unmount-Image /MountDir:"{mount_dir}" /discard')
        print("    dism /Cleanup-Wim")
        raise RuntimeError("Unmount failed")

    print("[OK] WIM unmounted and changes committed.")
