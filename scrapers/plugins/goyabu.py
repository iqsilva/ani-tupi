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
        """Async function to fetch video URL using Playwright with mouse automation"""
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
            captured_url = None

            # Capture video URL from navigation events
            def on_framenavigated(frame):
                nonlocal captured_url
                if "blogger.com/video.g" in frame.url:
                    # Clean URL: remove ALL whitespace using str.split() and join
                    # This removes newlines, tabs, spaces everywhere
                    cleaned = "".join(frame.url.split())
                    captured_url = cleaned
                    # Debug: print length to verify it's one line
                    print(f"[Goyabu] Captured video URL (length={len(cleaned)}): {cleaned[:80]}...")

            page.on("framenavigated", on_framenavigated)

            try:
                # Navigate to episode page
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=10000,
                    referer="https://www.google.com/",
                )
                await page.wait_for_timeout(1000)

                # Move mouse over video area to trigger player
                viewport_size = await page.evaluate(
                    "() => ({ width: window.innerWidth, height: window.innerHeight })"
                )
                center_x = viewport_size["width"] // 2
                center_y = viewport_size["height"] // 2

                await page.mouse.move(center_x, center_y)
                await page.wait_for_timeout(300)

                # Wave mouse inside video to keep controls visible
                for _ in range(2):
                    await page.mouse.move(center_x - 20, center_y - 10)
                    await page.wait_for_timeout(100)
                    await page.mouse.move(center_x + 20, center_y + 10)
                    await page.wait_for_timeout(100)

                # Wait for video URL to be captured
                await page.wait_for_timeout(2000)

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
