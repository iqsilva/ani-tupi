"""MugiwarasOficial.com manga scraper.

Scrapes manga from https://mugiwarasoficial.com/ (Brazilian Portuguese site).
Uses Scrapling.StealthyFetcher for search and DynamicFetcher for AJAX-loaded chapters.
Adaptive CSS selectors survive website design changes.
"""

import re
import time
from typing import Any

from scrapling.fetchers import StealthyFetcher, DynamicFetcher

# Enable adaptive mode for future-proof scraping
StealthyFetcher.adaptive = True


class MugiwarasOficial:
    """MugiwarasOficial.com scraper plugin."""

    name = "mugiwaras"
    languages = ["pt-br"]
    base_url = "https://mugiwarasoficial.com"

    def __init__(self):
        """Initialize scraper with Scrapling Fetcher."""
        pass  # Use Fetcher.get() directly, no instance needed

    def search_manga(self, query: str) -> list[dict[str, Any]]:
        """Search for manga by title.

        Args:
            query: Search query string

        Returns:
            List of manga results
        """
        try:
            # Use WordPress search endpoint
            search_url = f"{self.base_url}/?s={query.replace(' ', '+')}&post_type=wp-manga"

            # Fetch with adaptive StealthyFetcher for robustness against design changes
            tree = StealthyFetcher.fetch(search_url, headless=True, adaptive=True)

            results = []

            # Parse manga results from Madara theme
            # Each manga is in a div with class "row c-tabs-item__content"
            # Using adaptive=True to survive website design changes
            manga_items = tree.css("div.row.c-tabs-item__content", adaptive=True, auto_save=True)

            for item in manga_items:
                try:
                    # Extract title and URL from the link
                    links = item.css("div.post-title a")
                    if not links:
                        continue

                    link = links[0]
                    title = str(link.text).strip()
                    url = link.attrib.get("href", "")

                    if not title or not url:
                        continue

                    # Extract latest chapter info (optional)
                    latest_chapters = item.css("span.chapter a")
                    latest_chapter_text = (
                        str(latest_chapters[0].text).strip() if latest_chapters else None
                    )

                    # Extract manga ID from URL (slug)
                    manga_id = url.rstrip("/").split("/")[-1]

                    results.append(
                        {
                            "id": manga_id,
                            "title": title,
                            "url": url,
                            "description": None,  # Not available in search results
                            "status": "ongoing",  # Default, can be updated from detail page
                            "year": None,  # Not available in search results
                            "latest_chapter": latest_chapter_text,
                        }
                    )
                except Exception:
                    # Skip malformed entries
                    continue

            return results

        except Exception as e:
            print(f"⚠️  Erro ao buscar mangá: {e}")
            return []

    def get_chapters(self, manga_id: str, manga_url: str) -> list[dict[str, Any]]:
        """Fetch chapter list for a manga.

        Extracts chapter URLs directly from HTML href attributes in the chapter list.
        Each chapter's "url" field is populated with the link extracted from the website.

        Args:
            manga_id: Manga ID (slug)
            manga_url: Manga URL

        Returns:
            List of chapters with "url" field extracted from HTML href attributes
        """
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Use DynamicFetcher to render the page and wait for AJAX-loaded chapters
                # Use Firefox for better library compatibility
                # Increase timeout on retry attempts and add small delay between retries
                if retry_count > 0:
                    time.sleep(2)  # Wait before retrying

                timeout = 15000 + (retry_count * 5000)
                tree = DynamicFetcher.fetch(manga_url, timeout=timeout, browser="firefox")

                chapters = []

                # Extract chapter list
                chapter_items = tree.css("li.wp-manga-chapter")

                # If no chapters found and we can retry, do so
                if not chapter_items and retry_count < max_retries - 1:
                    retry_count += 1
                    print(f"⚠️  Nenhum capítulo encontrado, tentativa {retry_count + 1}...")
                    continue

                for item in chapter_items:
                    try:
                        links = item.css("a")
                        if not links:
                            continue

                        link = links[0]
                        chapter_url = link.attrib.get("href", "")
                        chapter_title = str(link.text).strip()

                        if not chapter_url:
                            continue

                        # Extract chapter number from title or URL
                        # Typical format: "Capítulo 222 PT-BR" or "capitulo-222-pt-br"
                        number_match = re.search(r"(\d+(?:\.\d+)?)", chapter_title)
                        if number_match:
                            chapter_number = number_match.group(1)
                        else:
                            # Try extracting from URL
                            url_match = re.search(r"capitulo-(\d+(?:\.\d+)?)", chapter_url)
                            if url_match:
                                chapter_number = url_match.group(1)
                            else:
                                continue  # Skip if no number found

                        # Generate chapter ID from URL
                        chapter_id = chapter_url.rstrip("/").split("/")[-1]

                        # Clean chapter title (remove "Capítulo X PT-BR")
                        clean_title = re.sub(
                            r"capítulo\s+\d+(\.\d+)?\s*-?\s*pt-br",
                            "",
                            chapter_title,
                            flags=re.IGNORECASE,
                        ).strip()
                        if clean_title and clean_title != chapter_title:
                            final_title = clean_title
                        else:
                            final_title = None

                        chapters.append(
                            {
                                "id": chapter_id,
                                "number": chapter_number,
                                "title": final_title,
                                "url": chapter_url,
                            }
                        )
                    except Exception:
                        continue

                # Sort chapters by number (descending - latest first)
                chapters.sort(key=lambda c: float(c["number"]), reverse=True)

                return chapters

            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"⚠️  Erro ao buscar capítulos (após {max_retries} tentativas): {e}")
                    return []
                print(f"⚠️  Erro ao buscar capítulos (tentativa {retry_count}): {e}")

        return []

    def get_chapter_pages(self, chapter_id: str, chapter_url: str) -> list[str]:
        """Fetch image URLs for a chapter.

        Args:
            chapter_id: Chapter ID
            chapter_url: Chapter URL

        Returns:
            List of image URLs
        """
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Use DynamicFetcher to handle AJAX-loaded images and JavaScript rendering
                # Increase timeout significantly to allow JavaScript to execute fully
                # MugiwarasOficial loads chapter images via AJAX, requiring longer wait time
                timeout = 30000 + (retry_count * 10000)  # 30s, 40s, 50s

                if retry_count > 0:
                    time.sleep(2)  # Wait before retrying

                tree = DynamicFetcher.fetch(chapter_url, timeout=timeout, browser="firefox")

                page_urls = []

                # Try multiple selectors for finding images
                # MugiwarasOficial may load images via AJAX in different containers
                selectors = [
                    "img[class*='manga']",  # Manga-specific images
                    "img[src*='/manga/']",  # Images with /manga/ in URL
                    "div.reading-content img",  # Reading content container
                    "div.post-content img",  # Post content container
                    "div.entry-content img",  # Entry content container
                ]

                for selector in selectors:
                    images = tree.css(selector)
                    if images:
                        break
                else:
                    # Fallback to all images if no specific selector worked
                    images = tree.css("img")

                for img in images:
                    # Try multiple attributes where image URL might be
                    # MugiwarasOficial uses data-src for lazy loading
                    img_url = (
                        img.attrib.get("data-src")
                        or img.attrib.get("data-lazy-src")
                        or img.attrib.get("src")
                        or img.attrib.get("data-original")
                    )

                    # Skip if no URL
                    if not img_url:
                        continue

                    # Strip whitespace (MugiwarasOficial has leading spaces in URLs!)
                    img_url = img_url.strip()

                    # Normalize URL - handle relative URLs
                    if not img_url.startswith("http"):
                        if img_url.startswith("//"):
                            img_url = "https:" + img_url
                        elif img_url.startswith("/"):
                            img_url = self.base_url + img_url
                        else:
                            continue

                    # Skip logos, banners, ads, and invalid formats
                    is_noise = any(
                        skip in img_url.lower()
                        for skip in [
                            "logo",
                            "banner",
                            "/ad/",
                            "/ads/",
                            "sidebar",
                            "amazon",
                            "cropped-",
                            ".gif",
                            "mugiwaras-removebg",
                            "icon",
                            "thumb",
                        ]
                    )

                    # Ensure it's an actual image file
                    is_image = any(
                        img_url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]
                    )

                    # Accept any non-noise image from CDN or site
                    if not is_noise and is_image and img_url not in page_urls:
                        # Additional filter: exclude known UI images
                        if (
                            "uploads" not in img_url
                            or "manga" in img_url.lower()
                            or "chapter" in img_url.lower()
                        ):
                            page_urls.append(img_url)

                # If no pages found and we can retry, do so
                if not page_urls and retry_count < max_retries - 1:
                    retry_count += 1
                    print(f"⚠️  Nenhuma página encontrada, tentativa {retry_count + 1}...")
                    continue

                return page_urls

            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    print(
                        f"⚠️  Erro ao buscar páginas do capítulo (após {max_retries} tentativas): {e}"
                    )
                    return []
                print(f"⚠️  Erro ao buscar páginas do capítulo (tentativa {retry_count}): {e}")

        return []


def load(languages: set[str]):
    """Load MugiwarasOficial plugin if pt-br is in languages.

    Args:
        languages: Set of supported languages

    Returns:
        Plugin instance or None
    """
    if "pt-br" in languages:
        return MugiwarasOficial()
    return None
