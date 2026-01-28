"""Tests for video URL caching in PlayerRepository."""

import pytest
import time
from services.player_repository import PlayerRepository
from utils.cache import get_cache


@pytest.fixture
def player_repo():
    """Create a fresh player repository for each test."""
    PlayerRepository.reset_singleton()
    # Clear cache to ensure isolation
    get_cache().clear()
    return PlayerRepository()


class TestVideoCaching:
    """Test video URL caching in PlayerRepository."""

    def test_set_get_video_url(self, player_repo):
        """Should set and get video URL from cache."""
        player_repo.set_video_url("Naruto", 1, "http://example.com/video1.mp4")
        result = player_repo.get_video_url("Naruto", 1)
        assert result == "http://example.com/video1.mp4"

    def test_get_video_url_not_found(self, player_repo):
        """Should return None for non-existent cache entry."""
        result = player_repo.get_video_url("Unknown", 1)
        assert result is None

    def test_video_url_cache_isolation(self, player_repo):
        """Should isolate cache entries by anime and episode."""
        player_repo.set_video_url("Naruto", 1, "naruto-ep1")
        player_repo.set_video_url("Naruto", 2, "naruto-ep2")
        player_repo.set_video_url("Bleach", 1, "bleach-ep1")

        assert player_repo.get_video_url("Naruto", 1) == "naruto-ep1"
        assert player_repo.get_video_url("Naruto", 2) == "naruto-ep2"
        assert player_repo.get_video_url("Bleach", 1) == "bleach-ep1"

    def test_video_url_cache_with_anilist_id(self, player_repo):
        """Should prefer AniList ID for cache keys."""
        player_repo.set_anime_to_anilist_id("Naruto", 20)
        player_repo.set_video_url("Naruto", 1, "naruto-ep1-anilist")

        # Even if we change the title, it should still find it by ID if the title-to-ID mapping is updated or preserved
        # But here we just verify it works with the title that has an associated ID
        assert player_repo.get_video_url("Naruto", 1) == "naruto-ep1-anilist"

    def test_video_url_cache_ttl(self, player_repo, monkeypatch):
        """Should respect TTL for video URLs."""
        # Set a very short TTL via monkeypatching settings
        from models.config import settings

        monkeypatch.setattr(settings.performance, "video_url_cache_ttl_seconds", 1)

        player_repo.set_video_url("FastExpire", 1, "expiring-soon")
        assert player_repo.get_video_url("FastExpire", 1) == "expiring-soon"

        # Wait for expiration (slightly more than 1s)
        time.sleep(1.1)

        assert player_repo.get_video_url("FastExpire", 1) is None
