"""Pytest configuration and fixtures for ani-tupi tests.

This module provides real service instances for integration testing,
avoiding excessive mocks in favor of testing actual behavior.
"""

import tempfile
from pathlib import Path

import pytest

from services.repository import Repository


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for test storage.

    Automatically cleaned up after test completes.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_settings(temp_dir, monkeypatch):
    """Provide real AppSettings configured for testing.

    Uses environment variables with test-specific paths.
    """
    # Use temporary directory for cache and storage
    monkeypatch.setenv("ANI_TUPI__CACHE__DIRECTORY", str(temp_dir / "cache"))
    monkeypatch.setenv("ANI_TUPI__ANIME__DOWNLOAD_DIRECTORY", str(temp_dir / "downloads"))
    monkeypatch.setenv("ANI_TUPI__LOG_LEVEL", "debug")

    # Return fresh settings instance
    from importlib import reload
    import models.config

    reload(models.config)
    return models.config.settings


@pytest.fixture
def repository(test_settings):
    """Provide a real Repository instance with real plugins loaded.

    This loads actual scraper plugins from scrapers/plugins/ directory.
    Cache is reset before each test to ensure isolation.
    """
    Repository.reset_singleton()
    repo = Repository()

    yield repo

    # Cleanup
    Repository.reset_singleton()


@pytest.fixture(autouse=True)
def reset_repository():
    """Auto-reset repository singleton before each test."""
    Repository.reset_singleton()
    yield
    Repository.reset_singleton()
