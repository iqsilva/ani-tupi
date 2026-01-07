import requests
from selectolax.parser import HTMLParser

from scrapers.loader import PluginInterface
from services.repository import rep

# Request timeout for all AnimesDigital API calls (seconds)
# Increased to 30s to handle slow network conditions
REQUEST_TIMEOUT = 30


class AnimesDigital(PluginInterface):
    languages = ["pt-br"]
    name = "animesdigital"

    @staticmethod
    def search_anime(query) -> None:
        """Search for anime on AnimesDigital.

        Constructs search URL and extracts anime titles and links.
        """
        url = "https://animesdigital.org/search/" + "+".join(query.split())
        html_content = requests.get(url, timeout=REQUEST_TIMEOUT)
        tree = HTMLParser(html_content.text)

        # Extract all anime links
        anime_links = tree.css("a[href*='/anime/']")
        titles = []
        urls = []

        for link in anime_links:
            href = link.attributes.get("href")
            title = link.text().strip()

            # Clean up title (remove extra whitespace and special chars)
            title = " ".join(title.split())

            if href and title:
                urls.append(href)
                titles.append(title)

        # Add anime to repository
        for title, url in zip(titles, urls):
            rep.add_anime(title, url, AnimesDigital.name)

    @staticmethod
    def search_episodes(anime, url, params) -> None:
        """Fetch episode list from anime page.

        Extracts episodes from the detail page using div.item_ep selector.
        Filters out special episodes (fractionated like 13.5) to avoid duplicates.
        """
        import re

        html_content = requests.get(url, timeout=REQUEST_TIMEOUT)
        tree = HTMLParser(html_content.text)

        # Find all episode containers
        episode_divs = tree.css("div.item_ep")

        episode_titles = []
        episode_urls = []

        for ep_div in episode_divs:
            # Find the link inside the episode div for the URL
            link = ep_div.css_first("a")
            href = None
            if link:
                href = link.attributes.get("href")

            # Get episode title from .title_anime class (avoids metadata like "9 meses atrás")
            title_elem = ep_div.css_first(".title_anime")
            if title_elem and href:
                title = title_elem.text().strip()
                # Clean up extra whitespace
                title = " ".join(title.split())
                if title:
                    # Filter out special episodes (fractionated like 13.5, 0.5, etc)
                    # These are OVAs/specials that shouldn't be counted as main episodes
                    if re.search(r"Episódio\s+\d+\.\d+", title):
                        continue  # Skip special episodes
                    episode_urls.append(href)
                    episode_titles.append(title)

        # Reverse episode lists because AnimesDigital lists episodes in descending order
        # (last episode first, episode 1 last). We need ascending order for proper navigation.
        episode_titles.reverse()
        episode_urls.reverse()

        # Add episodes to repository
        rep.add_episode_list(anime, episode_titles, episode_urls, AnimesDigital.name)

    @staticmethod
    def search_player_src(url_episode, container, event) -> None:
        """Extract video URL from episode player.

        AnimesDigital embeds video URLs directly in iframe src attributes,
        so we can extract them directly from HTML without Selenium.
        """
        try:
            response = requests.get(url_episode, timeout=REQUEST_TIMEOUT)
            tree = HTMLParser(response.text)

            # Look for iframes with video URLs
            iframes = tree.css("iframe[src]")

            if not iframes:
                msg = "No iframe found in AnimesDigital episode page."
                raise RuntimeError(msg)

            # Get the first iframe src (contains the video URL)
            for iframe in iframes:
                src = iframe.attributes.get("src", "")
                if src and ("m3u8" in src or "mp4" in src or "anivideo" in src):
                    if not event.is_set():
                        container.append(src)
                        event.set()
                    return

            # If no obvious video iframe found, try the first iframe
            src = iframes[0].attributes.get("src", "")
            if src and not event.is_set():
                container.append(src)
                event.set()

        except Exception as e:
            msg = f"Could not extract video from AnimesDigital: {e}"
            raise RuntimeError(msg) from e


def load(languages_dict) -> None:
    """Load plugin if language is supported."""
    can_load = False
    for language in AnimesDigital.languages:
        if language in languages_dict:
            can_load = True
            break
    if not can_load:
        return
    rep.register(AnimesDigital)
