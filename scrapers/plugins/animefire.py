import json

from scrapling.fetchers import DynamicFetcher

from services.repository import rep


class AnimeFire:
    languages = ["pt-br"]
    name = "animefire"

    def search_anime(self, query: str) -> None:
        url = "https://animefire.plus/pesquisar/" + "-".join(query.split())
        tree = DynamicFetcher.fetch(url, timeout=20000)
        target_class = "col-6 col-sm-4 col-md-3 col-lg-2 mb-1 minWDanime divCardUltimosEps"
        titles_urls = []
        for div in tree.css(f"div.{target_class.replace(' ', '.')}", adaptive=True, auto_save=True):
            # Use css()[0] instead of css_first() for scrapling compatibility
            article_results = div.css("article a", adaptive=True)
            article = article_results[0] if article_results else None
            if article is not None:
                href = article.attrib.get("href")
                if href:
                    titles_urls.append(href)
        titles = [str(h3.text) for h3 in tree.css("h3.animeTitle", adaptive=True, auto_save=True)]
        for title, url in zip(titles, titles_urls, strict=False):
            if url:  # Only add if url is not None
                rep.add_anime(title, url, self.name)

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        tree = DynamicFetcher.fetch(url, timeout=20000)
        links = tree.css("a.lEp.epT.divNumEp.smallbox.px-2.mx-1.text-left.d-flex")
        episode_links = [href for a in links if (href := a.attrib.get("href")) is not None]
        opts = [str(a.text) for a in links]
        rep.add_episode_list(anime, opts, episode_links, self.name)

    def search_player_src(self, url: str, container: list, event) -> None:
        try:
            # Use DynamicFetcher to render page and wait for video/iframe
            # Use Firefox for better library compatibility
            page = DynamicFetcher.fetch(url, timeout=15000)

            # AnimeFire uses Video.js player with data-video-src attribute
            # The attribute contains an API endpoint that returns JSON with video URLs
            # Use css()[0] instead of css_first() for scrapling compatibility
            video_results = page.css("video")
            video = video_results[0] if video_results else None
            if video:
                api_url = video.attrib.get("data-video-src")
                if api_url:
                    try:
                        # Fetch the API endpoint to get video URLs
                        api_response = DynamicFetcher.fetch(api_url, timeout=15000)
                        # Parse JSON from response
                        if hasattr(api_response, "json"):
                            video_data = api_response.json()
                        elif hasattr(api_response, "text"):
                            video_data = json.loads(api_response.text)
                        else:
                            video_data = json.loads(str(api_response))

                        if isinstance(video_data, dict) and "data" in video_data:
                            videos = video_data["data"]
                            if isinstance(videos, list) and len(videos) > 0:
                                # Prefer highest quality: 1080p > 720p > 480p > 360p
                                best_video = None
                                for quality in ["1080p", "720p", "480p", "360p"]:
                                    for v in videos:
                                        if v.get("label", "").lower() == quality.lower():
                                            best_video = v.get("src")
                                            break
                                    if best_video:
                                        break

                                # If no quality match, take the last one (usually highest quality)
                                if not best_video and videos:
                                    best_video = videos[-1].get("src")

                                if best_video:
                                    if not event.is_set():
                                        container.append(best_video)
                                        event.set()
                                    return
                    except Exception:
                        # API fetch failed, try fallback methods
                        pass

                # Fallback: try standard src attribute
                src = video.attrib.get("src")
                if src:
                    if not event.is_set():
                        container.append(src)
                        event.set()
                    return

            # Try to find source tag inside video
            # Use css()[0] instead of css_first() for scrapling compatibility
            source_results = page.css("video source")
            source = source_results[0] if source_results else None
            if source:
                src = source.attrib.get("src")
                if src:
                    if not event.is_set():
                        container.append(src)
                        event.set()
                    return

            # Try to find iframe
            # Use css()[0] instead of css_first() for scrapling compatibility
            iframe_results = page.css("iframe")
            iframe = iframe_results[0] if iframe_results else None
            if iframe:
                src = iframe.attrib.get("src")
                if src:
                    if not event.is_set():
                        container.append(src)
                        event.set()
                    return

            raise Exception("No video source found in AnimeFire episode page")
        except Exception as e:
            raise Exception(f"Could not extract video from AnimeFire: {e}") from e


def load(languages_dict) -> None:
    can_load = False
    for language in AnimeFire.languages:
        if language in languages_dict:
            can_load = True
            break
    if not can_load:
        return
    rep.register(AnimeFire())
