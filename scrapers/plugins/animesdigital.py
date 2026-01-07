import requests
from selectolax.parser import HTMLParser

from scrapers.loader import PluginInterface
from services.repository import rep


class AnimesDigital(PluginInterface):
    languages = ["pt-br"]
    name = "animesdigital"

    @staticmethod
    def search_anime(query) -> None:
        """Search for anime on AnimesDigital.

        Constructs search URL and extracts anime titles and links.
        """
        url = "https://animesdigital.org/search/" + "+".join(query.split())
        html_content = requests.get(url, timeout=20)
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
        """
        html_content = requests.get(url, timeout=15)
        tree = HTMLParser(html_content.text)

        # Find all episode containers
        episode_divs = tree.css("div.item_ep")

        episode_titles = []
        episode_urls = []

        for ep_div in episode_divs:
            # Find the link inside the episode div
            link = ep_div.css_first("a")
            if link:
                href = link.attributes.get("href")
                # Get episode title (clean up extra whitespace)
                title = link.text().strip()
                title = " ".join(title.split())

                if href:
                    episode_urls.append(href)
                    episode_titles.append(title)

        # Add episodes to repository
        rep.add_episode_list(anime, episode_titles, episode_urls, AnimesDigital.name)

    @staticmethod
    def search_player_src(url_episode, container, event) -> None:
        """Extract video URL from episode player.

        AnimesDigital embeds video URLs directly in iframe src attributes,
        so we can extract them directly from HTML without Selenium.
        """
        try:
            response = requests.get(url_episode, timeout=15)
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
