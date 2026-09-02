import json
from utils.logging import get_logger
import re
import urllib.parse

from scrapers.core.blogger_resolver import resolve_blogger_token
from scrapers.plugins.utils import (
    DEFAULT_HEADERS,
    FetchError,
    fetch,
    load_plugin,
    store_player_source,
)
from models.models import AnimeMetadata
from services.repository import rep

logger = get_logger(__name__)

BASE_URL = "https://goyabu.io"
HEADERS = DEFAULT_HEADERS
REQUEST_TIMEOUT = 15

_ALL_EPISODES_RE = re.compile(r"allEpisodes\s*=\s*(\[.*?\])\s*;", re.DOTALL)
_PLAYERS_DATA_RE = re.compile(r"var\s+playersData\s*=\s*(\[.*?\])\s*;", re.DOTALL)
_TOKEN_RE = re.compile(r"token=([^&\s]+)")


class Goyabu:
    name = "goyabu"
    base_url = BASE_URL

    def search_anime(self, query: str) -> list[AnimeMetadata]:
        results = []
        try:
            url = f"{BASE_URL}/?s={urllib.parse.quote(query)}"
            page = fetch(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            for article in page.css("article.boxAN", auto_save=True):
                a = article.css("a[href*='/anime/']").first
                title_el = article.css("div.title").first
                if not a or not title_el:
                    continue
                title = title_el.get_all_text(strip=True)
                link = (a.attrib.get("href") or "").strip()
                if title and link:
                    results.append(AnimeMetadata(title=title, url=link, source=self.name))
        except FetchError as e:
            logger.debug("goyabu search_anime falhou: %s", e)
        return results

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        _ = params
        try:
            response = fetch(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

            match = _ALL_EPISODES_RE.search(response.html_content)
            if not match:
                return

            episodes = json.loads(match.group(1))
            titles = []
            urls = []
            for ep in episodes:
                ep_num = ep.get("episodio", "")
                ep_name = ep.get("episode_name", "")
                link = ep.get("link", "")
                if not link or ep_num == "":
                    continue
                label = f"Episódio {ep_num}"
                if ep_name:
                    label = f"{label} - {ep_name}"
                ep_url = f"{BASE_URL}{link}" if link.startswith("/") else link
                titles.append(label)
                urls.append(ep_url)

            if titles and urls:
                rep.add_episode_list(anime, titles, urls, self.name)
        except (FetchError, json.JSONDecodeError, ValueError):
            pass

    def search_player_src(self, url: str, container: list, event) -> None:
        try:
            response = fetch(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

            # Extract playersData JSON from script
            match = _PLAYERS_DATA_RE.search(response.html_content)
            if not match:
                raise ValueError("No playersData found in Goyabu episode page")

            players = json.loads(match.group(1))
            for player in players:
                # Extract token from the direct blogger URL (blogger_token is base64-encoded)
                player_url = player.get("url", "")
                m = _TOKEN_RE.search(player_url)
                token = m.group(1) if m else ""

                if token:
                    video_url = resolve_blogger_token(token)
                    if store_player_source(container, event, video_url):
                        return

            raise ValueError("No playable video source found in Goyabu episode")
        except Exception as e:
            raise type(e)(f"Goyabu: {e}") from e


def load() -> None:
    load_plugin(Goyabu, rep.register)
