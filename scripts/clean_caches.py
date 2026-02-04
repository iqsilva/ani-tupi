#!/usr/bin/env python3
"""Clear all ani-tupi application caches.

Usage:
    uv run scripts/clean_caches.py
"""

import shutil

from models.config import get_data_path


def clean_caches() -> None:
    """Remove all cached data to force fresh queries."""
    data_path = get_data_path()

    cache_locations = [
        (data_path / "cache", "SQLite query cache"),
        (data_path / "anime_cache.json", "JSON episode cache"),
    ]

    cleared_count = 0
    for cache_path, description in cache_locations:
        if cache_path.exists():
            try:
                if cache_path.is_dir():
                    shutil.rmtree(cache_path)
                else:
                    cache_path.unlink()
                print(f"✅ Cleared {description}")
                cleared_count += 1
            except Exception as e:
                print(f"❌ Failed to clear {description}: {e}")
        else:
            print(f"ℹ️  {description} not found (already clean)")

    print(f"\n✅ Cache cleanup complete ({cleared_count} cache(s) cleared)")


if __name__ == "__main__":
    clean_caches()
