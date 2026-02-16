from playwright.async_api import async_playwright
import asyncio
import re

from services.repository import rep


class Goyabu:
    languages = ["pt-br"]
    name = "goyabu"

    def search_anime(self, query: str) -> None:
        """Search for anime on Goyabu homepage search"""
        try:
            # Use async function to search
            results = asyncio.run(self._search_anime_async(query))
            for title, url in results:
                rep.add_anime(title, url, self.name)
        except Exception:
            pass

    async def _search_anime_async(self, query: str) -> list:
        """Async function to search for anime on Goyabu homepage"""
        results = []
        # Use the correct search URL format
        url = "https://goyabu.io/?s=" + "+".join(query.split())

        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
            )

            page = await context.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(3000)

                # Look for anime links
                anime_items = await page.query_selector_all("a[href*='/anime/']")

                for item in anime_items:
                    try:
                        href = await item.get_attribute("href")
                        text = await item.text_content()
                        if href and text:
                            # Clean title: remove tabs, newlines, and extra spaces
                            title = (
                                text.strip().replace("\t", " ").replace("\n", " ").replace("\r", "")
                            )
                            # Collapse multiple spaces into one
                            title = " ".join(title.split())
                            # Remove rating numbers at the end (e.g., "3.9", "5.0")
                            # Match pattern like: "Title 3.9" or "Title 0.0"
                            title = re.sub(r"\s+\d+\.\d+\s*$", "", title)
                            # Remove "Dublado" prefix
                            title = title.removeprefix("Dublado").strip()
                            # Clean URL
                            href = href.strip().replace("\n", "").replace("\r", "")
                            if title and href and "/anime/" in href:
                                results.append((title, href))
                    except Exception:
                        pass

            except Exception:
                pass
            finally:
                await context.close()
                await browser.close()

        return results

    def search_episodes(self, anime: str, url: str, params: dict | None = None) -> None:
        """Find episodes for an anime using Playwright with mouse automation"""
        try:
            # Run async function
            episode_data = asyncio.run(self._fetch_episodes_async(url))

            if episode_data:
                episode_numbers, episode_urls = episode_data
                rep.add_episode_list(anime, episode_numbers, episode_urls, self.name)
        except Exception:
            pass

    async def _fetch_episodes_async(self, url: str) -> tuple | None:
        """Async function to fetch episodes using Playwright"""
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
                locale="en-US",
                timezone_id="America/New_York",
                viewport={"width": 1920, "height": 1080},
            )

            # Add stealth evasions
            await context.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
                window.chrome = {
                    runtime: {}
                };
            """
            )

            page = await context.new_page()

            try:
                # Navigate to anime page
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=15000,
                    referer="https://www.google.com/",
                )
                await page.wait_for_timeout(3000)

                # Scroll down to load episodes
                for _ in range(3):
                    await page.mouse.wheel(0, 500)
                    await page.wait_for_timeout(500)

                # Find episode items
                episodes = await page.query_selector_all("div.episode-item")

                if not episodes:
                    return None

                episode_numbers = []
                episode_urls = []

                for ep in episodes:
                    try:
                        link = await ep.query_selector("article > a")
                        if link:
                            url_str = await link.get_attribute("href")
                            if url_str:
                                # Clean URL: strip whitespace and newlines
                                url_str = url_str.strip().replace("\n", "").replace("\r", "")
                                # Extract episode number from HTML or text
                                text = await link.text_content()
                                # Try to find episode number pattern
                                match = re.search(r"(\d+)", text or "")
                                if match:
                                    episode_num = match.group(1)
                                    episode_numbers.append(episode_num)
                                    episode_urls.append(url_str)
                    except Exception:
                        pass

                await context.close()
                await browser.close()

                if episode_urls:
                    return (episode_numbers, episode_urls)

            except Exception:
                await context.close()
                await browser.close()

        return None

    def search_player_src(self, url: str, container: list, event) -> None:
        """Extract video URL from Goyabu episode page"""
        import time

        try:
            # Run async function in a new event loop (thread-safe)
            video_url = asyncio.run(self._fetch_video_url_async(url))

            if video_url:
                # Verify URL has no whitespace
                if any(c.isspace() for c in video_url):
                    video_url = "".join(video_url.split())

                container.append(video_url)
                event.set()
                time.sleep(0.1)  # Small delay to ensure event is processed
        except Exception:
            # Silently fail - let other sources try
            pass

    async def _fetch_video_url_async(self, url: str) -> str | None:
        """Async function to fetch video URL by extracting from Blogger iframe"""
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
                locale="pt-BR",
                timezone_id="America/Sao_Paulo",
                viewport={"width": 1920, "height": 1080},
            )

            # Add stealth evasions
            await context.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
                window.chrome = {
                    runtime: {}
                };
            """
            )

            page = await context.new_page()
            blogger_url = None
            captured_url = None

            try:
                # Step 1: Navigate to episode page and get Blogger iframe URL
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=15000,
                    referer="https://www.google.com/",
                )
                await page.wait_for_timeout(3000)

                # Click "Player FHD" button
                try:
                    fhd_button = await page.wait_for_selector(
                        "button:has-text('Player FHD')", timeout=5000
                    )
                    if fhd_button:
                        await fhd_button.evaluate("element => element.click()")
                        await page.wait_for_timeout(3000)
                except Exception:
                    pass

                # Extract Blogger iframe URL
                iframes = await page.query_selector_all("iframe")
                for iframe in iframes:
                    src = await iframe.get_attribute("src")
                    if src and "blogger.com/video.g" in src:
                        blogger_url = "".join(src.split())
                        break

                # Step 2: Navigate to Blogger URL and intercept video request
                if blogger_url:
                    # Setup network interception
                    def on_request(request):
                        nonlocal captured_url
                        req_url = request.url
                        if "googlevideo.com/videoplayback" in req_url:
                            captured_url = req_url

                    page.on("request", on_request)

                    # Navigate to Blogger URL
                    await page.goto(blogger_url, wait_until="domcontentloaded", timeout=15000)
                    await page.wait_for_timeout(3000)

                    # Click to trigger video loading
                    try:
                        await page.mouse.click(960, 540)
                        await page.wait_for_timeout(5000)
                    except Exception:
                        pass

                    # If still no URL, try clicking play button
                    if not captured_url:
                        try:
                            play_btn = await page.wait_for_selector(
                                "button[aria-label*='Play'], .jw-icon-playback", timeout=3000
                            )
                            if play_btn:
                                await play_btn.click()
                                await page.wait_for_timeout(5000)
                        except Exception:
                            pass

                # Fallback: return Blogger URL if Google Video not found
                if not captured_url and blogger_url:
                    captured_url = blogger_url

            except Exception:
                pass
            finally:
                await context.close()
                await browser.close()

            return captured_url


def load(languages_dict) -> None:
    """Load the Goyabu plugin if the required languages are available"""
    can_load = False
    for language in Goyabu.languages:
        if language in languages_dict:
            can_load = True
            break
    if not can_load:
        return
    rep.register(Goyabu())
