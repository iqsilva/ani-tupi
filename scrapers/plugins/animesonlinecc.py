from multiprocessing.pool import ThreadPool
from os import cpu_count

from scrapers.core.selenium_driver import SeleniumWebDriver
from services.repository import rep


class AnimesOnlineCC:
    languages = ["pt-br"]
    name = "animesonlinecc"

    def search_anime(self, query: str) -> None:
        url = "https://animesonlinecc.to/search/" + "+".join(query.split())
        with SeleniumWebDriver() as driver:
            tree = driver.fetch(url)

        divs = tree.select("div.data")
        titles_urls = []
        titles = []
        for div in divs:
            anchor = div.select_one("h3 a")
            if not anchor:
                continue
            url = anchor.get("href")
            title = str(anchor.text)
            if not url or not title:
                continue
            titles_urls.append(url)
            titles.append(title)

        for title, url in zip(titles, titles_urls):
            rep.add_anime(title, url, AnimesOnlineCC.name)

        def parse_seasons(title, url):
            with SeleniumWebDriver() as driver:
                tree = driver.fetch(url)
            num_seasons = len(tree.select("div.se-c"))
            if num_seasons > 1:
                for n in range(2, num_seasons + 1):
                    rep.add_anime(
                        title + " Temporada " + str(n),
                        url,
                        AnimesOnlineCC.name,
                        {"season": n},
                    )

        with ThreadPool(cpu_count()) as pool:
            for title, url in zip(titles, titles_urls):
                pool.apply(parse_seasons, args=(title, url))

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        with SeleniumWebDriver() as driver:
            tree = driver.fetch(url)

        seasons = tree.select("ul.episodios")
        # Extract season number from params (backwards compatible with int)
        season = params if isinstance(params, int) else (params.get("season") if params else None)
        season_idx = season - 1 if season is not None else 0
        season_ul = seasons[season_idx] if season_idx < len(seasons) else seasons[0]

        urls, titles = [], []
        for div in season_ul.select("div.episodiotitle"):
            anchor = div.select_one("a")
            if anchor:
                urls.append(anchor.get("href"))
                titles.append(str(anchor.text))

        rep.add_episode_list(anime, titles, urls, AnimesOnlineCC.name)

    def search_player_src(self, url: str, container: list, event) -> None:
        try:
            with SeleniumWebDriver() as driver:
                page = driver.fetch(url)

            # Find iframe element
            iframe = page.select_one("iframe")
            if not iframe:
                raise Exception("iframe not found in animesonlinecc page.")

            link = iframe.get("src")
            if not link:
                raise Exception("iframe src attribute not found")

        except Exception as e:
            raise Exception(f"Could not extract video from AnimesonlineCC: {e}") from e

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
