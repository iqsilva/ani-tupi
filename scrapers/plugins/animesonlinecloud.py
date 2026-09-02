import re
import urllib.parse

from models.models import AnimeMetadata
from scrapers.plugins.utils import (
    DEFAULT_HEADERS,
    FetchError,
    fetch,
    load_plugin,
    store_player_source,
)
from services.repository import rep
from utils.logging import get_logger

logger = get_logger(__name__)

BASE_URL = "https://animesonline.cloud"
HEADERS = DEFAULT_HEADERS
REQUEST_TIMEOUT = 20

_PLAYER_OPTION_RE = re.compile(r"data-type='([^']+)' data-post='(\d+)' data-nume='([^']+)'")
_EPISODE_NUM_RE = re.compile(r"-episodio-(\d+)/?$")


class AnimesOnlineCloud:
    name = "animesonlinecloud"
    base_url = BASE_URL

    def search_anime(self, query: str) -> list[AnimeMetadata]:
        results = []
        try:
            url = f"{BASE_URL}/?s={urllib.parse.quote(query)}"
            page = fetch(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            for article in page.css("article", auto_save=True):
                a = article.css(".details .title a[href*='/anime/']").first
                if not a:
                    continue
                title = a.get_all_text(strip=True)
                link = a.attrib.get("href", "")
                if title and link:
                    results.append(AnimeMetadata(title=title, url=link, source=self.name))
        except FetchError as e:
            logger.debug(f"AnimesOnlineCloud search request failed for '{query}': {e}")
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
                num_match = _EPISODE_NUM_RE.search(ep_url)
                if not ep_url.startswith("http") or not num_match or ep_url in seen:
                    continue
                seen.add(ep_url)
                title = a.get_all_text(strip=True) or f"Episódio {int(num_match.group(1))}"
                titles.append(title)
                urls.append(ep_url)

            if titles and urls:
                rep.add_episode_list(anime, titles, urls, self.name)
        except FetchError as e:
            logger.debug(f"AnimesOnlineCloud episode fetch failed for '{anime}': {e}")

    def search_player_src(self, url: str, container: list, event) -> None:
        try:
            r = fetch(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

            found = False
            for typ, post, nume in _PLAYER_OPTION_RE.findall(r.html_content):
                embed = self._dooplayer_embed(url, post, typ, nume)
                if not embed:
                    continue
                if embed.get("type") == "mp4":
                    if source := self._decode_source(embed.get("embed_url", "")):
                        if store_player_source(container, event, source):
                            found = True

            if not found:
                raise ValueError("No playable source in AnimesOnlineCloud episode page")
        except Exception as e:
            raise type(e)(f"AnimesOnlineCloud: {e}") from e

    def _dooplayer_embed(self, referer: str, post: str, typ: str, nume: str) -> dict | None:
        api = f"{BASE_URL}/wp-json/dooplayer/v2/{post}/{typ}/{nume}"
        try:
            r = fetch(
                api,
                headers={**HEADERS, "Referer": referer},
                timeout=REQUEST_TIMEOUT,
            )
            return r.json()
        except (FetchError, ValueError) as e:
            logger.debug(f"AnimesOnlineCloud dooplayer API failed ({post}/{typ}/{nume}): {e}")
            return None

    @staticmethod
    def _decode_source(embed_url: str) -> str | None:
        """Decode the `source` param of a jwplayer embed (direct .mp4 or signed HLS)."""
        query = urllib.parse.urlparse(embed_url).query
        source = urllib.parse.parse_qs(query).get("source", [""])[0]
        return urllib.parse.unquote(source) or None


def load() -> None:
    load_plugin(AnimesOnlineCloud, rep.register)
