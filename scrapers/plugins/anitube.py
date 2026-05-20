import urllib.parse

import requests
from bs4 import BeautifulSoup

from scrapers.plugins.utils import load_plugin_if_supported, store_player_source
from services.repository import rep

class AniTube:
    languages = ["pt-br"]
    name = "anitube"
    base_url = "https://www.anitube.news"

    def search_anime(self, query: str) -> None:
        def _do_search(q: str) -> None:
            url = f"{self.base_url}/wp-json/wp/v2/posts?search={urllib.parse.quote(q)}&per_page=20"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = requests.get(url, headers=headers, timeout=30)
            results = response.json()
            for post in results:
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
                    rep.add_anime(title.strip(), link, self.name)

        _do_search(query)
        _do_search(f"{query} todos os episodios")

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        separator = "&" if "?" in url else "?"
        episodes_url = f"{url}{separator}ord=1"

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(episodes_url, headers=headers, timeout=30)
        response.raise_for_status()
        page = BeautifulSoup(response.text, "html.parser")

        episode_links = page.select("a[title*='Episódio']")
        titles = []
        urls = []
        for a in episode_links:
            href = a.get("href")
            title = a.get("title")
            if href and title and "anitube" in href:
                titles.append(title.strip())
                urls.append(href)

        rep.add_episode_list(anime, titles, urls, self.name)

    def search_player_src(self, url: str, container: list, event) -> None:
        try:
            with SeleniumWebDriver() as driver:
                page = driver.fetch(url)

            iframe = page.select_one("iframe")
            if iframe:
                src = iframe.get("src")
                if src and "api." in src:
                    if store_player_source(container, event, src):
                        return

            video = page.select_one("video")
            if video:
                video_src = video.get("src") or video.get("data-src")
                if video_src and "api." in video_src:
                    if store_player_source(container, event, video_src):
                        return

            source = page.select_one("video source")
            if source:
                src = source.get("src")
                if src and "api." in src:
                    if store_player_source(container, event, src):
                        return

            raise Exception("No video source found in AniTube episode page")
        except Exception as e:
            raise Exception(f"Could not extract video from AniTube: {e}") from e


def load(languages_dict) -> None:
    load_plugin_if_supported(AniTube, languages_dict, rep.register)
