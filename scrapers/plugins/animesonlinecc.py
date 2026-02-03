from scrapling import Fetcher, DynamicFetcher
from multiprocessing.pool import ThreadPool
from os import cpu_count

from services.repository import rep


class AnimesOnlineCC:
    languages = ["pt-br"]
    name = "animesonlinecc"

    def search_anime(self, query: str) -> None:
        url = "https://animesonlinecc.to/search/" + "+".join(query.split())
        fetcher = Fetcher()
        tree = fetcher.get(url)

        divs = tree.css("div.data")
        titles_urls = []
        titles = []
        for div in divs:
            n = div.css_first("h3 a")
            if not n:
                continue
            url = n.attrib.get("href")
            title = str(n.text)
            if not url or not title:
                continue
            titles_urls.append(url)
            titles.append(title)

        for title, url in zip(titles, titles_urls):
            rep.add_anime(title, url, AnimesOnlineCC.name)

        def parse_seasons(title, url):
            tree = fetcher.get(url)
            num_seasons = len(tree.css("div.se-c"))
            if num_seasons > 1:
                for n in range(2, num_seasons + 1):
                    rep.add_anime(
                        title + " Temporada " + str(n), url, AnimesOnlineCC.name, {"season": n}
                    )

        with ThreadPool(cpu_count()) as pool:
            for title, url in zip(titles, titles_urls):
                pool.apply(parse_seasons, args=(title, url))

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        fetcher = Fetcher()
        tree = fetcher.get(url)

        seasons = tree.css("ul.episodios")
        # Extract season number from params (backwards compatible with int)
        season = params if isinstance(params, int) else (params.get("season") if params else None)
        season_idx = season - 1 if season is not None else 0
        season_ul = seasons[season_idx] if season_idx < len(seasons) else seasons[0]

        urls, titles = [], []
        for div in season_ul.css("div.episodiotitle"):
            anchor = div.css_first("a")
            if anchor:
                urls.append(anchor.attrib.get("href"))
                titles.append(str(anchor.text))

        rep.add_episode_list(anime, titles, urls, AnimesOnlineCC.name)

    def search_player_src(self, url: str, container: list, event) -> None:
        try:
            # Use DynamicFetcher to render page and extract iframe
            # Use Firefox for better library compatibility
            page = DynamicFetcher.fetch(url, timeout=15000, browser="firefox")

            # Find iframe element
            iframe = page.css_first("iframe")
            if not iframe:
                raise Exception("iframe not found in animesonlinecc page.")

            link = iframe.attrib.get("src")
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
