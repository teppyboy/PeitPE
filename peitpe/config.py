"""
Configuration management module.

Handles loading and validation of config.json, updates.json, and additions.json.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AppConfig:
    """Application configuration loaded from config.json."""

    source_iso: str = ""
    work_dir: str = ""
    iso_extract_dir: str = ""
    mount_dir: str = ""
    output_iso: str = ""
    wim_index: int = 1
    wim_file: str = ""
    wallpaper_source: str = ""
    oscdimg_path: str = ""
    seven_zip_path: str = ""
    download_cache_dir: str = ""

    # Derived/resolved fields
    resolved_wallpaper_path: str = ""
    skip_wallpaper: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        """Create AppConfig from a dictionary (loaded from JSON)."""
        return cls(
            source_iso=data.get("source_iso", ""),
            work_dir=data.get("work_dir", ""),
            iso_extract_dir=data.get("iso_extract_dir", ""),
            mount_dir=data.get("mount_dir", ""),
            output_iso=data.get("output_iso", ""),
            wim_index=data.get("wim_index", 1),
            wim_file=data.get("wim_file", ""),
            wallpaper_source=data.get("wallpaper_source", ""),
            oscdimg_path=data.get("oscdimg_path", ""),
            seven_zip_path=data.get("seven_zip_path", ""),
            download_cache_dir=data.get("download_cache_dir", ""),
        )

    def resolve_paths(self, project_root: Path) -> None:
        """Resolve all relative paths against project root."""
        path_fields = [
            "source_iso",
            "work_dir",
            "iso_extract_dir",
            "mount_dir",
            "output_iso",
            "download_cache_dir",
            "wallpaper_source",
        ]

        for field_name in path_fields:
            value = getattr(self, field_name)
            if value and not Path(value).is_absolute():
                resolved = (project_root / value).resolve()
                setattr(self, field_name, str(resolved))


@dataclass
class AppDefinition:
    """Definition of an app to inject into the WIM."""

    name: str
    description: str
    enabled: bool = True
    source: str = "direct"  # "direct" or "github"
    download_url: str = ""
    type: str = ""  # "zip", "7z", "exe", "msi"
    extract_sub_dir: str = ""
    target_path: str = ""
    executable_hint: str = ""
    note: str = ""

    # GitHub-specific fields
    owner: str = ""
    repo: str = ""
    asset_pattern: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppDefinition:
        """Create AppDefinition from a dictionary (loaded from JSON)."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            source=data.get("source", "direct"),
            download_url=data.get("download_url", ""),
            type=data.get("type", ""),
            extract_sub_dir=data.get("extract_sub_dir", ""),
            target_path=data.get("target_path", ""),
            executable_hint=data.get("executable_hint", ""),
            note=data.get("note", ""),
            owner=data.get("owner", ""),
            repo=data.get("repo", ""),
            asset_pattern=data.get("asset_pattern", ""),
        )


def load_config(config_path: Path) -> AppConfig:
    """Load configuration from config.json file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    config = AppConfig.from_dict(data)
    config.resolve_paths(config_path.parent)

    return config


def load_app_definitions(json_path: Path) -> list[AppDefinition]:
    """Load app definitions from a JSON file (updates.json or additions.json)."""
    if not json_path.exists():
        raise FileNotFoundError(f"App definitions file not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    apps = data.get("apps", [])
    return [AppDefinition.from_dict(app) for app in apps]


def get_enabled_apps(apps: list[AppDefinition]) -> list[AppDefinition]:
    """Filter apps to only enabled ones."""
    return [app for app in apps if app.enabled]
