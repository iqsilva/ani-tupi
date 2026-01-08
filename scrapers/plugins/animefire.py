import re
import requests
from selectolax.parser import HTMLParser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from scrapers.loader import PluginInterface
from services.repository import rep

from .utils import is_firefox_installed_as_snap

# Quality preferences for Blogger videos (in order of preference)
PREFERRED_QUALITIES = ["720", "hd", "480", "360"]


class AnimeFire(PluginInterface):
    languages = ["pt-br"]
    name = "animefire"

    def _extract_best_quality_source(self, sources: list) -> str:
        """
        Extract the best quality video source from a list of source elements.
        Tries to find 720p first, then HD, then falls back to lower qualities.

        Args:
            sources: List of Selenium source elements

        Returns:
            Best quality source URL found, or None if no sources available
        """
        quality_sources = {}

        for source in sources:
            try:
                src = source.get_attribute("src")
                data_quality = source.get_attribute("data-quality")

                if not src:
                    continue

                # Check src for quality indicators
                for quality in PREFERRED_QUALITIES:
                    if quality in src.lower():
                        if quality not in quality_sources:
                            quality_sources[quality] = src
                        break

                # Check data-quality attribute
                if data_quality:
                    for quality in PREFERRED_QUALITIES:
                        if quality in data_quality.lower():
                            if quality not in quality_sources:
                                quality_sources[quality] = src
                            break
            except Exception:
                continue

        # Return the highest quality source found
        for quality in PREFERRED_QUALITIES:
            if quality in quality_sources:
                return quality_sources[quality]

        return None

    def search_anime(self, query) -> None:
        url = "https://animefire.plus/pesquisar/" + "-".join(query.split())
        html_content = requests.get(url)
        tree = HTMLParser(html_content.text)
        target_class = "col-6 col-sm-4 col-md-3 col-lg-2 mb-1 minWDanime divCardUltimosEps"
        titles_urls = []
        for div in tree.css(f"div.{target_class.replace(' ', '.')}"):
            article = div.css_first("article a")
            if article is not None:
                href = article.attributes.get("href")
                if href:
                    titles_urls.append(href)
        titles = [h3.text() for h3 in tree.css("h3.animeTitle")]
        for title, url in zip(titles, titles_urls, strict=False):
            if url:  # Only add if url is not None
                rep.add_anime(title, url, self.name)

    def search_episodes(self, anime, url, params) -> None:
        html_episodes_page = requests.get(url)
        tree = HTMLParser(html_episodes_page.text)
        links = tree.css("a.lEp.epT.divNumEp.smallbox.px-2.mx-1.text-left.d-flex")
        episode_links = [a.attributes.get("href") for a in links if a.attributes.get("href")]
        opts = [a.text() for a in links]
        rep.add_episode_list(anime, opts, episode_links, self.name)

    def search_player_src(self, url, container, event) -> None:
        options = webdriver.FirefoxOptions()
        options.add_argument("--headless")

        try:
            if is_firefox_installed_as_snap():
                service = webdriver.FirefoxService(executable_path="/snap/bin/geckodriver")
                driver = webdriver.Firefox(options=options, service=service)
            else:
                driver = webdriver.Firefox(options=options)
        except:
            msg = "Firefox not installed."
            raise Exception(msg)

        driver.get(url)
        try:
            params = (By.ID, "my-video_html5_api")
            WebDriverWait(driver, 7).until(EC.visibility_of_all_elements_located(params))
        except:
            try:
                xpath = "/html/body/div[2]/div[2]/div/div[1]/div[1]/div/div/div[2]/div[4]/iframe"
                params = (By.XPATH, xpath)
                WebDriverWait(driver, 7).until(EC.visibility_of_all_elements_located(params))
            except:
                driver.quit()
                msg = "nor iframe nor video tags were found in animefire."
                raise Exception(msg)

        product = driver.find_element(params[0], params[1])
        link = product.get_property("src")

        # Try to get the best quality (720p) from the video element
        # Look for source tags with quality information
        try:
            video_element = driver.find_element(By.CSS_SELECTOR, "video")
            sources = video_element.find_elements(By.TAG_NAME, "source")

            if sources:
                best_quality_link = self._extract_best_quality_source(sources)
                if best_quality_link:
                    link = best_quality_link
        except Exception:
            # If no source tags found, use the original link
            pass

        # Prefer HD quality for direct video URLs
        # If URL contains /sd/, try to upgrade to /hd/
        if "/sd/" in link:
            hd_link = link.replace("/sd/", "/hd/")
            try:
                # Check if HD version exists by making a HEAD request
                response = requests.head(hd_link, timeout=5)
                if response.status_code == 200:
                    link = hd_link
            except Exception:
                # If HD version doesn't exist or check fails, use original SD link
                pass

        # If the link is a Blogger URL, try to add quality parameters
        # Blogger supports quality hints via URL parameters
        if "blogger.com" in link:
            # Add quality preference parameter if not already present
            if "?" not in link:
                link = link + "?quality=720p&preferredQuality=720"
            elif "&quality=" not in link and "&preferredQuality=" not in link:
                link = link + "&quality=720p&preferredQuality=720"

        driver.quit()

        if not event.is_set():
            container.append(link)
            event.set()


def load(languages_dict) -> None:
    can_load = False
    for language in AnimeFire.languages:
        if language in languages_dict:
            can_load = True
            break
    if not can_load:
        return
    rep.register(AnimeFire())
