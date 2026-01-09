import requests
from selectolax.parser import HTMLParser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from scrapers.loader import PluginInterface
from services.repository import rep

from .utils import is_firefox_installed_as_snap


class AnimeFire(PluginInterface):
    languages = ["pt-br"]
    name = "animefire"

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

    def search_player_src(self, url: str, container: list, event) -> None:
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
        link = str(product.get_property("src"))

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
