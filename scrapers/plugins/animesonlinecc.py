from scrapers.core.selenium_driver import SeleniumWebDriver
from scrapers.plugins.utils import load_plugin_if_supported, store_player_source
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

        store_player_source(container, event, link)


def load(languages_dict) -> None:
    load_plugin_if_supported(AnimesOnlineCC, languages_dict, rep.register)
