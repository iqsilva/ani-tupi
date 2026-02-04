"""Tests for AiringAnimeEntry Pydantic model."""

import pytest
from pydantic import ValidationError

from models.models import AiringAnimeEntry


class TestAiringAnimeEntryModel:
    """Test AiringAnimeEntry Pydantic model validation."""

    def test_creates_valid_entry_with_all_fields(self):
        """Test creating a valid AiringAnimeEntry with all fields."""
        entry = AiringAnimeEntry(
            anilist_id=165847,
            title="Jujutsu Kaisen",
            progress=12,
            next_episode_number=15,
            episodes_behind=3,
            airing_at=1704067200,
            average_score=82,
        )

        assert entry.anilist_id == 165847
        assert entry.title == "Jujutsu Kaisen"
        assert entry.progress == 12
        assert entry.next_episode_number == 15
        assert entry.episodes_behind == 3
        assert entry.airing_at == 1704067200
        assert entry.average_score == 82

    def test_creates_entry_with_optional_fields_none(self):
        """Test creating entry with optional fields as None."""
        entry = AiringAnimeEntry(
            anilist_id=1,
            title="Test Anime",
            progress=0,
            next_episode_number=1,
            episodes_behind=1,
            airing_at=None,
            average_score=None,
        )

        assert entry.airing_at is None
        assert entry.average_score is None

    def test_validates_anilist_id_required(self):
        """Test that anilist_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            AiringAnimeEntry(
                title="Test",
                progress=0,
                next_episode_number=1,
                episodes_behind=1,
            )

        assert "anilist_id" in str(exc_info.value)

    def test_validates_title_required_and_nonempty(self):
        """Test that title is required and must be non-empty."""
        with pytest.raises(ValidationError):
            AiringAnimeEntry(
                anilist_id=1,
                title="",  # Empty title
                progress=0,
                next_episode_number=1,
                episodes_behind=1,
            )

    def test_validates_progress_nonnegative(self):
        """Test that progress must be >= 0."""
        with pytest.raises(ValidationError):
            AiringAnimeEntry(
                anilist_id=1,
                title="Test",
                progress=-1,  # Negative
                next_episode_number=1,
                episodes_behind=1,
            )

    def test_validates_next_episode_number_positive(self):
        """Test that next_episode_number must be >= 1."""
        with pytest.raises(ValidationError):
            AiringAnimeEntry(
                anilist_id=1,
                title="Test",
                progress=0,
                next_episode_number=0,  # Must be >= 1
                episodes_behind=1,
            )

    def test_validates_episodes_behind_nonnegative(self):
        """Test that episodes_behind must be >= 0."""
        with pytest.raises(ValidationError):
            AiringAnimeEntry(
                anilist_id=1,
                title="Test",
                progress=5,
                next_episode_number=10,
                episodes_behind=-1,  # Negative
            )

    def test_validates_average_score_range(self):
        """Test that average_score must be 0-100 if provided."""
        # Score too high
        with pytest.raises(ValidationError):
            AiringAnimeEntry(
                anilist_id=1,
                title="Test",
                progress=0,
                next_episode_number=1,
                episodes_behind=1,
                average_score=101,  # > 100
            )

        # Score negative
        with pytest.raises(ValidationError):
            AiringAnimeEntry(
                anilist_id=1,
                title="Test",
                progress=0,
                next_episode_number=1,
                episodes_behind=1,
                average_score=-1,  # < 0
            )

    def test_allows_score_boundaries(self):
        """Test that average_score accepts 0 and 100."""
        entry_zero = AiringAnimeEntry(
            anilist_id=1,
            title="Test",
            progress=0,
            next_episode_number=1,
            episodes_behind=1,
            average_score=0,
        )
        assert entry_zero.average_score == 0

        entry_max = AiringAnimeEntry(
            anilist_id=1,
            title="Test",
            progress=0,
            next_episode_number=1,
            episodes_behind=1,
            average_score=100,
        )
        assert entry_max.average_score == 100

    def test_serializes_to_dict(self):
        """Test that model can be serialized to dict."""
        entry = AiringAnimeEntry(
            anilist_id=1,
            title="Test",
            progress=5,
            next_episode_number=10,
            episodes_behind=5,
            airing_at=1704067200,
            average_score=80,
        )

        data = entry.model_dump()

        assert data["anilist_id"] == 1
        assert data["title"] == "Test"
        assert data["progress"] == 5
        assert data["next_episode_number"] == 10
        assert data["episodes_behind"] == 5
        assert data["airing_at"] == 1704067200
        assert data["average_score"] == 80

    def test_serializes_to_json(self):
        """Test that model can be serialized to JSON."""
        entry = AiringAnimeEntry(
            anilist_id=1,
            title="Test Anime",
            progress=5,
            next_episode_number=10,
            episodes_behind=5,
            airing_at=1704067200,
            average_score=80,
        )

        json_str = entry.model_dump_json()

        assert '"anilist_id":1' in json_str
        assert '"title":"Test Anime"' in json_str

    def test_validates_all_required_fields(self):
        """Test that all required fields must be provided."""
        required_fields = [
            "anilist_id",
            "title",
            "progress",
            "next_episode_number",
            "episodes_behind",
        ]

        for field in required_fields:
            # Create valid data
            data = {
                "anilist_id": 1,
                "title": "Test",
                "progress": 5,
                "next_episode_number": 10,
                "episodes_behind": 5,
            }

            # Remove one field
            del data[field]

            with pytest.raises(ValidationError) as exc_info:
                AiringAnimeEntry(**data)

            assert field in str(exc_info.value)

    def test_handles_large_episode_numbers(self):
        """Test handling of large episode numbers."""
        entry = AiringAnimeEntry(
            anilist_id=1,
            title="Long Series",
            progress=500,
            next_episode_number=1000,
            episodes_behind=500,
        )

        assert entry.next_episode_number == 1000
        assert entry.episodes_behind == 500

    def test_handles_zero_episode_behind(self):
        """Test handling when caught up (episodes_behind = 0)."""
        entry = AiringAnimeEntry(
            anilist_id=1,
            title="Current",
            progress=10,
            next_episode_number=10,
            episodes_behind=0,
        )

        assert entry.episodes_behind == 0

    def test_model_is_immutable_in_json_mode(self):
        """Test model serialization options."""
        entry = AiringAnimeEntry(
            anilist_id=1,
            title="Test",
            progress=5,
            next_episode_number=10,
            episodes_behind=5,
        )

        # Model dump should work
        data = entry.model_dump()
        assert isinstance(data, dict)

        # JSON dump should work
        json_str = entry.model_dump_json()
        assert isinstance(json_str, str)
