from utils.logging import get_logger
import re
import urllib.parse

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

BASE_URL = "https://anroll.io"
HEADERS = DEFAULT_HEADERS
REQUEST_TIMEOUT = 15

_TITLE_DUB_HD_RE = re.compile(r"^(DUB|LEG)HD")
_TITLE_YEAR_RE = re.compile(r"\s*\d{4}$")
_TITLE_LEG_RE = re.compile(r"\s*\(?Legendado\)?\s*$", re.IGNORECASE)


class AnRoll:
    name = "anroll"
    base_url = BASE_URL

    def search_anime(self, query: str) -> list[AnimeMetadata]:
        results = []
        try:
            url = f"{BASE_URL}/?s={urllib.parse.quote(query)}"
            page = fetch(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            for article in page.css("article.anime-card", auto_save=True):
                a = article.css("a[href]").first
                if not a:
                    continue
                href = str(a.attrib.get("href", ""))
                if "/anime/" not in href or "episodio" in href:
                    continue
                img = a.css("img").first
                title = (
                    (img.attrib.get("alt") or "").strip() if img else a.get_all_text(strip=True)
                )
                title = _TITLE_DUB_HD_RE.sub("", title).strip()
                title = _TITLE_YEAR_RE.sub("", title).strip()
                title = _TITLE_LEG_RE.sub("", title).strip()
                if title and href:
                    results.append(AnimeMetadata(title=title, url=href, source=self.name))
        except FetchError as e:
            logger.debug("anroll search_anime falhou: %s", e)
        return results

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        _ = params
        try:
            soup = fetch(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            titles = []
            urls = []
            for a in soup.css("a.ep-text-item"):
                href = str(a.attrib.get("href", ""))
                ep_num = a.attrib.get("data-ep", "")
                if not href or not ep_num:
                    continue
                if not href.startswith("http"):
                    href = BASE_URL + href
                label = f"Ep.{int(ep_num):03d}"
                titles.append(label)
                urls.append(href)
            if not titles:
                first_ep_url = self._find_first_episode_url(soup)
                if first_ep_url:
                    titles, urls = self._episodes_from_sidebar(first_ep_url)
            if titles and urls:
                rep.add_episode_list(anime, titles, urls, self.name)
        except FetchError as e:
            logger.debug("anroll search_episodes falhou: %s", e)

    def _find_first_episode_url(self, soup) -> str | None:
        """Return the 'Primeiro Episódio' link from the anime page."""
        for anchor in soup.css("a[href]"):
            if "Primeiro" not in anchor.get_all_text(strip=True):
                continue
            href = str(anchor.attrib["href"])
            if re.search(r"/\d+/?$", href):
                return href if href.startswith("http") else f"{BASE_URL}{href}"
        return None

    def _episodes_from_sidebar(self, first_ep_url: str) -> tuple[list[str], list[str]]:
        """Fallback: scrape the episode sidebar from the first episode page.

        Anroll post IDs are global (not sequential per anime). The old range()
        fallback treated last_id - first_id as episode count, inflating lists to
        thousands. The sidebar on any episode page lists all episodes in order.
        """
        soup = fetch(first_ep_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

        sidebar = soup.css(".ep-list-box").first
        if sidebar is None:
            return [], []

        titles: list[str] = []
        urls: list[str] = []
        seen: set[str] = set()
        for anchor in sidebar.css("a[href]"):
            href = str(anchor.attrib["href"])
            if not re.match(rf"{re.escape(BASE_URL)}/\d+/?$", href):
                continue
            if href in seen:
                continue
            seen.add(href)
            ep_num = anchor.attrib.get("data-ep") or len(urls) + 1
            try:
                label = f"Ep.{int(ep_num):03d}"
            except ValueError:
                label = f"Ep.{len(urls) + 1:03d}"
            titles.append(label)
            urls.append(href)

        return titles, urls

    def search_player_src(self, url: str, container: list, event) -> None:
        # The anidrive player serves a "Bot Detected" placeholder (pro.mp4) unless
        # the page is loaded inside the trusted anroll parent (passing the Cloudflare
        # challenge sets the cookies that unlock the real googlevideo sources).
        # The real URL is also bound to the requesting User-Agent, so the browser must
        # use the SAME UA the video player (mpv) will replay it with.
        from scrapers.core.browser_check import INSTALL_HINT, browsers_available

        if not browsers_available():
            raise RuntimeError(f"Anroll indisponível: {INSTALL_HINT}")

        from scrapling.fetchers import StealthyFetcher

        captured: dict[str, str] = {}

        _JW_SOURCES_JS = """
            () => {
                try {
                    var pl = jwplayer().getPlaylist();
                    if (pl && pl[0] && pl[0].sources)
                        return pl[0].sources.map(function(s){ return s.file; });
                } catch(e) { return null; }
                return null;
            }
        """

        def _poll_jwplayer(page):
            for _ in range(40):
                if event.is_set():
                    return page
                for frame in page.frames:
                    if "anidrive" not in (frame.url or ""):
                        continue
                    try:
                        sources = frame.evaluate(_JW_SOURCES_JS)
                    except Exception:
                        sources = None
                    if sources:
                        real = [s for s in sources if s and "pro.mp4" not in s]
                        if real:
                            captured["url"] = real[0]
                            return page
                page.wait_for_timeout(500)
            return page

        try:
            StealthyFetcher.fetch(
                url,
                headless=True,
                solve_cloudflare=True,
                useragent=HEADERS["User-Agent"],
                page_action=_poll_jwplayer,
                timeout=90000,
            )

            video_url = captured.get("url")
            if not video_url:
                raise ValueError("Anroll: real video source not resolved (bot detected)")

            if store_player_source(container, event, video_url):
                return

            raise ValueError("Anroll: failed to store video source")
        except Exception as e:
            raise type(e)(f"Anroll: {e}") from e


def load() -> None:
    load_plugin(AnRoll, rep.register)
