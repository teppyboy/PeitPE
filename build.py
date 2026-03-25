"""
PeitPE Builder - Main Entry Point

A pure Python tool for modifying Windows PE ISOs.

Usage:
    uv run build.py [options]

Options:
    --skip-download     Skip ISO download
    --skip-extract      Skip ISO extraction
    --skip-apps         Skip app updates and additions
    --skip-rebrand      Skip rebranding from HBCD to PeitPE
    --skip-wallpaper    Skip wallpaper replacement
    --skip-build        Skip final ISO build
    --force-download    Re-download ISO even if it exists
    --config PATH       Path to config.json (default: config.json)
    --help              Show this help message
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path

from peitpe.config import AppConfig, load_config
from peitpe.prerequisites import verify_prerequisites
from peitpe.iso_downloader import download_iso
from peitpe.iso_extractor import extract_iso
from peitpe.wim_manager import mount_wim, unmount_wim
from peitpe.app_manager import (
    process_updates,
    process_additions,
    create_start_menu_shortcuts,
)
from peitpe.rebranding import rebrand
from peitpe.wallpaper import replace_wallpaper
from peitpe.iso_builder import build_iso


# Global config for cleanup
_global_config: AppConfig | None = None
_was_mounted = False


def signal_handler(sig, frame):
    """Handle interrupt signals gracefully."""
    print("\n\n[!] Interrupted by user.")

    if _global_config and _was_mounted:
        print("\n[WARN] WIM may still be mounted. To unmount manually, run:")
        print(f'  dism /Unmount-Image /MountDir:"{_global_config.mount_dir}" /discard')

    sys.exit(1)


def invoke_step(name: str, func, *args, **kwargs):
    """Execute a step with error handling."""
    print(f"\n--- {name} ---")
    try:
        return func(*args, **kwargs)
    except Exception as e:
        print(f"\n[ERROR] Step '{name}' failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    global _global_config, _was_mounted

    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="PeitPE - Windows PE ISO Modifier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run build.py                          # Full build
  uv run build.py --force-download         # Force fresh ISO download
  uv run build.py --skip-download --skip-extract  # Rebuild ISO only
  uv run build.py --skip-apps --skip-wallpaper    # Skip optional steps
        """,
    )
    parser.add_argument(
        "--skip-download", action="store_true", help="Skip ISO download"
    )
    parser.add_argument(
        "--skip-extract", action="store_true", help="Skip ISO extraction"
    )
    parser.add_argument(
        "--skip-apps", action="store_true", help="Skip app updates and additions"
    )
    parser.add_argument(
        "--skip-rebrand",
        action="store_true",
        help="Skip rebranding from HBCD to PeitPE",
    )
    parser.add_argument(
        "--skip-wallpaper", action="store_true", help="Skip wallpaper replacement"
    )
    parser.add_argument(
        "--skip-build", action="store_true", help="Skip final ISO build"
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download ISO even if it exists",
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config.json (default: config.json)",
    )

    args = parser.parse_args()

    start_time = time.time()

    # Print banner
    print("")
    print("=" * 49)
    print("  PeitPE - Windows PE ISO Modifier")
    print("=" * 49)
    print("")

    # Load configuration
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).parent / config_path

    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"[ERROR] Failed to load configuration: {e}")
        sys.exit(1)

    # Apply command-line overrides
    if args.skip_wallpaper:
        config.skip_wallpaper = True

    _global_config = config

    # Step 0: Download ISO
    if not args.skip_download:
        invoke_step(
            "Download ISO",
            download_iso,
            config,
            force=args.force_download,
        )
    else:
        print("\n[*] Skipping ISO download.")

    # Step 1: Prerequisites
    invoke_step("Prerequisites", verify_prerequisites, config)

    # Step 2: Extract ISO
    if not args.skip_extract:
        invoke_step("Extract ISO", extract_iso, config)
    else:
        print("\n[*] Skipping ISO extraction.")

    # Step 3 & 4: Apps (inject into ISO directory, not WIM)
    if not args.skip_apps:
        invoke_step("Update Apps", process_updates, config)
        invoke_step("Add New Apps", process_additions, config)
    else:
        print("\n[*] Skipping app updates and additions.")

    # Step 5: Mount WIM (needed for rebranding, wallpaper, or Start Menu shortcuts)
    need_wim_mount = (
        (not args.skip_wallpaper and not config.skip_wallpaper)
        or not args.skip_rebrand
        or not args.skip_apps
    )

    if need_wim_mount:
        invoke_step("Mount WIM", mount_wim, config)
        _was_mounted = True

        # Create Start Menu shortcuts for injected apps
        if not args.skip_apps:
            invoke_step("Start Menu Shortcuts", create_start_menu_shortcuts, config)

        # Step 6: Rebrand (update boot text and config files)
        if not args.skip_rebrand:
            invoke_step("Rebrand", rebrand, config)
        else:
            print("\n[*] Skipping rebranding.")

        # Step 7: Wallpaper
        if not args.skip_wallpaper and not config.skip_wallpaper:
            invoke_step("Set Wallpaper", replace_wallpaper, config)
        else:
            print("\n[*] Skipping wallpaper update.")

        # Step 8: Unmount WIM
        invoke_step("Unmount WIM", unmount_wim, config)
        _was_mounted = False
    else:
        print("\n[*] Skipping WIM mount/unmount (rebrand and wallpaper skipped).")

    # Step 8: Build ISO
    if not args.skip_build:
        invoke_step("Build ISO", build_iso, config)
    else:
        print("\n[*] Skipping ISO build.")

    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    print("")
    print("=" * 49)
    print(f"  Done in {minutes:02d}:{seconds:02d}!")
    print(f"  Output: {config.output_iso}")
    print("=" * 49)
    print("")


if __name__ == "__main__":
    main()
