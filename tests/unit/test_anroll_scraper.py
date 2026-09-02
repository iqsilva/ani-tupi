"""Tests for AnRoll scraper episode list extraction."""

from unittest.mock import MagicMock, patch


from scrapers.plugins.anroll import AnRoll

ANIME_PAGE_HTML = """
<html><body>
  <a href="https://anroll.io/53289/">Primeiro Episódio</a>
  <a href="https://anroll.io/60098/">Último Episódio</a>
</body></html>
"""

SIDEBAR_HTML = """
<html><body>
  <div class="ep-list-box">
    <a href="https://anroll.io/53289/">01 Ep</a>
    <a href="https://anroll.io/53633/">02 Ep</a>
    <a href="https://anroll.io/60098/">12 Ep</a>
  </div>
</body></html>
"""


def _html_response(html: str):
    from scrapling.parser import Selector

    return Selector(html)


class TestAnRollEpisodes:
    def setup_method(self):
        self.scraper = AnRoll()

    @patch("scrapers.plugins.anroll.rep")
    @patch("scrapers.plugins.anroll.fetch")
    def test_search_episodes_uses_sidebar_not_id_range(self, mock_get, mock_rep):
        mock_get.side_effect = [
            _html_response(ANIME_PAGE_HTML),
            _html_response(SIDEBAR_HTML),
        ]

        self.scraper.search_episodes(
            "Aishiteru Game wo Owarasetai",
            "https://anroll.io/anime/aishiteru-game-wo-owarasetai/",
            None,
        )

        assert mock_get.call_count == 2
        mock_rep.add_episode_list.assert_called_once()
        anime, _, urls, source = mock_rep.add_episode_list.call_args[0]
        assert anime == "Aishiteru Game wo Owarasetai"
        assert source == "anroll"
        assert len(urls) == 3
        assert urls[0] == "https://anroll.io/53289/"
        assert urls[-1] == "https://anroll.io/60098/"

    @patch("scrapers.plugins.anroll.fetch")
    def test_episodes_from_sidebar_parses_ep_list_box(self, mock_get):
        mock_get.return_value = _html_response(SIDEBAR_HTML)

        titles, urls = self.scraper._episodes_from_sidebar("https://anroll.io/53289/")

        assert len(titles) == 3
        assert titles[0] == "Ep.001"
        assert urls[1] == "https://anroll.io/53633/"

    @patch("scrapers.plugins.anroll.fetch")
    def test_episodes_from_sidebar_returns_empty_without_box(self, mock_get):
        mock_get.return_value = _html_response("<html></html>")

        titles, urls = self.scraper._episodes_from_sidebar("https://anroll.io/53289/")

        assert titles == []
        assert urls == []


SEARCH_ANIME_HTML = """
<html><body>
  <article class="anime-card">
    <a href="https://anroll.io/anime/mao/">
      <img alt="Mao" />
    </a>
  </article>
</body></html>
"""


class TestAnRollSearchAnimeAndPlayer:
    def setup_method(self):
        self.scraper = AnRoll()

    @patch("scrapers.plugins.anroll.fetch")
    def test_search_anime_returns_results(self, mock_get):
        mock_get.return_value = _html_response(SEARCH_ANIME_HTML)

        results = self.scraper.search_anime("mao")

        assert len(results) == 1
        assert results[0].title == "Mao"
        assert results[0].url == "https://anroll.io/anime/mao/"
        assert results[0].source == "anroll"

    @patch("scrapers.plugins.anroll.store_player_source")
    @patch("scrapling.fetchers.StealthyFetcher.fetch")
    def test_search_player_src_extracts_video_url(self, mock_fetch, mock_store):
        mock_store.return_value = True
        event = MagicMock()
        event.is_set.return_value = False

        def run_page_action(url, **kwargs):
            page = MagicMock()
            frame = MagicMock()
            frame.url = "https://anidrive.example.com/embed/abc"
            frame.evaluate.return_value = ["https://googlevideo.com/videoplayback?id=abc"]
            page.frames = [frame]
            kwargs["page_action"](page)
            return MagicMock()

        mock_fetch.side_effect = run_page_action

        container = []
        self.scraper.search_player_src("https://anroll.io/53289/", container, event)

        mock_store.assert_called_once_with(
            container, event, "https://googlevideo.com/videoplayback?id=abc"
        )
