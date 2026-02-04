"""Tests for AniList airing episodes GraphQL query."""

import pytest
from unittest.mock import Mock

from services.anilist.anime_operations import AnimeOperationsMixin


class TestAnimeOperationsMixinAiringQuery:
    """Test AnimeOperationsMixin.get_airing_episodes_for_watching()."""

    @pytest.fixture
    def mixin(self):
        """Create a test instance of AnimeOperationsMixin."""
        mixin = AnimeOperationsMixin()
        mixin.user_id = 12345
        mixin.is_authenticated = Mock(return_value=True)
        mixin.get_viewer_info = Mock(return_value=None)
        mixin._query = Mock()
        return mixin

    def test_returns_empty_list_when_not_authenticated(self):
        """Test that method returns empty list when not authenticated."""
        mixin = AnimeOperationsMixin()
        mixin.is_authenticated = Mock(return_value=False)

        result = mixin.get_airing_episodes_for_watching()

        assert result == []
        mixin.is_authenticated.assert_called_once()

    def test_returns_empty_list_when_no_user_id_and_cannot_fetch(self):
        """Test that method returns empty list when user_id is None and fetch fails."""
        mixin = AnimeOperationsMixin()
        mixin.user_id = None
        mixin.is_authenticated = Mock(return_value=True)
        mixin.get_viewer_info = Mock(return_value=None)

        result = mixin.get_airing_episodes_for_watching()

        assert result == []

    def test_sets_user_id_from_viewer_info(self):
        """Test that user_id is set from get_viewer_info when initially None."""
        mock_user = Mock()
        mock_user.id = 98765

        mixin = AnimeOperationsMixin()
        mixin.user_id = None
        mixin.is_authenticated = Mock(return_value=True)
        mixin.get_viewer_info = Mock(return_value=mock_user)
        mixin._query = Mock(return_value={"MediaListCollection": {"lists": []}})

        result = mixin.get_airing_episodes_for_watching()

        assert mixin.user_id == 98765
        assert result == []

    def test_queries_with_correct_variables(self, mixin):
        """Test that GraphQL query is called with correct user_id."""
        mixin._query.return_value = {"MediaListCollection": {"lists": []}}

        mixin.get_airing_episodes_for_watching()

        # Verify _query was called
        assert mixin._query.called
        call_args = mixin._query.call_args

        # Check that query string is passed
        query_string = call_args[0][0]
        assert "MediaListCollection" in query_string
        assert "CURRENT" in query_string
        assert "nextAiringEpisode" in query_string

        # Check that variables include userId
        variables = call_args[0][1]
        assert variables["userId"] == 12345

    def test_flattens_nested_lists_structure(self, mixin):
        """Test that nested lists structure is correctly flattened."""
        mixin._query.return_value = {
            "MediaListCollection": {
                "lists": [
                    {
                        "entries": [
                            {"progress": 5, "media": {"id": 1}},
                            {"progress": 10, "media": {"id": 2}},
                        ]
                    },
                    {
                        "entries": [
                            {"progress": 15, "media": {"id": 3}},
                        ]
                    },
                ]
            }
        }

        result = mixin.get_airing_episodes_for_watching()

        # Should have 3 entries flattened
        assert len(result) == 3
        assert result[0]["progress"] == 5
        assert result[1]["progress"] == 10
        assert result[2]["progress"] == 15

    def test_returns_empty_list_for_empty_lists(self, mixin):
        """Test handling of empty lists in response."""
        mixin._query.return_value = {"MediaListCollection": {"lists": []}}

        result = mixin.get_airing_episodes_for_watching()

        assert result == []

    def test_returns_empty_list_when_query_returns_none(self, mixin):
        """Test handling when _query returns None."""
        mixin._query.return_value = None

        result = mixin.get_airing_episodes_for_watching()

        assert result == []

    def test_returns_empty_list_when_no_media_list_collection(self, mixin):
        """Test handling when MediaListCollection is missing from response."""
        mixin._query.return_value = {"Page": {"media": []}}

        result = mixin.get_airing_episodes_for_watching()

        assert result == []

    def test_handles_exception_gracefully(self, mixin):
        """Test that exceptions are caught and empty list is returned."""
        mixin._query.side_effect = Exception("Network error")

        result = mixin.get_airing_episodes_for_watching()

        assert result == []

    def test_query_includes_required_fields(self, mixin):
        """Test that GraphQL query includes all required fields."""
        mixin._query.return_value = {"MediaListCollection": {"lists": []}}

        mixin.get_airing_episodes_for_watching()

        query_string = mixin._query.call_args[0][0]

        # Verify required fields are in query
        assert "progress" in query_string
        assert "media" in query_string
        assert "id" in query_string
        assert "title" in query_string
        assert "romaji" in query_string
        assert "english" in query_string
        assert "native" in query_string
        assert "averageScore" in query_string
        assert "status" in query_string
        assert "nextAiringEpisode" in query_string
        assert "episode" in query_string
        assert "airingAt" in query_string

    def test_preserves_raw_api_response_structure(self, mixin):
        """Test that raw API structure is preserved for service layer processing."""
        raw_entries = [
            {
                "progress": 12,
                "media": {
                    "id": 165847,
                    "title": {
                        "romaji": "Jujutsu Kaisen",
                        "english": "Sorcery Fight",
                        "native": "呪術廻戦",
                    },
                    "averageScore": 82,
                    "status": "RELEASING",
                    "nextAiringEpisode": {"episode": 15, "airingAt": 1704067200},
                },
            }
        ]

        mixin._query.return_value = {"MediaListCollection": {"lists": [{"entries": raw_entries}]}}

        result = mixin.get_airing_episodes_for_watching()

        # Verify raw structure is preserved
        assert result[0]["progress"] == 12
        assert result[0]["media"]["id"] == 165847
        assert result[0]["media"]["title"]["romaji"] == "Jujutsu Kaisen"
        assert result[0]["media"]["nextAiringEpisode"]["episode"] == 15
        assert result[0]["media"]["nextAiringEpisode"]["airingAt"] == 1704067200

    def test_handles_large_watching_list(self, mixin):
        """Test handling of large watching lists (100+ anime)."""
        large_list = []
        for i in range(150):
            large_list.append(
                {
                    "progress": i,
                    "media": {
                        "id": 1000 + i,
                        "title": {"romaji": f"Anime {i}", "english": None, "native": None},
                        "averageScore": 50 + (i % 50),
                        "nextAiringEpisode": {"episode": i + 10, "airingAt": 1704067200},
                    },
                }
            )

        mixin._query.return_value = {"MediaListCollection": {"lists": [{"entries": large_list}]}}

        result = mixin.get_airing_episodes_for_watching()

        assert len(result) == 150
        # Verify first and last entries
        assert result[0]["progress"] == 0
        assert result[-1]["progress"] == 149

    def test_handles_null_fields_in_response(self, mixin):
        """Test handling of null fields that are optional."""
        mixin._query.return_value = {
            "MediaListCollection": {
                "lists": [
                    {
                        "entries": [
                            {
                                "progress": 5,
                                "media": {
                                    "id": 1,
                                    "title": {"romaji": "Test", "english": None, "native": None},
                                    "averageScore": None,  # Null score
                                    "status": None,  # Null status
                                    "nextAiringEpisode": {
                                        "episode": 10,
                                        "airingAt": None,  # Null airing time
                                    },
                                },
                            }
                        ]
                    }
                ]
            }
        }

        result = mixin.get_airing_episodes_for_watching()

        # Should not fail with null values
        assert len(result) == 1
        assert result[0]["media"]["averageScore"] is None
        assert result[0]["media"]["nextAiringEpisode"]["airingAt"] is None
