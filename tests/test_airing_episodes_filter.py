"""Tests for AiringEpisodesService awaiting filter.

Tests cover:
- Filtering only awaiting episodes (within 90 days, not yet aired)
- Excluding already-aired episodes
- Excluding no-next-episode entries
- Excluding hiatus anime (90+ days in future)
- Sorting preserved on filtered results
- Empty result when no awaiting anime
"""

import time
from unittest.mock import patch

from services.anime.airing_episodes_service import AiringEpisodesService


class TestAwaitingEpisodeFilter:
    """Tests for _is_awaiting_episode helper method."""

    def test_none_airing_at_returns_false(self):
        """Test that None airing_at returns False."""
        assert AiringEpisodesService._is_awaiting_episode(None) is False

    def test_already_aired_returns_false(self):
        """Test that already-aired episode (past airing_at) returns False."""
        now = int(time.time())
        past_time = now - 86400  # 1 day ago

        assert AiringEpisodesService._is_awaiting_episode(past_time) is False

    def test_just_aired_returns_false(self):
        """Test that just-aired episode (airing_at == now) returns False."""
        now = int(time.time())

        assert AiringEpisodesService._is_awaiting_episode(now) is False

    def test_within_90_days_returns_true(self):
        """Test that episode within 90 days returns True."""
        now = int(time.time())
        in_30_days = now + (30 * 24 * 60 * 60)

        assert AiringEpisodesService._is_awaiting_episode(in_30_days) is True

    def test_exactly_90_days_in_future_returns_false(self):
        """Test that episode exactly 90 days away returns False (boundary)."""
        now = int(time.time())
        exactly_90_days = now + (90 * 24 * 60 * 60)

        assert AiringEpisodesService._is_awaiting_episode(exactly_90_days) is False

    def test_just_under_90_days_returns_true(self):
        """Test that episode just under 90 days returns True."""
        now = int(time.time())
        almost_90_days = now + (90 * 24 * 60 * 60) - 1

        assert AiringEpisodesService._is_awaiting_episode(almost_90_days) is True

    def test_far_future_returns_false(self):
        """Test that episode far in future (hiatus) returns False."""
        now = int(time.time())
        in_200_days = now + (200 * 24 * 60 * 60)

        assert AiringEpisodesService._is_awaiting_episode(in_200_days) is False


