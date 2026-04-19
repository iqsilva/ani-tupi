#!/usr/bin/env python3
"""Debug helper for startup update-check version detection.

This script shows exactly which local and remote version values are identified
and how the comparison is computed.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path

from models.config import UpdateCheckSettings, get_data_path, settings
from services.update_check_service import UpdateCheckService


DEFAULT_GITHUB_RELEASE_URL = "https://api.github.com/repos/levyvix/ani-tupi/releases/latest"


def read_pyproject_version() -> str | None:
    """Read project version from local pyproject.toml."""
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if not pyproject_path.exists():
        return None

    try:
        with pyproject_path.open("rb") as f:
            data = tomllib.load(f)
        project = data.get("project", {})
        version = project.get("version")
        if isinstance(version, str):
            return version
    except Exception:
        return None

    return None


def read_installed_version(package_name: str) -> str | None:
    """Read installed version from importlib metadata."""
    try:
        return importlib.metadata.version(package_name)
    except Exception:
        return None


def iso_or_none(value: datetime | None) -> str:
    if value is None:
        return "None"
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Debug startup update-check version detection",
    )
    parser.add_argument(
        "--release-url",
        default=settings.updates.release_source_url or DEFAULT_GITHUB_RELEASE_URL,
        help="Remote endpoint used for latest version lookup",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=settings.updates.request_timeout_seconds,
        help="HTTP timeout in seconds",
    )
    parser.add_argument(
        "--interval-hours",
        type=int,
        default=settings.updates.interval_hours,
        help="Cooldown interval in hours",
    )
    parser.add_argument(
        "--state-path",
        default=str(get_data_path() / "update_check_state.json"),
        help="Path to update-check state cache JSON",
    )
    parser.add_argument(
        "--local-version",
        default=None,
        help="Force local version override for comparison",
    )
    parser.add_argument(
        "--package-name",
        default="ani-tupi",
        help="Package name for installed version lookup",
    )
    parser.add_argument(
        "--force-remote",
        action="store_true",
        help="Ignore cooldown cache and always fetch remote version",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON output",
    )
    args = parser.parse_args()

    update_settings = UpdateCheckSettings(
        enabled=True,
        interval_hours=args.interval_hours,
        request_timeout_seconds=args.timeout,
        release_source_url=args.release_url,
        update_command=settings.updates.update_command,
    )

    state_path = Path(args.state_path)
    service = UpdateCheckService(
        update_settings=update_settings,
        state_path=state_path,
        package_name=args.package_name,
        local_version=args.local_version,
    )

    installed_raw = read_installed_version(args.package_name)
    pyproject_raw = read_pyproject_version()
    resolved_local = service._get_local_version()

    state = service._load_state()
    cached_result = None if args.force_remote else service._get_cached_result(resolved_local)

    latest_version = None
    compare_key_local = service._version_key(resolved_local)
    compare_key_remote = None
    update_available = False
    decision_source = "cache" if cached_result is not None else "remote"

    if cached_result is not None:
        latest_version = cached_result.latest_version
        if latest_version is not None:
            compare_key_remote = service._version_key(latest_version)
        update_available = cached_result.update_available
    else:
        latest_version = service._fetch_latest_version()
        if latest_version is not None:
            compare_key_remote = service._version_key(latest_version)
            update_available = service._is_remote_newer(resolved_local, latest_version)

    output = {
        "package_name": args.package_name,
        "release_url": args.release_url,
        "state_path": str(state_path),
        "timeout_seconds": args.timeout,
        "interval_hours": args.interval_hours,
        "decision_source": decision_source,
        "versions": {
            "installed_raw": installed_raw,
            "pyproject_raw": pyproject_raw,
            "resolved_local": resolved_local,
            "resolved_remote": latest_version,
        },
        "comparison": {
            "local_key": compare_key_local,
            "remote_key": compare_key_remote,
            "update_available": update_available,
        },
        "cache": {
            "exists": state is not None,
            "last_checked_at": iso_or_none(state.last_checked_at) if state else "None",
            "last_latest_version": state.last_latest_version if state else None,
            "last_update_available": state.last_update_available if state else None,
        },
        "notes": [
            "Compares version strings only (semantic numeric parts).",
            "Does not compare local git commit with remote git commit.",
        ],
    }

    if args.json:
        print(json.dumps(output, indent=2))
        return

    print("=== Update Check Debug ===")
    print(f"release_url: {output['release_url']}")
    print(f"state_path: {output['state_path']}")
    print(f"decision_source: {output['decision_source']}")
    print("\nLocal version detection:")
    print(f"- installed_raw: {installed_raw}")
    print(f"- pyproject_raw: {pyproject_raw}")
    print(f"- resolved_local: {resolved_local}")
    print("\nRemote version detection:")
    print(f"- resolved_remote: {latest_version}")
    print("\nComparison:")
    print(f"- local_key: {compare_key_local}")
    print(f"- remote_key: {compare_key_remote}")
    print(f"- update_available: {update_available}")
    print("\nCache state:")
    print(f"- exists: {output['cache']['exists']}")
    print(f"- last_checked_at: {output['cache']['last_checked_at']}")
    print(f"- last_latest_version: {output['cache']['last_latest_version']}")
    print(f"- last_update_available: {output['cache']['last_update_available']}")
    print("\nNote:")
    print("- Compares version numbers, not git commit hashes.")


if __name__ == "__main__":
    main()
