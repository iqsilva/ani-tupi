from utils.logging import get_logger
import urllib.parse

from scrapers.plugins.utils import (
    DEFAULT_HEADERS,
    FetchError,
    extract_anivideo_hls,
    fetch,
    load_plugin,
    store_player_source,
)
from models.models import AnimeMetadata
from services.repository import rep

logger = get_logger(__name__)

HEADERS = DEFAULT_HEADERS


class AniTube:
    name = "anitube"
    base_url = "https://www.anitube.zip"

    def search_anime(self, query: str) -> list[AnimeMetadata]:
        collected: list[AnimeMetadata] = []

        def _do_search(q: str) -> None:
            try:
                url = f"{self.base_url}/wp-json/wp/v2/posts?search={urllib.parse.quote(q)}&per_page=20"
                response = fetch(url, headers=HEADERS, timeout=30)
                posts = response.json()
            except FetchError as e:
                logger.debug(f"AniTube search request failed for '{q}': {e}")
                return
            for post in posts:
                title = post.get("title", {}).get("rendered", "")
                link = post.get("link", "")
                if title and link:
                    lower_title = title.lower()
                    if "episódio" in lower_title and "todos" not in lower_title:
                        if " – ep" in lower_title or "episódio " in lower_title:
                            continue
                    title = (
                        title.replace(" – Todos os Episódios", "")
                        .replace(" – Todos Episódios", "")
                        .replace(" todos os episodios", "")
                        .replace(" todos episodios", "")
                        .replace("&#8211;", "–")
                    )
                    collected.append(AnimeMetadata(title=title.strip(), url=link, source=self.name))

        _do_search(query)
        _do_search(f"{query} todos os episodios")
        return collected

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        _ = params
        try:
            separator = "&" if "?" in url else "?"
            episodes_url = f"{url}{separator}ord=1"

            response = fetch(episodes_url, headers=HEADERS, timeout=30)
            page = response

            episode_links = page.css("a[title*='Episódio']")
            titles = []
            urls = []
            for a in episode_links:
                href = a.attrib.get("href")
                title = a.attrib.get("title")
                if href and title and href.startswith("http"):
                    titles.append(title.strip())
                    urls.append(href)

            rep.add_episode_list(anime, titles, urls, self.name)
        except FetchError as e:
            logger.debug(f"AniTube episode fetch failed for '{anime}': {e}")
            return

    def search_player_src(self, url: str, container: list, event) -> None:
        try:
            response = fetch(url, headers=HEADERS, timeout=30)
            html = response.html_content

            if hls_url := extract_anivideo_hls(html):
                store_player_source(container, event, hls_url)

            if container:
                return

            raise Exception("No playable video source found in AniTube episode page")
        except FetchError as e:
            raise Exception(f"Could not extract video from AniTube: {e}") from e


def load() -> None:
    load_plugin(AniTube, rep.register)
