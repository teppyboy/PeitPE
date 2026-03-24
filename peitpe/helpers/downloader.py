"""
Download utilities with progress bar support.

Uses requests + tqdm for HTTP downloads with progress indication.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional, Callable

import requests
from tqdm import tqdm


USER_AGENT = "PeitPE-Builder/1.0"


def download_file(
    url: str,
    dest: Path,
    resume: bool = True,
    chunk_size: int = 8192,
) -> None:
    """
    Download a file with progress bar.

    Args:
        url: URL to download from
        dest: Destination file path
        resume: Whether to resume partial downloads
        chunk_size: Download chunk size in bytes
    """
    headers = {"User-Agent": USER_AGENT}

    # Check for partial download
    initial_pos = 0
    if resume and dest.exists():
        initial_pos = dest.stat().st_size
        headers["Range"] = f"bytes={initial_pos}-"

    response = requests.get(url, headers=headers, stream=True, timeout=30)

    # Handle resume response
    if initial_pos > 0 and response.status_code == 206:
        # Server supports resume
        mode = "ab"
    elif initial_pos > 0 and response.status_code == 200:
        # Server doesn't support resume, restart from beginning
        initial_pos = 0
        mode = "wb"
    else:
        response.raise_for_status()
        mode = "wb"

    total_size = int(response.headers.get("content-length", 0))
    if initial_pos > 0:
        total_size += initial_pos

    # Get filename for display
    filename = dest.name

    with open(dest, mode) as f:
        with tqdm(
            total=total_size,
            initial=initial_pos,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc=f"Downloading {filename}",
        ) as pbar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))


def get_file_size(url: str) -> Optional[int]:
    """Get file size from URL without downloading."""
    try:
        response = requests.head(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=10,
            allow_redirects=True,
        )
        if response.status_code == 200:
            content_length = response.headers.get("content-length")
            if content_length:
                return int(content_length)
    except requests.RequestException:
        pass
    return None


def compute_sha256(file_path: Path, chunk_size: int = 65536) -> str:
    """
    Compute SHA-256 hash of a file.

    Args:
        file_path: Path to file
        chunk_size: Read chunk size in bytes

    Returns:
        Uppercase hex string of SHA-256 hash
    """
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha256.update(chunk)

    return sha256.hexdigest().upper()


def verify_sha256(file_path: Path, expected_hash: str) -> bool:
    """Verify file SHA-256 matches expected hash."""
    actual = compute_sha256(file_path)
    return actual == expected_hash.upper()
