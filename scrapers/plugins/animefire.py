from selectolax.parser import HTMLParser
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from scrapers.core.browser_pool import get_browser_pool

from scrapers.plugins.utils import get_with_retry, head_with_retry
from services.repository import rep


class AnimeFire:
    languages = ["pt-br"]
    name = "animefire"

    def search_anime(self, query: str) -> None:
        url = "https://animefire.plus/pesquisar/" + "-".join(query.split())
        response = get_with_retry(url)
        tree = HTMLParser(response.text)
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

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        response = get_with_retry(url)
        tree = HTMLParser(response.text)
        links = tree.css("a.lEp.epT.divNumEp.smallbox.px-2.mx-1.text-left.d-flex")
        episode_links = [href for a in links if (href := a.attributes.get("href")) is not None]
        opts = [a.text() for a in links]
        rep.add_episode_list(anime, opts, episode_links, self.name)

    def search_player_src(self, url: str, container: list, event) -> None:
        try:
            with get_browser_pool().get_browser() as driver:
                driver.get(url)
                try:
                    params = (By.ID, "my-video_html5_api")
                    WebDriverWait(driver, 7).until(EC.visibility_of_all_elements_located(params))
                except:
                    try:
                        xpath = "/html/body/div[2]/div[2]/div/div[1]/div[1]/div/div/div[2]/div[4]/iframe"
                        params = (By.XPATH, xpath)
                        WebDriverWait(driver, 7).until(
                            EC.visibility_of_all_elements_located(params)
                        )
                    except:
                        msg = "neither iframe nor video tags were found in animefire."
                        raise Exception(msg)

                product = driver.find_element(params[0], params[1])
                link = str(product.get_property("src"))
        except Exception as e:
            if "Firefox" in str(e):
                msg = "Firefox not installed or browser pool failed."
                raise Exception(msg)
            else:
                raise

        # Prefer HD quality for direct video URLs
        # If URL contains /sd/, try to upgrade to /hd/
        if "/sd/" in link:
            hd_link = link.replace("/sd/", "/hd/")
            try:
                # Check if HD version exists by making a HEAD request
                response = head_with_retry(hd_link)
                if response.status_code == 200:
                    link = hd_link
            except Exception:
                # If HD version doesn't exist or check fails, use original SD link
                pass

        # if url contains 480p, try to upgrade to 720p
        elif "480p" in link:
            hd_link = link.replace("/480p", "/720p")
            try:
                response = head_with_retry(hd_link)
                if response.status_code == 200:
                    link = hd_link
            except Exception:
                pass

        # If the link is a Blogger URL, try to add quality parameters
        # Blogger supports quality hints via URL parameters
        if "blogger.com" in link:
            # Add quality preference parameter if not already present
            if "?" not in link:
                link = link + "?quality=720p&preferredQuality=720"
            elif "&quality=" not in link and "&preferredQuality=" not in link:
                link = link + "&quality=720p&preferredQuality=720"

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
