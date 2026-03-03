import re
import urllib.parse

import requests
from playwright.sync_api import sync_playwright
from scrapling.fetchers import DynamicFetcher

from services.repository import rep


def _extract_episode_number(title: str) -> int | None:
    match = re.search(r"epis[óo]dio\s*(\d+)", title.lower())
    if match:
        return int(match.group(1))
    return None


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
        anime_base = (
            anime.lower()
            .replace("todos os episódios", "")
            .replace("todos episodios", "")
            .replace("– todos episódios", "")
            .replace("- todos episodios", "")
            .strip()
        )
        episodes_url = f"{url}?ord=1"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(episodes_url)
            page.wait_for_load_state("networkidle", timeout=30000)

            episode_links = page.query_selector_all("a[title*='Episódio']")
            titles = []
            urls = []
            for a in episode_links:
                href = a.get_attribute("href")
                title = a.get_attribute("title")
                if href and title and "anitube" in href:
                    title_lower = title.lower()
                    if anime_base in title_lower:
                        titles.append(title.strip())
                        urls.append(href)
            browser.close()

        if titles and urls:
            first_ep_num = _extract_episode_number(titles[0])
            if first_ep_num is not None and len(titles) > 1:
                second_ep_num = _extract_episode_number(titles[1])
                if second_ep_num is not None and first_ep_num > second_ep_num:
                    titles = list(reversed(titles))
                    urls = list(reversed(urls))

        rep.add_episode_list(anime, titles, urls, self.name)

    def search_player_src(self, url: str, container: list, event) -> None:
        try:
            page = DynamicFetcher.fetch(url, timeout=20000)
            iframe_results = page.css("iframe")
            iframe = iframe_results[0] if iframe_results else None
            if iframe:
                src = iframe.attrib.get("src")
                if src:
                    if not event.is_set():
                        container.append(src)
                        event.set()
                    return
            video_results = page.css("video")
            video = video_results[0] if video_results else None
            if video:
                video_src = video.attrib.get("src") or video.attrib.get("data-src")
                if video_src:
                    if not event.is_set():
                        container.append(video_src)
                        event.set()
                    return
            source_results = page.css("video source")
            source = source_results[0] if source_results else None
            if source:
                src = source.attrib.get("src")
                if src:
                    if not event.is_set():
                        container.append(src)
                        event.set()
                    return
            raise Exception("No video source found in AniTube episode page")
        except Exception as e:
            raise Exception(f"Could not extract video from AniTube: {e}") from e


def load(languages_dict) -> None:
    can_load = False
    for language in AniTube.languages:
        if language in languages_dict:
            can_load = True
            break
    if not can_load:
        return
    rep.register(AniTube())
