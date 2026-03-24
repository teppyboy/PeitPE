"""
GitHub API client for fetching release information.

Used to get latest release assets for GitHub-hosted apps.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import requests


USER_AGENT = "PeitPE-Builder/1.0"


@dataclass
class ReleaseAsset:
    """Represents a GitHub release asset."""

    name: str
    size: int
    download_url: str


@dataclass
class ReleaseInfo:
    """Represents a GitHub release."""

    tag_name: str
    name: str
    assets: list[ReleaseAsset]


def get_latest_release(owner: str, repo: str) -> Optional[ReleaseInfo]:
    """
    Fetch the latest release from GitHub API.

    Args:
        owner: Repository owner
        repo: Repository name

    Returns:
        ReleaseInfo if successful, None if failed
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        assets = []
        for asset in data.get("assets", []):
            assets.append(
                ReleaseAsset(
                    name=asset.get("name", ""),
                    size=asset.get("size", 0),
                    download_url=asset.get("browser_download_url", ""),
                )
            )

        return ReleaseInfo(
            tag_name=data.get("tag_name", ""),
            name=data.get("name", ""),
            assets=assets,
        )

    except requests.RequestException as e:
        print(f"  [WARN] Failed to query GitHub API for {owner}/{repo}: {e}")
        return None


def find_matching_asset(release: ReleaseInfo, pattern: str) -> Optional[ReleaseAsset]:
    """
    Find the first asset matching the given regex pattern.

    Args:
        release: Release info to search
        pattern: Regex pattern to match against asset names

    Returns:
        Matching ReleaseAsset or None
    """
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        print(f"  [WARN] Invalid regex pattern: {pattern}")
        return None

    for asset in release.assets:
        if regex.search(asset.name):
            return asset

    # Print available assets if no match found
    print(f"  [WARN] No asset matching '{pattern}' found in release")
    print("    Available assets:")
    for asset in release.assets:
        size_mb = asset.size / (1024 * 1024)
        print(f"      - {asset.name} ({size_mb:.1f} MB)")

    return None


def get_download_url(owner: str, repo: str, asset_pattern: str) -> Optional[str]:
    """
    Get download URL for the latest release asset matching pattern.

    Args:
        owner: Repository owner
        repo: Repository name
        asset_pattern: Regex pattern for asset name

    Returns:
        Download URL or None if not found
    """
    release = get_latest_release(owner, repo)
    if not release:
        return None

    asset = find_matching_asset(release, asset_pattern)
    if not asset:
        return None

    size_mb = asset.size / (1024 * 1024)
    print(f"    Found: {asset.name} ({size_mb:.1f} MB)")

    return asset.download_url
