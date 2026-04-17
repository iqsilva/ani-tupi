import re

import requests
from bs4 import BeautifulSoup

from scrapers.core.selenium_driver import SeleniumWebDriver
from scrapers.plugins.utils import load_plugin_if_supported, store_player_source
from services.repository import rep

BASE_URL = "https://www.dattebayo-br.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
}
REQUEST_TIMEOUT = 30


def _extract_episode_number(text: str) -> int:
    match = re.search(r"epis[oó]dio\s*(\d+)", text.lower())
    if match:
        return int(match.group(1))
    match = re.search(r"\bep\s*(\d+)\b", text.lower())
    if match:
        return int(match.group(1))
    match = re.search(r"(\d+)", text)
    if match:
        return int(match.group(1))
    return 0


class DattebayoBR:
    languages = ["pt-br"]
    name = "dattebayo"
    base_url = BASE_URL

    def search_anime(self, query: str) -> None:
        url = f"{BASE_URL}/busca?busca={requests.utils.quote(query)}"
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for item in soup.select(".ultimosAnimesHomeItem"):
            anchor = item.select_one("a")
            if not anchor:
                continue
            href = str(anchor.get("href", ""))
            if not href.startswith("http"):
                href = BASE_URL + href
            title_el = item.select_one(".ultimosAnimesHomeItemInfosNome")
            title = title_el.text.strip() if title_el else ""
            if title and href:
                rep.add_anime(title, href, self.name)

    def _fetch_episode_page(self, url: str) -> list[tuple[str, str]]:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        results = []
        for item in soup.select(".ultimosEpisodiosHomeItem"):
            anchor = item.select_one("a")
            if not anchor:
                continue
            href = str(anchor.get("href", ""))
            if not href.startswith("http"):
                href = BASE_URL + href
            name_el = item.select_one(".ultimosEpisodiosHomeItemInfosNome")
            title = name_el.text.strip() if name_el else anchor.get("title", "")
            if title and href:
                results.append((title, href))
        return results

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
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
        deduped = []
        for t, u in all_items:
            n = _extract_episode_number(t)
            if n > 0 and n not in seen:
                seen.add(n)
                deduped.append((t, u))
        paired = sorted(deduped, key=lambda x: _extract_episode_number(x[0]))
        if paired:
            titles, urls = zip(*paired)
            rep.add_episode_list(anime, list(titles), list(urls), self.name)

    def search_player_src(self, url: str, container: list, event) -> None:
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By

        driver = SeleniumWebDriver(timeout=60)
        try:
            driver.driver.get(url)
            try:
                WebDriverWait(driver.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#jwContainer_0"))
                )
            except Exception:
                pass
            candidates = driver.driver.execute_script("""
                var containers = ['jwContainer_2', 'jwContainer_1', 'jwContainer_0'];
                var urls = [];
                for (var i = 0; i < containers.length; i++) {
                    try {
                        var f = jwplayer(containers[i]).getPlaylistItem().file;
                        if (f) urls.push(f);
                    } catch(e) {}
                }
                return urls;
            """)
        finally:
            driver.close()

        if not candidates:
            return

        for candidate in candidates:
            try:
                r = requests.get(
                    candidate,
                    headers={**HEADERS, "Range": "bytes=0-0"},
                    timeout=10,
                    stream=True,
                )
                if r.status_code in (200, 206):
                    if store_player_source(container, event, candidate):
                        return
            except Exception:
                continue


def load(languages_dict) -> None:
    load_plugin_if_supported(DattebayoBR, languages_dict, rep.register)
