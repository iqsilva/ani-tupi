"""Dattebayo BR scraper — search, episode listing, and signed R2 playback URLs."""

from __future__ import annotations

import re
import urllib.parse
from utils.logging import get_logger

from models.models import AnimeMetadata
from scrapers.plugins.utils import (
    DEFAULT_HEADERS,
    FetchError,
    fetch,
    load_plugin,
    store_player_source,
)
from services.repository import rep

logger = get_logger(__name__)

BASE_URL = "https://www.dattebayo-br.com"
R2_BASE = "https://842e802996826993acdd6d2f7385b287.r2.cloudflarestorage.com"
SIGN_API = "https://ads.animeyabu.net/"
HEADERS = DEFAULT_HEADERS
REQUEST_TIMEOUT = 20

VIDEO_ID_RE = re.compile(r"/videos/(\d+)")
QUALITY_PATHS = {
    "fullhd": "fful",
    "hd": "f333",
    "sd": "fiphonec",
}
PLAYBACK_QUALITIES = ("fullhd", "hd", "sd")


def _extract_episode_number(text: str) -> int:
    lowered = text.lower()
    for pattern in (
        r"epis[oó]dio\s*(\d+)",
        r"\bep\s*(\d+)\b",
        r"(\d+)",
    ):
        if match := re.search(pattern, lowered):
            return int(match.group(1))
    return 0


def _absolute_url(href: str) -> str:
    if href.startswith("http"):
        return href
    return urllib.parse.urljoin(BASE_URL, href)


def _request_headers(referer: str) -> dict[str, str]:
    return {
        **HEADERS,
        "Referer": referer,
        "Origin": BASE_URL,
    }


def extract_video_id(episode_url: str) -> str:
    match = VIDEO_ID_RE.search(episode_url)
    if not match:
        raise ValueError(f"URL de episódio inválida (esperado .../videos/{{id}}): {episode_url}")
    return match.group(1)


def unsigned_video_url(video_id: str, *, quality: str = "fullhd") -> str:
    path = QUALITY_PATHS.get(quality)
    if not path:
        raise ValueError(f"Qualidade inválida: {quality!r}")
    return f"{R2_BASE}/{path}/{video_id}.mp4"


def sign_video_url(
    unsigned_url: str,
    *,
    referer: str,
) -> str:
    sign_url = f"{SIGN_API}?url={urllib.parse.quote(unsigned_url, safe='')}"
    response = fetch(sign_url, headers=_request_headers(referer), timeout=REQUEST_TIMEOUT)

    payload = response.json()
    if not payload or not isinstance(payload, list):
        raise ValueError("Resposta inesperada da API de assinatura")

    query = payload[0].get("publicidade")
    if not query:
        raise ValueError("API de assinatura não retornou publicidade")

    return unsigned_url + (query if query.startswith("?") else f"?{query}")


def _is_playable(video_url: str, *, referer: str) -> bool:
    try:
        response = fetch(
            video_url,
            headers={**_request_headers(referer), "Range": "bytes=0-0"},
            timeout=10,
            raise_for_status=False,
        )
        return response.status in (200, 206)
    except FetchError:
        return False


def resolve_signed_video_url(
    episode_url: str,
    *,
    qualities: tuple[str, ...] = PLAYBACK_QUALITIES,
) -> str:
    video_id = extract_video_id(episode_url)
    for quality in qualities:
        unsigned = unsigned_video_url(video_id, quality=quality)
        try:
            signed = sign_video_url(unsigned, referer=episode_url)
        except (FetchError, ValueError) as exc:
            logger.debug("Dattebayo sign failed for %s (%s): %s", video_id, quality, exc)
            continue
        if _is_playable(signed, referer=episode_url):
            return signed
    raise ValueError(f"Nenhuma fonte reproduzível encontrada para {episode_url}")


def _parse_anime_items(page) -> list[AnimeMetadata]:
    results: list[AnimeMetadata] = []
    seen: set[str] = set()

    for item in page.css(".ultimosAnimesHomeItem", auto_save=True):
        anchor = item.css("a[href*='/animes/']").first
        if not anchor:
            continue
        href = _absolute_url(str(anchor.attrib.get("href", "")))
        if "/letra/" in href or href in seen:
            continue
        title_el = item.css(".ultimosAnimesHomeItemInfosNome").first
        title = (
            title_el.get_all_text(strip=True) if title_el else anchor.get_all_text(strip=True)
        )
        if title and href:
            seen.add(href)
            results.append(AnimeMetadata(title=title, url=href, source="dattebayo"))
    return results


def _parse_episode_items(page) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    for item in page.css(".ultimosEpisodiosHomeItem"):
        anchor = item.css("a[href*='/videos/']").first
        if not anchor:
            continue
        href = _absolute_url(str(anchor.attrib.get("href", "")))
        name_el = item.css(".ultimosEpisodiosHomeItemInfosNome").first
        title = (
            name_el.get_all_text(strip=True)
            if name_el
            else str(anchor.attrib.get("title", "")).strip()
        )
        if title and href:
            results.append((title, href))
    return results


class Dattebayo:
    name = "dattebayo"
    base_url = BASE_URL

    def search_anime(self, query: str) -> list[AnimeMetadata]:
        try:
            url = f"{BASE_URL}/busca?busca={urllib.parse.quote(query)}"
            page = fetch(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            return _parse_anime_items(page)
        except FetchError as exc:
            logger.debug("Dattebayo search_anime failed for %r: %s", query, exc)
            return []

    def list_animes(self, page: int = 1) -> list[AnimeMetadata]:
        """Lista animes do catálogo (/animes), paginado."""
        try:
            if page <= 1:
                url = f"{BASE_URL}/animes"
            else:
                url = f"{BASE_URL}/animes/page/{page}"
            result = fetch(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            return _parse_anime_items(result)
        except FetchError as exc:
            logger.debug("Dattebayo list_animes failed for page %s: %s", page, exc)
            return []

    def _fetch_episode_page(self, url: str) -> list[tuple[str, str]]:
        page = fetch(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        return _parse_episode_items(page)

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        _ = params
        try:
            all_items: list[tuple[str, str]] = []
            page = 1
            while True:
                page_url = url if page == 1 else f"{url.rstrip('/')}/page/{page}"
                items = self._fetch_episode_page(page_url)
                if not items:
                    break
                all_items.extend(items)
                page += 1

            seen: set[int] = set()
            deduped: list[tuple[str, str]] = []
            for title, episode_url in all_items:
                number = _extract_episode_number(title)
                if number > 0 and number not in seen:
                    seen.add(number)
                    deduped.append((title, episode_url))

            paired = sorted(deduped, key=lambda item: _extract_episode_number(item[0]))
            if paired:
                titles, urls = zip(*paired, strict=True)
                rep.add_episode_list(anime, list(titles), list(urls), self.name)
        except FetchError as exc:
            logger.debug("Dattebayo search_episodes failed for %r: %s", anime, exc)

    def search_player_src(self, url: str, container: list, event) -> None:
        try:
            video_url = resolve_signed_video_url(url)
            if store_player_source(container, event, video_url):
                return
            raise ValueError("Falha ao armazenar fonte de vídeo do Dattebayo")
        except Exception as exc:
            raise type(exc)(f"Dattebayo: {exc}") from exc


def load() -> None:
    load_plugin(Dattebayo, rep.register)
