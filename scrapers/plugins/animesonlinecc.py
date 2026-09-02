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

BASE_URL = "https://animesonlinecc.to"
HEADERS = DEFAULT_HEADERS
REQUEST_TIMEOUT = 15

_EPISODE_NUM_RE = re.compile(r"-episodio-(\d+)/?$")
_TOKEN_RE = re.compile(r"token=([^&\s\"']+)")


class AnimesOnlineCC:
    name = "animesonlinecc"
    base_url = BASE_URL

    def search_anime(self, query: str) -> list[AnimeMetadata]:
        results = []
        try:
            url = f"{BASE_URL}/search/{urllib.parse.quote(query)}"
            page = fetch(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            for article in page.css("article", auto_save=True):
                a = article.css("a[href*='/anime/']").first
                if not a:
                    continue
                title_el = article.css("h2, h3").first
                title = (
                    title_el.get_all_text(strip=True)
                    if title_el
                    else a.get_all_text(strip=True)
                )
                link = a.attrib.get("href", "")
                if title and link:
                    results.append(AnimeMetadata(title=title, url=link, source=self.name))
        except FetchError as e:
            logger.debug(f"AnimesOnlineCC search request failed for '{query}': {e}")
        return results

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        _ = params
        try:
            page = fetch(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

            seen = set()
            titles = []
            urls = []
            for a in page.css("a[href*='/episodio/']"):
                ep_url = str(a.attrib.get("href", ""))
                if ep_url.startswith("//"):
                    ep_url = "https:" + ep_url
                num_match = _EPISODE_NUM_RE.search(ep_url)
                # Skip nav links (no episode number) and relative URLs
                if not ep_url.startswith("http") or not num_match or ep_url in seen:
                    continue
                seen.add(ep_url)
                title = a.get_all_text(strip=True) or f"Episódio {num_match.group(1)}"
                titles.append(title)
                urls.append(ep_url)

            if titles and urls:
                rep.add_episode_list(anime, titles, urls, self.name)
        except FetchError as e:
            logger.debug(f"AnimesOnlineCC episode fetch failed for '{anime}': {e}")

    def search_player_src(self, url: str, container: list, event) -> None:
        try:
            page = fetch(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

            iframes = page.css("iframe[src*='blogger.com/video.g']")
            if not iframes:
                raise ValueError("No blogger iframe found in AnimesOnlineCC episode page")

            for iframe in iframes:
                src = iframe.attrib.get("src", "")
                m = _TOKEN_RE.search(src)
                if not m:
                    continue
                token = m.group(1)
                try:
                    video_url = resolve_blogger_token(token)
                except Exception as e:
                    logger.debug(f"AnimesOnlineCC blogger token resolve failed, trying next: {e}")
                    continue
                if store_player_source(container, event, video_url):
                    return

            raise ValueError("No playable blogger source in AnimesOnlineCC episode page")
        except Exception as e:
            raise type(e)(f"AnimesOnlineCC: {e}") from e


def load() -> None:
    load_plugin(AnimesOnlineCC, rep.register)
