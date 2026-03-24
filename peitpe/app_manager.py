"""
App injection module.

Downloads and injects apps into the ISO directory.
Handles both direct downloads and GitHub releases.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .config import AppConfig, AppDefinition, load_app_definitions, get_enabled_apps
from .helpers.downloader import download_file
from .helpers.github_api import get_download_url
from .helpers.archiver import extract_with_subdir, copy_contents, clean_directory


def download_and_stage(
    app: AppDefinition,
    cache_dir: Path,
    seven_zip_path: str,
) -> Path:
    """
    Download and stage an app for injection.

    Args:
        app: App definition
        cache_dir: Cache directory path
        seven_zip_path: Path to 7z.exe

    Returns:
        Path to staged app directory

    Raises:
        RuntimeError: If download or extraction fails
    """
    app_name = app.name
    url = app.download_url
    app_type = app.type
    sub_dir = app.extract_sub_dir

    # Create staging area
    stage_dir = cache_dir / "staged" / app_name
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True, exist_ok=True)

    # Determine local cache filename
    url_path = url.split("?")[0]
    ext = Path(url_path).suffix
    if not ext:
        ext = f".{app_type}"
    cache_file = cache_dir / f"{app_name}{ext}"

    # Download if not cached
    if not cache_file.exists():
        print(f"    Downloading {app_name}...")
        try:
            download_file(url, cache_file, resume=False)
        except Exception as e:
            raise RuntimeError(f"Download failed for {app_name} from '{url}': {e}")
        print(f"    Downloaded: {cache_file}")
    else:
        print(f"    Using cached: {cache_file}")

    # Extract or copy based on type
    if app_type in ("zip", "7z"):
        print(f"    Extracting {app_name}...")
        extract_temp = cache_dir / f"extract_{app_name}"
        if extract_temp.exists():
            shutil.rmtree(extract_temp)

        source_dir = extract_with_subdir(
            seven_zip_path,
            cache_file,
            extract_temp,
            sub_dir,
        )

        # Copy contents to staging dir
        copy_contents(source_dir, stage_dir)

        # Clean up temp extraction
        shutil.rmtree(extract_temp)

    elif app_type == "exe":
        # Portable exe - just copy directly
        dest_exe = stage_dir / f"{app_name}.exe"
        shutil.copy2(cache_file, dest_exe)

    else:
        raise RuntimeError(f"Unsupported app type '{app_type}' for {app_name}")

    print(f"    Staged at: {stage_dir}")
    return stage_dir


def create_shortcut(
    iso_extract_dir: Path,
    app_name: str,
    target_path: str,
    executable_hint: str,
) -> None:
    """
    Create a shortcut (.lnk) file for an app in the Programs folder.

    Args:
        iso_extract_dir: ISO extract directory
        app_name: Application name
        target_path: Target path relative to Programs (e.g., SystemInformer)
        executable_hint: Executable name to find (e.g., SystemInformer.exe)
    """
    programs_dir = iso_extract_dir / "Programs"

    # Find the executable in the target directory
    app_dir = iso_extract_dir / target_path.lstrip("\\")

    if not app_dir.exists():
        print(f"    [WARN] App directory not found: {app_dir}")
        return

    # Search for the executable
    exe_path = None
    for root, dirs, files in app_dir.walk():
        for file in files:
            if file.lower() == executable_hint.lower():
                exe_path = root / file
                break
        if exe_path:
            break

    if not exe_path:
        print(f"    [WARN] Executable '{executable_hint}' not found in {app_dir}")
        return

    # Create shortcut using PowerShell
    import subprocess

    shortcut_path = programs_dir / f"{app_name}.lnk"
    relative_exe = exe_path.relative_to(iso_extract_dir)

    # Use PowerShell to create the shortcut
    ps_script = f"""
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
    $Shortcut.TargetPath = "Y:\\{relative_exe}"
    $Shortcut.WorkingDirectory = "Y:\\{relative_exe.parent}"
    $Shortcut.Save()
    """

    try:
        subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"    Created shortcut: {shortcut_path.name}")
    except subprocess.CalledProcessError as e:
        print(f"    [WARN] Failed to create shortcut: {e.stderr}")


def inject_to_iso(stage_dir: Path, iso_extract_dir: Path, target_path: str) -> None:
    """
    Inject staged app into the ISO directory.

    Args:
        stage_dir: Source stage directory
        iso_extract_dir: ISO extract directory
        target_path: Target path inside ISO (relative to extract dir)
    """
    # Clean target path (remove leading backslash)
    clean_target = target_path.lstrip("\\")
    iso_target = iso_extract_dir / clean_target

    # Remove existing app folder if present
    if iso_target.exists():
        shutil.rmtree(iso_target)
        print(f"    Removed old version at: {iso_target}")

    # Copy staged contents to ISO
    iso_target.mkdir(parents=True, exist_ok=True)
    copy_contents(stage_dir, iso_target)


def process_apps(
    apps_json: Path,
    iso_extract_dir: str,
    cache_dir: str,
    seven_zip_path: str,
    update_mode: bool = True,
) -> None:
    """
    Process apps from a JSON definition file.

    Args:
        apps_json: Path to apps JSON file
        iso_extract_dir: ISO extract directory
        cache_dir: Download cache directory
        seven_zip_path: Path to 7z.exe
        update_mode: True for updates (replace), False for additions (add new)
    """
    from .helpers.github_api import get_download_url

    apps = load_app_definitions(apps_json)
    enabled = get_enabled_apps(apps)

    if not enabled:
        action = "update" if update_mode else "add"
        print(f"[*] No apps enabled for {action}. Skipping.")
        return

    action = "Updating" if update_mode else "Adding"
    print(f"[*] {action} {len(enabled)} app(s) in ISO...")

    iso_path = Path(iso_extract_dir)
    cache_path = Path(cache_dir)

    for app in enabled:
        print(f"\n  -> {app.name}: {app.description}")

        # Resolve download URL for GitHub-sourced apps
        if app.source == "github":
            url = get_download_url(app.owner, app.repo, app.asset_pattern)
            if not url:
                print(f"  [SKIP] Could not resolve download URL for {app.name}")
                continue
            app.download_url = url

        if not app.download_url:
            print(f"  [SKIP] No downloadUrl for {app.name}. Update apps JSON.")
            continue

        # Download and stage
        try:
            stage_dir = download_and_stage(app, cache_path, seven_zip_path)
        except Exception as e:
            print(f"  [FAIL] {app.name}: {e}")
            continue

        # Inject to ISO
        try:
            inject_to_iso(stage_dir, iso_path, app.target_path)
        except Exception as e:
            print(f"  [FAIL] {app.name}: Injection failed: {e}")
            continue

        # Create shortcut if executable_hint is provided
        if app.executable_hint:
            try:
                create_shortcut(
                    iso_path,
                    app.name,
                    app.target_path,
                    app.executable_hint,
                )
            except Exception as e:
                print(f"  [WARN] Failed to create shortcut: {e}")

        print(f"  [OK] {app.name} -> {app.target_path}")

    action_past = "updates" if update_mode else "additions"
    print(f"\n[OK] App {action_past} complete.")


def process_updates(config: AppConfig) -> None:
    """Process app updates from updates.json."""
    project_root = Path(config.source_iso).parent.parent
    apps_json = project_root / "apps" / "updates.json"

    process_apps(
        apps_json,
        config.iso_extract_dir,
        config.download_cache_dir,
        config.seven_zip_path,
        update_mode=True,
    )


def process_additions(config: AppConfig) -> None:
    """Process new app additions from additions.json."""
    project_root = Path(config.source_iso).parent.parent
    apps_json = project_root / "apps" / "additions.json"

    process_apps(
        apps_json,
        config.iso_extract_dir,
        config.download_cache_dir,
        config.seven_zip_path,
        update_mode=False,
    )
