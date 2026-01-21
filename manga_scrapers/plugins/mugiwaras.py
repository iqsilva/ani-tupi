"""MugiwarasOficial.com manga scraper.

Scrapes manga from https://mugiwarasoficial.com/ (Brazilian Portuguese site).
Uses requests + selectolax (fast) and Playwright for AJAX-loaded chapters.
"""

import re
from typing import Any

import requests
from playwright.sync_api import sync_playwright
from selectolax.parser import HTMLParser


class MugiwarasOficial:
    """MugiwarasOficial.com scraper plugin."""

    name = "mugiwaras"
    languages = ["pt-br"]
    base_url = "https://mugiwarasoficial.com"

    def __init__(self):
        """Initialize scraper with requests session."""
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        )

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

            # Fetch with requests
            resp = self.session.get(search_url, timeout=10)
            resp.raise_for_status()

            # Parse HTML
            tree = HTMLParser(resp.text)

            results = []

            # Parse manga results from Madara theme
            # Each manga is in a div with class "row c-tabs-item__content"
            manga_items = tree.css("div.row.c-tabs-item__content")

            for item in manga_items:
                try:
                    # Extract title and URL from the link
                    link = item.css_first("div.post-title a")
                    if not link:
                        continue

                    title = link.text(strip=True)
                    url = link.attributes.get("href", "")

                    if not title or not url:
                        continue

                    # Extract cover image
                    img = item.css_first("img")
                    cover_url = None
                    if img:
                        cover_url = img.attributes.get("data-src") or img.attributes.get("src")

                    # Extract latest chapter info (optional)
                    latest_chapter = item.css_first("span.chapter a")
                    latest_chapter_text = (
                        latest_chapter.text(strip=True) if latest_chapter else None
                    )

                    # Extract manga ID from URL (slug)
                    manga_id = url.rstrip("/").split("/")[-1]

                    results.append(
                        {
                            "id": manga_id,
                            "title": title,
                            "url": url,
                            "cover_url": cover_url,
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

        Args:
            manga_id: Manga ID (slug)
            manga_url: Manga URL

        Returns:
            List of chapters
        """
        try:
            # Use Playwright to render the page and wait for AJAX-loaded chapters
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Navigate to manga page
                page.goto(manga_url, wait_until="networkidle", timeout=30000)

                # Wait for chapter list to load (Madara theme loads via AJAX)
                try:
                    page.wait_for_selector("li.wp-manga-chapter", timeout=10000)
                except Exception:
                    # If chapters don't load within timeout, continue anyway
                    pass

                # Get page HTML after JavaScript execution
                html = page.content()
                browser.close()

            # Parse rendered HTML
            tree = HTMLParser(html)
            chapters = []

            # Extract chapter list
            chapter_items = tree.css("li.wp-manga-chapter")

            for item in chapter_items:
                try:
                    link = item.css_first("a")
                    if not link:
                        continue

                    chapter_url = link.attributes.get("href", "")
                    chapter_title = link.text(strip=True)

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
            print(f"⚠️  Erro ao buscar capítulos: {e}")
            return []

    def get_chapter_pages(self, chapter_id: str, chapter_url: str) -> list[str]:
        """Fetch image URLs for a chapter.

        Args:
            chapter_id: Chapter ID
            chapter_url: Chapter URL

        Returns:
            List of image URLs
        """
        try:
            # Use Playwright to handle age verification modal
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Navigate to chapter page
                page.goto(chapter_url, wait_until="networkidle", timeout=30000)

                # Check for age verification modal and handle it
                try:
                    # Wait for adult modal to appear (if present) - it might be hidden initially
                    page.wait_for_selector("#adult_modal", timeout=5000)

                    # Make modal visible (it might be hidden initially)
                    page.evaluate("""
                        const modal = document.getElementById('adult_modal');
                        if (modal) {
                            modal.style.display = 'block';
                            modal.classList.remove('fade');
                            modal.classList.add('show');
                        }
                    """)

                    # Click "Yes, I am" button to confirm age
                    confirm_button = page.query_selector(".btn-adult-confirm")
                    if confirm_button:
                        confirm_button.click()
                        # Wait a moment for modal to close and content to load
                        page.wait_for_timeout(3000)
                except Exception:
                    # No modal found or modal handling failed, continue anyway
                    pass

                # Get page HTML after JavaScript execution and modal handling
                html = page.content()
                browser.close()

            # Parse rendered HTML
            tree = HTMLParser(html)

            page_urls = []

            # If specific selectors didn't work, try all images
            # MugiwarasOficial has manga images directly in HTML
            all_images = tree.css("img")

            for img in all_images:
                # Try multiple attributes where image URL might be
                # MugiwarasOficial uses data-src for lazy loading
                img_url = (
                    img.attributes.get("data-src")
                    or img.attributes.get("data-lazy-src")
                    or img.attributes.get("src")
                    or img.attributes.get("data-original")
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

                # Filter for manga page images
                # MugiwarasOficial uses /WP-manga/ path for manga pages
                is_manga_page = "/WP-manga/" in img_url or "/wp-manga/" in img_url.lower()

                # Skip logos, banners, ads, and invalid formats
                # Note: .webp is NOT in noise list since manga pages use webp
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
                    ]
                )

                # Ensure it's an actual image file
                is_image = any(
                    img_url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]
                )

                if is_manga_page and not is_noise and is_image and img_url not in page_urls:
                    page_urls.append(img_url)

            return page_urls

        except Exception as e:
            print(f"⚠️  Erro ao buscar páginas do capítulo: {e}")
            import traceback

            traceback.print_exc()
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
