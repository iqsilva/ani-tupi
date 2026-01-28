from selectolax.parser import HTMLParser
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from multiprocessing.pool import ThreadPool
from os import cpu_count

from scrapers.core.browser_pool import get_browser_pool

from scrapers.plugins.utils import get_with_retry
from services.repository import rep


class AnimesOnlineCC:
    languages = ["pt-br"]
    name = "animesonlinecc"

    def search_anime(self, query: str) -> None:
        url = "https://animesonlinecc.to/search/" + "+".join(query.split())
        response = get_with_retry(url)
        tree = HTMLParser(response.text)

        divs = tree.css("div.data")
        titles_urls = []
        titles = []
        for div in divs:
            n = div.css_first("h3 a")
            if not n:
                continue
            url = n.attributes.get("href")
            title = n.text()
            if not url or not title:
                continue
            titles_urls.append(url)
            titles.append(title)

        for title, url in zip(titles, titles_urls):
            rep.add_anime(title, url, AnimesOnlineCC.name)

        def parse_seasons(title, url):
            response = get_with_retry(url)
            tree = HTMLParser(response.text)
            num_seasons = len(tree.css("div.se-c"))
            if num_seasons > 1:
                for n in range(2, num_seasons + 1):
                    rep.add_anime(title + " Temporada " + str(n), url, AnimesOnlineCC.name, n)

        with ThreadPool(cpu_count()) as pool:
            for title, url in zip(titles, titles_urls):
                pool.apply(parse_seasons, args=(title, url))

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        response = get_with_retry(url)
        tree = HTMLParser(response.text)

        seasons = tree.css("ul.episodios")
        # Extract season number from params (backwards compatible with int)
        season = params if isinstance(params, int) else (params.get("season") if params else None)
        season_idx = season - 1 if season is not None else 0
        season_ul = seasons[season_idx] if season_idx < len(seasons) else seasons[0]

        urls, titles = [], []
        for div in season_ul.css("div.episodiotitle"):
            anchor = div.css_first("a")
            if anchor:
                urls.append(anchor.attributes.get("href"))
                titles.append(anchor.text())

        rep.add_episode_list(anime, titles, urls, AnimesOnlineCC.name)

    def search_player_src(self, url: str, container: list, event) -> None:
        try:
            with get_browser_pool().get_browser() as driver:
                driver.get(url)
                try:
                    xpath = "/html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[1]/div[1]/iframe"
                    params = (By.XPATH, xpath)
                    WebDriverWait(driver, 7).until(EC.visibility_of_all_elements_located(params))
                except Exception:
                    msg = "iframe not found in animesonlinecc page."
                    raise Exception(msg)

                product = driver.find_element(params[0], params[1])
                link = str(product.get_property("src"))
        except Exception as e:
            if "Firefox" in str(e):
                msg = "Firefox not installed or browser pool failed."
                raise Exception(msg)
            else:
                raise

        if not event.is_set():
            container.append(link)
            event.set()


def load(languages_dict) -> None:
    can_load = False
    for language in AnimesOnlineCC.languages:
        if language in languages_dict:
            can_load = True
            break
    if not can_load:
        return
    rep.register(AnimesOnlineCC())
