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
    def test_returns_all_episodes_beyond_old_limit(self, mock_post):
        """Test API now returns all episodes beyond old limit (regression: episode 11+)."""
        # Simulate API response with 22 episodes (full series + part 2)
        html_fragments = [self._create_episode_html(i) for i in range(1, 23)]
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": html_fragments}
        mock_post.return_value = mock_response

        results = self.scraper._search_episodes_with_audio("sakamoto days", "dublado")

        # Should get all 22 episodes (was capped at 10 before fix)
        assert len(results) == 22, f"Expected 22 episodes, got {len(results)}"

        # Verify episodes are in order and include episode 11 (regression check)
        for i, ep in enumerate(results, 1):
            assert f"Episódio {i:02d}" in ep["title"], f"Episode {i} not found in correct position"

        episode_numbers = [
            int(ep["title"].split("Episódio ")[1]) for ep in results if "Episódio" in ep["title"]
        ]
        assert 11 in episode_numbers, "Episode 11 not found - regression detected!"

    @patch("scrapers.plugins.animesdigital.requests.post")
    def test_handles_partial_response(self, mock_post):
        """Test handling of partial API response."""
        # Simulate response with 15 episodes
        html_fragments = [self._create_episode_html(i) for i in range(1, 16)]
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": html_fragments}
        mock_post.return_value = mock_response

        results = self.scraper._search_episodes_with_audio("sakamoto days", "dublado")

        # Should return all 15 episodes provided by API
        assert len(results) == 15, f"Expected 15 episodes, got {len(results)}"
