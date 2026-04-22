import re
import urllib.parse

import requests
from bs4 import BeautifulSoup

from scrapers.plugins.utils import load_plugin_if_supported, store_player_source
from services.repository import rep


BASE_URL = "https://sushianimes.com.br"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
}
REQUEST_TIMEOUT = 30


def _normalize_url(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return f"{BASE_URL}{href}"


def _extract_season_number(text: str) -> int:
    match = re.search(r"(?:temporada|season)\s*(\d+)", text.lower())
    if match:
        return int(match.group(1))
    match = re.search(r"(?:^|\D)(\d+)(?:º|ª)?\s*(?:temporada|season)", text.lower())
    if match:
        return int(match.group(1))
    match = re.search(r"(?:^|\D)(\d+)(?:º|ª)?", text.lower())
    if match:
        return int(match.group(1))
    return 1


def _build_result_title(title: str, season: int) -> str:
    normalized = title.strip()
    audio_suffix = ""

    if re.search(r"\bdublado\b", normalized, re.IGNORECASE):
        audio_suffix = " - Dublado"
    elif re.search(r"\blegendado\b", normalized, re.IGNORECASE):
        audio_suffix = " - Legendado"

    base_title = re.sub(r"\s*[(-]?\s*(dublado|legendado)\s*[)]?\s*", " ", normalized, flags=re.I)
    base_title = re.sub(r"\s+", " ", base_title).strip()

    if season > 1:
        return f"{base_title} {season}{audio_suffix}"
    return f"{base_title}{audio_suffix}"


class SushiAnimes:
    languages = ["pt-br"]
    name = "sushianimes"
    base_url = BASE_URL

    def _search_page(self, query: str) -> BeautifulSoup:
        url = f"{BASE_URL}/search/{urllib.parse.quote(query)}"
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def _fetch_anime_page(self, url: str) -> BeautifulSoup:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def search_anime(self, query: str) -> None:
        soup = self._search_page(query)
        anime_items = soup.select("#animes .list-movie")

        for item in anime_items:
            anchor = item.select_one("a.list-title") or item.select_one("a.list-media")
            if not anchor:
                continue

            title = anchor.get_text(strip=True)
            href = anchor.get("href")
            if not title or not href:
                continue

            anime_url = _normalize_url(href)
            anime_page = self._fetch_anime_page(anime_url)
            season_panes = anime_page.select(".episodes.tab-content .tab-pane[id^='season-']")

            if len(season_panes) <= 1:
                rep.add_anime(_build_result_title(title, 1), anime_url, self.name, {"season": 1})
                continue

            for pane in season_panes:
                season_id = pane.get("id", "season-1")
                season = _extract_season_number(season_id)
                season_title = _build_result_title(title, season)
                rep.add_anime(season_title, anime_url, self.name, {"season": season})

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        season = None
        if isinstance(params, dict):
            season = params.get("season")
        if not season:
            season = _extract_season_number(anime)

        season_pane = soup.select_one(f".episodes.tab-content .tab-pane#season-{season}")
        if season_pane is None:
            season_pane = soup.select_one(".episodes.tab-content .tab-pane")
        if season_pane is None:
            return

        titles: list[str] = []
        urls: list[str] = []
        for episode in season_pane.select("a[href*='/anime/']"):
            href = episode.get("href")
            if not href:
                continue

            episode_title = episode.get("title", "").strip()
            name_el = episode.select_one(".name")
            episode_name = name_el.get_text(" ", strip=True) if name_el else ""
            full_title = f"{episode_title} {episode_name}".strip()

            titles.append(full_title)
            urls.append(_normalize_url(href))

        if titles and urls:
            rep.add_episode_list(anime, titles, urls, self.name, season=season)

    def search_player_src(self, url: str, container: list, event) -> None:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        embed_button = soup.select_one(".btn-service.selected[data-embed]")
        if embed_button is None:
            embed_button = soup.select_one("[data-embed]")
        if embed_button is None:
            return

        embed_id = embed_button.get("data-embed")
        if not embed_id:
            return

        embed_response = requests.post(
            f"{BASE_URL}/ajax/embed",
            data={"id": embed_id},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        embed_response.raise_for_status()

        match = re.search(r'var\s+playerEmbed\s*=\s*"([^"]+)"', embed_response.text)
        if not match:
            return

        player_url = match.group(1).replace("\\/", "/")
        store_player_source(container, event, player_url)


def load(languages_dict) -> None:
    load_plugin_if_supported(SushiAnimes, languages_dict, rep.register)
