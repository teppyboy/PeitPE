"""
ISO download module.

Downloads the source Windows PE ISO with resume support
and SHA-256 verification.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .config import AppConfig
from .helpers.downloader import (
    download_file,
    compute_sha256,
    verify_sha256,
    USER_AGENT,
)


DOWNLOAD_PAGE = "https://www.hirensbootcd.org/download/"


def fetch_download_page() -> str:
    """Fetch the download page content."""
    print(f"    Page: {DOWNLOAD_PAGE}")

    response = requests.get(
        DOWNLOAD_PAGE,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()

    return response.text


def parse_iso_url(html: str, base_url: str) -> str:
    """
    Parse ISO download URL from page HTML.

    Args:
        html: Page HTML content
        base_url: Base URL for resolving relative URLs

    Returns:
        Absolute ISO download URL

    Raises:
        RuntimeError: If no ISO link found
    """
    soup = BeautifulSoup(html, "html.parser")

    # Find links ending in .iso
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.lower().endswith(".iso") or ".iso?" in href.lower():
            # Make absolute if relative
            if not href.startswith(("http://", "https://")):
                parsed = urlparse(base_url)
                href = f"{parsed.scheme}://{parsed.netloc}{href}"
            return href

    # Fallback: regex search for .iso URLs
    match = re.search(r'https?://[^\s"<>]+\.iso\b', html)
    if match:
        return match.group(0)

    raise RuntimeError(
        f"Could not find an ISO download link on '{DOWNLOAD_PAGE}'. "
        "The page layout may have changed."
    )


def extract_iso_filename(url: str) -> str:
    """Extract filename from ISO URL."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    filename = Path(path).name

    # Remove query parameters
    if "?" in filename:
        filename = filename.split("?")[0]

    return filename


def parse_sha256(html: str) -> str | None:
    """Parse SHA-256 hash from page HTML if present."""
    pattern = r"(?i)sha-?256[:\s]+([0-9a-f]{64})"
    match = re.search(pattern, html)
    if match:
        return match.group(1).upper()
    return None


def download_iso(config: AppConfig, force: bool = False) -> None:
    """
    Download the source Windows PE ISO.

    Args:
        config: Application configuration
        force: Force re-download even if file exists
    """
    print("[*] Checking latest source ISO release...")

    # Fetch download page
    try:
        html = fetch_download_page()
    except Exception as e:
        raise RuntimeError(f"Failed to fetch download page '{DOWNLOAD_PAGE}': {e}")

    # Parse ISO URL
    iso_url = parse_iso_url(html, DOWNLOAD_PAGE)
    print(f"    ISO URL : {iso_url}")

    # Extract filename and destination path
    iso_filename = extract_iso_filename(iso_url)
    work_dir = Path(config.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    iso_dest = work_dir / iso_filename

    # Update config with actual ISO path
    config.source_iso = str(iso_dest)

    # Parse SHA-256 if available
    expected_hash = parse_sha256(html)
    if expected_hash:
        print(f"    Expected SHA-256: {expected_hash}")

    # Check if already downloaded
    if not force and iso_dest.exists():
        print(f"    Found existing: {iso_dest}")

        if expected_hash:
            print("    Verifying checksum...")
            if verify_sha256(iso_dest, expected_hash):
                print("[OK] ISO is already up to date (checksum verified).")
                return
            print("    Checksum mismatch - re-downloading.")
        else:
            print(
                "[OK] ISO already present (no checksum to verify). Use --force-download to re-download."
            )
            return

    # Download ISO
    print(f"[*] Downloading ISO to: {iso_dest}")
    part_file = Path(f"{iso_dest}.part")

    try:
        download_file(iso_url, part_file)
    except Exception as e:
        # Clean up partial file
        if part_file.exists():
            part_file.unlink()
        raise RuntimeError(f"Download failed: {e}")

    # Move to final location
    if iso_dest.exists():
        iso_dest.unlink()
    part_file.rename(iso_dest)

    # Verify checksum
    if expected_hash:
        print("[*] Verifying download...")
        if not verify_sha256(iso_dest, expected_hash):
            actual = compute_sha256(iso_dest)
            iso_dest.unlink()
            raise RuntimeError(
                f"SHA-256 mismatch after download. Expected: {expected_hash}  Got: {actual}. File removed."
            )
        print(f"    SHA-256 OK: {compute_sha256(iso_dest)}")

    size_mb = iso_dest.stat().st_size / (1024 * 1024)
    print(f"[OK] Downloaded: {iso_dest} ({size_mb:.1f} MB)")