class TestGetWatchingWithAwaitingEpisodes:
    """Tests for get_watching_with_airing_episodes filter logic."""

    def setup_method(self):
        """Set up test service and mocks."""
        self.service = AiringEpisodesService()

    def _create_entry(
        self,
        anilist_id: int,
        title: str,
        progress: int,
        next_episode: int,
        airing_at: int | None,
    ) -> dict:
        """Helper to create a raw API entry."""
        return {
            "progress": progress,
            "media": {
                "id": anilist_id,
                "title": {"romaji": title, "english": None, "native": None},
                "averageScore": 80,
                "nextAiringEpisode": {"episode": next_episode, "airingAt": airing_at},
            },
        }

    def test_no_entries_returns_empty(self):
        """Test that empty API response returns empty list."""
        with patch.object(self.service.client, "get_airing_episodes_for_watching", return_value=[]):
            result = self.service.get_watching_with_airing_episodes()

        assert result == []

    def test_awaiting_episode_included(self):
        """Test that awaiting episode is included in results."""
        now = int(time.time())
        in_30_days = now + (30 * 24 * 60 * 60)

        with patch.object(
            self.service.client,
            "get_airing_episodes_for_watching",
            return_value=[
                self._create_entry(
                    anilist_id=1001,
                    title="Test Anime",
                    progress=5,
                    next_episode=6,
                    airing_at=in_30_days,
                ),
            ],
        ):
            result = self.service.get_watching_with_airing_episodes()

        assert len(result) == 1
        assert result[0].anilist_id == 1001
        assert result[0].title == "Test Anime"

    def test_already_aired_excluded(self):
        """Test that already-aired episode is excluded."""
        now = int(time.time())
        past_time = now - 86400  # 1 day ago

        with patch.object(
            self.service.client,
            "get_airing_episodes_for_watching",
            return_value=[
                self._create_entry(
                    anilist_id=1001,
                    title="Test Anime",
                    progress=10,
                    next_episode=11,
                    airing_at=past_time,
                ),
            ],
        ):
            result = self.service.get_watching_with_airing_episodes()

        assert len(result) == 0

    def test_hiatus_excluded(self):
        """Test that anime on hiatus (90+ days) is excluded."""
        now = int(time.time())
        in_200_days = now + (200 * 24 * 60 * 60)

        with patch.object(
            self.service.client,
            "get_airing_episodes_for_watching",
            return_value=[
                self._create_entry(
                    anilist_id=1001,
                    title="Test Anime Hiatus",
                    progress=5,
                    next_episode=6,
                    airing_at=in_200_days,
                ),
            ],
        ):
            result = self.service.get_watching_with_airing_episodes()

        assert len(result) == 0

    def test_no_next_airing_excluded(self):
        """Test that entries without nextAiringEpisode are excluded."""
        with patch.object(
            self.service.client,
            "get_airing_episodes_for_watching",
            return_value=[
                {
                    "progress": 10,
                    "media": {
                        "id": 1001,
                        "title": {"romaji": "Completed Anime", "english": None, "native": None},
                        "averageScore": 85,
                        "nextAiringEpisode": None,
                    },
                },
            ],
        ):
            result = self.service.get_watching_with_airing_episodes()

        assert len(result) == 0

    def test_mixed_entries_filters_correctly(self):
        """Test filtering with mix of awaiting, aired, and hiatus anime."""
        now = int(time.time())
        in_30_days = now + (30 * 24 * 60 * 60)
        past_time = now - 86400
        in_200_days = now + (200 * 24 * 60 * 60)

        with patch.object(
            self.service.client,
            "get_airing_episodes_for_watching",
            return_value=[
                self._create_entry(
                    anilist_id=1001,
                    title="Awaiting Anime 1",
                    progress=5,
                    next_episode=6,
                    airing_at=in_30_days,
                ),
                self._create_entry(
                    anilist_id=1002,
                    title="Already Aired",
                    progress=10,
                    next_episode=11,
                    airing_at=past_time,
                ),
                self._create_entry(
                    anilist_id=1003,
                    title="Awaiting Anime 2",
                    progress=15,
                    next_episode=17,
                    airing_at=in_30_days,
                ),
                self._create_entry(
                    anilist_id=1004,
                    title="On Hiatus",
                    progress=3,
                    next_episode=4,
                    airing_at=in_200_days,
                ),
            ],
        ):
            result = self.service.get_watching_with_airing_episodes()

        # Should only include awaiting anime (1001, 1003)
        assert len(result) == 2
        assert result[0].anilist_id in (1001, 1003)
        assert result[1].anilist_id in (1001, 1003)

    def test_sorting_preserved_on_filtered(self):
        """Test that filtered results are still sorted by episodes_behind."""
        now = int(time.time())
        in_30_days = now + (30 * 24 * 60 * 60)

        with patch.object(
            self.service.client,
            "get_airing_episodes_for_watching",
            return_value=[
                self._create_entry(
                    anilist_id=1001,
                    title="Behind 3 Episodes",
                    progress=6,
                    next_episode=10,  # 10 - 1 - 6 = 3 behind
                    airing_at=in_30_days,
                ),
                self._create_entry(
                    anilist_id=1002,
                    title="Behind 1 Episode",
                    progress=8,
                    next_episode=10,  # 10 - 1 - 8 = 1 behind
                    airing_at=in_30_days,
                ),
                self._create_entry(
                    anilist_id=1003,
                    title="Behind 5 Episodes",
                    progress=4,
                    next_episode=10,  # 10 - 1 - 4 = 5 behind
                    airing_at=in_30_days,
                ),
            ],
        ):
            result = self.service.get_watching_with_airing_episodes()

        assert len(result) == 3
        # Should be sorted by episodes_behind descending
        assert result[0].episodes_behind == 5  # Most behind first
        assert result[1].episodes_behind == 3
        assert result[2].episodes_behind == 1  # Least behind last

    def test_empty_when_no_awaiting_anime(self):
        """Test empty result when all anime are either aired or hiatus."""
        now = int(time.time())
        past_time = now - 86400
        in_200_days = now + (200 * 24 * 60 * 60)

        with patch.object(
            self.service.client,
            "get_airing_episodes_for_watching",
            return_value=[
                self._create_entry(
                    anilist_id=1001,
                    title="Already Aired",
                    progress=10,
                    next_episode=11,
                    airing_at=past_time,
                ),
                self._create_entry(
                    anilist_id=1002,
                    title="On Hiatus",
                    progress=5,
                    next_episode=6,
                    airing_at=in_200_days,
                ),
            ],
        ):
            result = self.service.get_watching_with_airing_episodes()

        assert len(result) == 0

    def test_malformed_entry_skipped(self):
        """Test that malformed entries are skipped gracefully."""
        now = int(time.time())
        in_30_days = now + (30 * 24 * 60 * 60)

        with patch.object(
            self.service.client,
            "get_airing_episodes_for_watching",
            return_value=[
                {
                    "progress": 5,
                    "media": None,  # Malformed
                },
                self._create_entry(
                    anilist_id=1001,
                    title="Valid Anime",
                    progress=5,
                    next_episode=6,
                    airing_at=in_30_days,
                ),
            ],
        ):
            result = self.service.get_watching_with_airing_episodes()

        assert len(result) == 1
        assert result[0].anilist_id == 1001

    def test_episodes_behind_calculated_correctly(self):
        """Test correct episodes_behind calculation on filtered results."""
        now = int(time.time())
        in_30_days = now + (30 * 24 * 60 * 60)

        with patch.object(
            self.service.client,
            "get_airing_episodes_for_watching",
            return_value=[
                self._create_entry(
                    anilist_id=1001,
                    title="Test",
                    progress=10,
                    next_episode=15,
                    airing_at=in_30_days,
                ),
            ],
        ):
            result = self.service.get_watching_with_airing_episodes()

        assert len(result) == 1
        # episodes_behind = (next_episode - 1) - progress = (15 - 1) - 10 = 4
        assert result[0].episodes_behind == 4
