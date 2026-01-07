import requests
from selectolax.parser import HTMLParser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from multiprocessing.pool import ThreadPool
from os import cpu_count

from scrapers.loader import PluginInterface
from services.repository import rep
from .utils import is_firefox_installed_as_snap


class AnimesOnlineCC(PluginInterface):
    languages = ["pt-br"]
    name = "animesonlinecc"

    @staticmethod
    def search_anime(query):
        url = "https://animesonlinecc.to/search/" + "+".join(query.split())
        html_content = requests.get(url, timeout=10)
        tree = HTMLParser(html_content.text)

        divs = tree.css("div.data")
        titles_urls = [div.css_first("h3 a").attributes.get("href") for div in divs]
        titles = [div.css_first("h3 a").text() for div in divs]

        for title, url in zip(titles, titles_urls):
            rep.add_anime(title, url, AnimesOnlineCC.name)

        def parse_seasons(title, url):
            html = requests.get(url, timeout=10)
            tree = HTMLParser(html.text)
            num_seasons = len(tree.css("div.se-c"))
            if num_seasons > 1:
                for n in range(2, num_seasons + 1):
                    rep.add_anime(title + " Temporada " + str(n), url, AnimesOnlineCC.name, n)

        with ThreadPool(cpu_count()) as pool:
            for title, url in zip(titles, titles_urls):
                pool.apply(parse_seasons, args=(title, url))

    @staticmethod
    def search_episodes(anime, url, season):
        html_episodes_page = requests.get(url, timeout=10)
        tree = HTMLParser(html_episodes_page.text)

        seasons = tree.css("ul.episodios")
        season_idx = season - 1 if season is not None else 0
        season_ul = seasons[season_idx] if season_idx < len(seasons) else seasons[0]

        urls, titles = [], []
        for div in season_ul.css("div.episodiotitle"):
            anchor = div.css_first("a")
            if anchor:
                urls.append(anchor.attributes.get("href"))
                titles.append(anchor.text())

        rep.add_episode_list(anime, titles, urls, AnimesOnlineCC.name)

    @staticmethod
    def search_player_src(url_episode, container, event):
        options = webdriver.FirefoxOptions()
        options.add_argument("--headless")

        driver = None
        try:
            if is_firefox_installed_as_snap():
                service = webdriver.FirefoxService(executable_path="/snap/bin/geckodriver")
                driver = webdriver.Firefox(options=options, service=service)
            else:
                driver = webdriver.Firefox(options=options)
        except Exception as e:
            msg = "Firefox not installed."
            raise RuntimeError(msg) from e

        try:
            driver.get(url_episode)

            # Debug: Check what iframes exist on the page
            import os
            debug = os.environ.get("ANI_TUPI_SCRAPER_DEBUG") == "1"

            # Try multiple methods to find the iframe
            link = None
            iframe = None

            # Method 1: Try the original XPath
            try:
                xpath = "/html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[1]/div[1]/iframe"
                params = (By.XPATH, xpath)
                WebDriverWait(driver, 5).until(EC.visibility_of_all_elements_located(params))
                iframe = driver.find_element(*params)
                link = iframe.get_property("src")
                if debug:
                    print(f"   ✅ Method 1 (XPath): Found iframe")
            except Exception as e:
                iframe = None
                if debug:
                    print(f"   ❌ Method 1 (XPath): {str(e)[:80]}")

            # Method 2: Try finding any iframe with src attribute (if original didn't work)
            if not link:
                try:
                    WebDriverWait(driver, 3).until(
                        lambda d: len(d.find_elements(By.TAG_NAME, "iframe")) > 0
                    )
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    if debug:
                        print(f"   Found {len(iframes)} iframe(s) on page")
                    for idx, frame in enumerate(iframes):
                        src = frame.get_property("src")
                        if debug:
                            print(f"      iframe[{idx}] src: {src[:80] if src else 'empty'}...")
                        if src and src.startswith(("http://", "https://", "//")):
                            link = src
                            if debug:
                                print(f"   ✅ Method 2 (Tag search): Found valid iframe")
                            break
                    if debug and not link:
                        print(f"   ❌ Method 2 (Tag search): No valid iframe found")
                except Exception as e:
                    if debug:
                        print(f"   ❌ Method 2 (Tag search): {str(e)[:80]}")
                    pass

            # Method 3: Try CSS selector as last resort
            if not link:
                try:
                    iframe = driver.find_element(By.CSS_SELECTOR, "iframe[src]")
                    link = iframe.get_property("src")
                    if debug:
                        print(f"   ✅ Method 3 (CSS): Found iframe")
                except Exception as e:
                    if debug:
                        print(f"   ❌ Method 3 (CSS): {str(e)[:80]}")
                    pass

            if not link:
                msg = "Could not find iframe with video URL on animesonlinecc page."
                if debug:
                    print(f"   ⚠️  {msg}")
                raise RuntimeError(msg)

            # Handle relative URLs - convert to absolute if needed
            if link.startswith("/"):
                from urllib.parse import urljoin
                link = urljoin("https://animesonlinecc.to", link)

            if not event.is_set():
                container.append(link)
                event.set()
        finally:
            if driver:
                try:
                    driver.quit()
                except:  # noqa: E722
                    pass


def load(languages_dict):
    can_load = False
    for language in AnimesOnlineCC.languages:
        if language in languages_dict:
            can_load = True
            break
    if not can_load:
        return
    rep.register(AnimesOnlineCC)
