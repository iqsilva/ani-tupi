"""MangaLivre.blog manga scraper.

Scrapes manga from https://mangalivre.blog/ (Brazilian Portuguese site).
Uses Scrapling.Fetcher for search and DynamicFetcher for AJAX-loaded chapters.
"""

import re
from typing import Any

from scrapling import Fetcher, DynamicFetcher


class MangaLivre:
    """MangaLivre.blog scraper plugin."""

    name = "mangalivre"
    languages = ["pt-br"]
    base_url = "https://mangalivre.blog"

    def __init__(self):
        """Initialize scraper with Scrapling Fetcher."""
        self.fetcher = Fetcher()

    def search_manga(self, query: str) -> list[dict[str, Any]]:
        """Search for manga by title.

        Args:
            query: Search query string

        Returns:
            List of manga results with structure:
            [
                {
                    "id": "unique-id",
                    "title": "Manga Title",
                    "url": "https://...",
                    "description": "Description or None",
                    "status": "ongoing",
                    "year": None,
                }
            ]
        """
        try:
            # Use WordPress search endpoint
            search_url = f"{self.base_url}/?s={query.replace(' ', '+')}&post_type=wp-manga"

            # Fetch with Scrapling Fetcher
            tree = self.fetcher.get(search_url, timeout=10)

            results = []

            # Parse manga results from WordPress theme
            # Search results use div.manga-card structure
            manga_cards = tree.css("div.manga-card")

            for card in manga_cards:
                try:
                    # Extract link and title
                    link = card.css_first("a")
                    if not link:
                        continue

                    url = link.attrib.get("href", "")
                    if not url:
                        continue

                    # Extract title - try multiple selectors
                    # MangaLivre uses h2, h3, h4 or spans for titles
                    title_elem = (
                        card.css_first("h2")
                        or card.css_first("h3")
                        or card.css_first("h4")
                        or card.css_first("span[class*='title']")
                        or card.css_first(".title")
                    )
                    title = str(title_elem.text) if title_elem else str(link.text)
                    title = title.strip()

                    if not title or title.isspace():
                        continue

                    # Extract description if available
                    desc_elem = card.css_first("p")
                    description = str(desc_elem.text).strip() if desc_elem else None

                    # Extract status if available
                    status_elem = card.css_first("span")
                    status = str(status_elem.text).strip().lower() if status_elem else "ongoing"

                    # Extract manga ID from URL (slug)
                    manga_id = url.rstrip("/").split("/")[-1]

                    results.append(
                        {
                            "id": manga_id,
                            "title": title,
                            "url": url,
                            "description": description,
                            "status": status,
                            "year": None,  # Not available in search results
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
            List of chapters with "url" field extracted from HTML href attributes:
            [
                {
                    "id": "chapter-id",
                    "number": "1",
                    "title": "Chapter Title or None",
                    "url": "https://...",
                }
            ]
        """
        try:
            # Use DynamicFetcher to render page and wait for AJAX-loaded chapters
            df = DynamicFetcher()
            tree = df.fetch(manga_url, timeout=15)

            chapters = []

            # Extract chapter list - MangaLivre uses li.chapter-item
            chapter_items = tree.css("li.chapter-item")

            for item in chapter_items:
                try:
                    link = item.css_first("a")
                    if not link:
                        continue

                    chapter_url = link.attrib.get("href", "")
                    chapter_title = str(link.text).strip()

                    if not chapter_url:
                        continue

                    # Extract chapter number from title or URL
                    # Typical format: "Capítulo 222 - Título" or "capitulo-222"
                    number_match = re.search(
                        r"capítulo\s+(\d+(?:\.\d+)?)", chapter_title, re.IGNORECASE
                    )
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

                    # Clean chapter title (remove "Capítulo X" and similar)
                    clean_title = re.sub(
                        r"capítulo\s+\d+(\.\d+)?\s*-?\s*",
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
            List of image URLs (absolute URLs)
        """
        try:
            # Use DynamicFetcher to render the page with JavaScript
            df = DynamicFetcher()
            tree = df.fetch(chapter_url, timeout=15)

            page_urls = []

            # Extract all images from the page
            all_images = tree.css("img")

            for img in all_images:
                # Try multiple attributes where image URL might be
                # WordPress lazy-loading uses data-src or data-lazy-src
                img_url = (
                    img.attrib.get("data-src")
                    or img.attrib.get("data-lazy-src")
                    or img.attrib.get("src")
                    or img.attrib.get("data-original")
                )

                # Skip if no URL
                if not img_url:
                    continue

                # Strip whitespace
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
                # MangaLivre stores images in /wp-content/uploads/
                is_manga_page = "/wp-content/uploads/" in img_url.lower()

                # Skip logos, banners, ads, and other non-manga content
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
            return []


def load(languages: set[str]):
    """Load MangaLivre plugin if pt-br is in languages.

    Args:
        languages: Set of supported languages

    Returns:
        Plugin instance or None
    """
    if "pt-br" in languages:
        return MangaLivre()
    return None
