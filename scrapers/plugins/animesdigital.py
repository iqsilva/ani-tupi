from scrapling import Fetcher, DynamicFetcher

from services.repository import rep

# Request timeout for all AnimesDigital API calls (seconds)
# Increased to 30s to handle slow network conditions
REQUEST_TIMEOUT = 30


class AnimesDigital:
    languages = ["pt-br"]
    name = "animesdigital"

    def search_anime(self, query) -> None:
        """Search for anime on AnimesDigital.

        Constructs search URL and extracts anime titles and links.
        Prioritizes subtitled versions over dubbed versions when both exist.
        """
        url = "https://animesdigital.org/search/" + "+".join(query.split())
        fetcher = Fetcher()
        tree = fetcher.get(url, timeout=REQUEST_TIMEOUT)

        # Extract all anime links
        anime_links = tree.css("a[href*='/anime/']")
        titles = []
        urls = []

        for link in anime_links:
            href = link.attrib.get("href")
            title = str(link.text).strip()

            # Clean up title (remove extra whitespace and special chars)
            title = " ".join(title.split())

            if href and title:
                urls.append(href)
                titles.append(title)

        titled_urls = list(zip(titles, urls))

        # Add anime to repository in priority order
        for title, url in titled_urls:
            rep.add_anime(title, url, AnimesDigital.name)

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        """Fetch episode list from anime page.

        Ensures all episodes are displayed by adding ?odr=1 parameter.
        Extracts episodes from the detail page using div.item_ep selector.
        Filters out special episodes (fractionated like 13.5) to avoid duplicates.
        """
        import re

        # Ensure ?odr=1 parameter is present to show all episodes
        if "?" in url:
            if "odr=" not in url:
                url = url + "&odr=1"
        else:
            url = url + "?odr=1"

        fetcher = Fetcher()
        tree = fetcher.get(url, timeout=REQUEST_TIMEOUT)

        # Find all episode containers
        episode_divs = tree.css("div.item_ep")

        episode_titles = []
        episode_urls = []

        for ep_div in episode_divs:
            # Find the link inside the episode div for the URL
            link = ep_div.css_first("a")
            href = None
            if link:
                href = link.attrib.get("href")

            # Get episode title from .title_anime class (avoids metadata like "9 meses atrás")
            title_elem = ep_div.css_first(".title_anime")
            if title_elem and href:
                title = str(title_elem.text).strip()
                # Clean up extra whitespace
                title = " ".join(title.split())
                if title:
                    # Filter out special episodes (fractionated like 13.5, 0.5, etc)
                    # These are OVAs/specials that shouldn't be counted as main episodes
                    if re.search(r"Episódio\s+\d+\.\d+", title):
                        continue  # Skip special episodes
                    episode_urls.append(href)
                    episode_titles.append(title)

        # Add episodes to repository
        rep.add_episode_list(anime, episode_titles, episode_urls, AnimesDigital.name)

    def search_player_src(self, url: str, container: list, event) -> None:
        """Extract video URL from episode player.

        AnimesDigital loads iframes dynamically via JavaScript.
        Uses DynamicFetcher to render the page and extract iframe sources.
        Prioritizes api.anivideo.net iframes which are most reliable.
        """
        try:
            df = DynamicFetcher()
            page = df.fetch(url, timeout=10)

            # Extract all iframes
            iframes = page.css("iframe")

            if not iframes:
                raise Exception("No iframe found in AnimesDigital episode page.")

            # Priority 1: Look for api.anivideo.net iframes (most reliable)
            for iframe in iframes:
                src = iframe.attrib.get("src")
                if src and "api.anivideo.net" in src:
                    if not event.is_set():
                        container.append(src)
                        event.set()
                    return

            # Priority 2: Look for m3u8 or mp4 iframes
            for iframe in iframes:
                src = iframe.attrib.get("src")
                if src and ("m3u8" in src or "mp4" in src):
                    if not event.is_set():
                        container.append(src)
                        event.set()
                    return

            # Priority 3: Use the first iframe as fallback
            src = iframes[0].attrib.get("src")
            if src and not event.is_set():
                container.append(src)
                event.set()

        except Exception as e:
            msg = f"Could not extract video from AnimesDigital: {e}"
            raise Exception(msg) from e


def load(languages_dict) -> None:
    """Load plugin if language is supported."""
    can_load = False
    for language in AnimesDigital.languages:
        if language in languages_dict:
            can_load = True
            break
    if not can_load:
        return
    rep.register(AnimesDigital())
