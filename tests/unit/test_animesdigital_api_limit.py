"""Test AnimesDigital API limit parameter fix.

Tests that the _search_episodes_with_audio method now includes the
'limit' parameter in API requests, allowing it to fetch all episodes
instead of being capped at 10.

Regression test for: Episode 11 of Sakamoto Days not being found
"""

from unittest.mock import patch, MagicMock

from scrapers.plugins.animesdigital import AnimesDigital


class TestAnimesDigitalAPILimit:
    """Tests for AnimesDigital._search_episodes_with_audio API limit fix."""

    def setup_method(self):
        """Set up test scraper."""
        self.scraper = AnimesDigital()

    def _create_episode_html(self, episode_num: int) -> str:
        """Helper to create episode HTML fragment for API response."""
        return f"""
        <div class="itemA">
            <a href="https://animesdigital.org/video/a/{100000 + episode_num}/">
                <span class="title_anime">Sakamoto Days Dublado Episódio {episode_num:02d}</span>
                <img src="image.jpg" />
            </a>
        </div>
        """

    @patch("scrapers.plugins.animesdigital.requests.post")
    def test_api_includes_limit_parameter(self, mock_post):
        """Verify that _search_episodes_with_audio includes 'limit' in payload."""
        # Create mock response with 15 episodes
        html_fragments = [self._create_episode_html(i) for i in range(1, 16)]
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": html_fragments}
        mock_post.return_value = mock_response

        self.scraper._search_episodes_with_audio("sakamoto days", "dublado")

        # Verify the API was called
        assert mock_post.called

        # Check that 'limit' parameter was included in the payload
        call_args = mock_post.call_args
        payload = call_args[1]["data"]  # Get the data kwargs

        assert "limit" in payload, "API request missing 'limit' parameter"
        assert payload["limit"] == "90", f"Expected limit=90, got {payload['limit']}"

    @patch("scrapers.plugins.animesdigital.requests.post")
    def test_api_returns_all_episodes_up_to_limit(self, mock_post):
        """Test that API with limit=90 returns all episodes up to 90."""
        # Simulate API response with 22 episodes (both series and part 2)
        html_fragments = [self._create_episode_html(i) for i in range(1, 23)]
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": html_fragments}
        mock_post.return_value = mock_response

        results = self.scraper._search_episodes_with_audio("sakamoto days", "dublado")

        # Should get all 22 episodes
        assert len(results) == 22, f"Expected 22 episodes, got {len(results)}"

        # Verify episodes are sorted
        for i, ep in enumerate(results, 1):
            assert f"Episódio {i:02d}" in ep["title"], f"Episode {i} not found in correct position"

    @patch("scrapers.plugins.animesdigital.requests.post")
    def test_search_episodes_with_audio_returns_11_plus_episodes(self, mock_post):
        """Regression test: Verify episode 11 is now discoverable (was capped at 10)."""
        # Create response with 15 episodes
        html_fragments = [self._create_episode_html(i) for i in range(1, 16)]
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": html_fragments}
        mock_post.return_value = mock_response

        results = self.scraper._search_episodes_with_audio("sakamoto days", "dublado")

        # Must include episode 11 (was missing before fix)
        episode_numbers = [
            int(ep["title"].split("Episódio ")[1]) for ep in results if "Episódio" in ep["title"]
        ]

        assert 11 in episode_numbers, "Episode 11 not found - regression detected!"
        assert len(results) > 10, f"Still capped at 10 episodes, got {len(results)}"
