#!/usr/bin/env python3

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import sys
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USER_AGENT = "transmute-release-pin-updater/1.0"
CHUNK_SIZE = 1024 * 1024


def status(message: str) -> None:
    print(f"[status] {message}", file=sys.stderr)


@dataclass(frozen=True)
class ToolRelease:
    arg_prefix: str
    release_url: str
    version: str
    sha_amd64: str
    sha_arm64: str


def fetch_json(url: str) -> dict:
    status(f"Fetching metadata: {url}")
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )
    with urlopen(request) as response:
        return json.load(response)


def download_and_hash(url: str, destination: Path) -> str:
    status(f"Downloading {destination.name}")
    request = Request(url, headers={"User-Agent": USER_AGENT})
    hasher = hashlib.sha256()

    with urlopen(request) as response, destination.open("wb") as output_file:
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
            output_file.write(chunk)

            status(f"Computed sha256 for {destination.name}")
    return hasher.hexdigest()


def find_asset_url(release: dict, expected_name: str) -> str:
    for asset in release.get("assets", []):
        if asset.get("name") == expected_name:
            url = asset.get("browser_download_url")
            if url:
                return url
    raise RuntimeError(f"Asset not found in release: {expected_name}")


def normalize_github_version(tag_name: str) -> str:
    return tag_name[1:] if tag_name.startswith("v") else tag_name


def build_pandoc_release(download_dir: Path) -> ToolRelease:
    status("Checking latest Pandoc release")
    release = fetch_json("https://api.github.com/repos/jgm/pandoc/releases/latest")
    version = normalize_github_version(release["tag_name"])
    amd_name = f"pandoc-{version}-linux-amd64.tar.gz"
    arm_name = f"pandoc-{version}-linux-arm64.tar.gz"

    amd_sha = download_and_hash(
        find_asset_url(release, amd_name),
        download_dir / amd_name,
    )
    arm_sha = download_and_hash(
        find_asset_url(release, arm_name),
        download_dir / arm_name,
    )

    return ToolRelease(
        arg_prefix="PANDOC",
        release_url="https://github.com/jgm/pandoc/releases",
        version=version,
        sha_amd64=amd_sha,
        sha_arm64=arm_sha,
    )


def build_drawio_release(download_dir: Path) -> ToolRelease:
    status("Checking latest Draw.io release")
    release = fetch_json("https://api.github.com/repos/jgraph/drawio-desktop/releases/latest")
    version = normalize_github_version(release["tag_name"])
    amd_name = f"drawio-amd64-{version}.deb"
    arm_name = f"drawio-arm64-{version}.deb"

    amd_sha = download_and_hash(
        find_asset_url(release, amd_name),
        download_dir / amd_name,
    )
    arm_sha = download_and_hash(
        find_asset_url(release, arm_name),
        download_dir / arm_name,
    )

    return ToolRelease(
        arg_prefix="DRAWIO",
        release_url="https://github.com/jgraph/drawio-desktop/releases",
        version=version,
        sha_amd64=amd_sha,
        sha_arm64=arm_sha,
    )


def build_calibre_release(download_dir: Path) -> ToolRelease:
    status("Checking latest Calibre release")
    release = fetch_json("https://api.github.com/repos/kovidgoyal/calibre/releases/latest")
    version = normalize_github_version(release["tag_name"])
    amd_name = f"calibre-{version}-x86_64.txz"
    arm_name = f"calibre-{version}-arm64.txz"

    find_asset_url(release, amd_name)
    find_asset_url(release, arm_name)

    amd_url = f"https://download.calibre-ebook.com/{version}/{amd_name}"
    arm_url = f"https://download.calibre-ebook.com/{version}/{arm_name}"

    amd_sha = download_and_hash(amd_url, download_dir / amd_name)
    arm_sha = download_and_hash(arm_url, download_dir / arm_name)

    return ToolRelease(
        arg_prefix="CALIBRE",
        release_url="https://github.com/kovidgoyal/calibre/releases",
        version=version,
        sha_amd64=amd_sha,
        sha_arm64=arm_sha,
    )


def format_output(releases: list[ToolRelease]) -> str:
    lines: list[str] = []
    for release in releases:
        lines.append(f"# {release.release_url}")
        lines.append(f'ARG {release.arg_prefix}_VERSION="{release.version}"')
        lines.append(f'ARG {release.arg_prefix}_SHA_AMD64="{release.sha_amd64}"')
        lines.append(f'ARG {release.arg_prefix}_SHA_ARM64="{release.sha_arm64}"')
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch latest Dockerfile release versions and checksums for Calibre, Pandoc, and Draw.io.",
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        help="Directory to store downloaded artifacts. Defaults to a temporary directory that is deleted after the run.",
    )
    return parser.parse_args()


@contextlib.contextmanager
def resolve_download_dir(download_dir: Path | None) -> Iterator[Path]:
    if download_dir is None:
        with tempfile.TemporaryDirectory(prefix="transmute-release-pins-") as temp_dir:
            temp_path = Path(temp_dir)
            status(f"Using temporary download directory: {temp_path}")
            yield temp_path
        return

    download_dir.mkdir(parents=True, exist_ok=True)
    status(f"Using download directory: {download_dir}")
    yield download_dir


def main() -> int:
    args = parse_args()
    try:
        status("Resolving latest release pins")
        with resolve_download_dir(args.download_dir) as download_dir:
            releases = [
                build_calibre_release(download_dir),
                build_pandoc_release(download_dir),
                build_drawio_release(download_dir),
            ]
            status("Finished computing release pins")
            print(format_output(releases))
        return 0
    except (HTTPError, URLError, OSError, RuntimeError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())