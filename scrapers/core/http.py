"""HTTP fetch shim over Scrapling's Fetcher.

Single transport layer for all scraper plugins. Wraps Scrapling so plugins
(and tests) depend on this module instead of a specific HTTP library.

The returned ``Response`` is also a Scrapling ``Selector``: it supports
``.css()``, ``.find_all()``, ``.json()``, ``.re()``, plus ``.status``,
``.headers`` and ``.html_content`` (raw HTML string).

On platforms where Scrapling's Fetcher cannot be imported (e.g. armv7l,
where playwright wheels don't exist), we transparently fall back to:

1. ``curl_cffi`` directly with browser TLS impersonation (if installed), or
2. plain ``httpx`` (no impersonation) as last resort,

both returning a Scrapling ``Selector`` subclass with the same
``.status``/``.headers``/``.json()`` surface.
"""

import logging
from typing import Any

from scrapling.parser import Selector

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30

# Single pinned UA used for URL resolution AND playback (mpv). Many video CDNs
# (e.g. googlevideo.com via Blogger) bind the resolved URL to the resolving UA.
RESOLVER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# curl_cffi impersonation profile — MUST stay aligned with RESOLVER_USER_AGENT.
CURL_IMPERSONATE = "chrome124"

try:  # pragma: no cover - depends on platform
    from scrapling.fetchers import Fetcher

    _HAS_FETCHER = True
    _HAS_CURL_CFFI = False
except (ImportError, ModuleNotFoundError):  # playwright missing (e.g. armv7l)
    Fetcher = None  # type: ignore[assignment]
    _HAS_FETCHER = False
    try:
        import curl_cffi.requests  # noqa: F401

        _HAS_CURL_CFFI = True
        logger.warning(
            "Scrapling Fetcher unavailable (missing playwright); "
            "falling back to curl_cffi with TLS impersonation (%s).",
            CURL_IMPERSONATE,
        )
    except (ImportError, ModuleNotFoundError):
        _HAS_CURL_CFFI = False
        logger.warning(
            "Scrapling Fetcher unavailable (missing playwright/curl_cffi); "
            "falling back to httpx transport without TLS impersonation."
        )

_FALLBACK_HEADERS = {
    "User-Agent": RESOLVER_USER_AGENT,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}


def resolver_user_agent() -> str:
    """User-Agent used to resolve video URLs.

    Video hosts like googlevideo.com bind the playback URL to the User-Agent
    that resolved it, so the media player MUST send this same UA.
    """
    return RESOLVER_USER_AGENT


class FetchError(Exception):
    """Raised when an HTTP request fails (network error or bad status)."""

    def __init__(self, message: str, status: int | None = None, url: str | None = None):
        super().__init__(message)
        self.status = status
        self.url = url


class _FallbackResponse(Selector):
    """Selector exposing ``.status``/``.headers``/``.json()`` like Scrapling's Response."""

    def __init__(self, text: str, url: str, status: int, headers: dict[str, str]):
        super().__init__(text or "<html></html>", url=url)
        self.status = status
        self.headers = headers
        self._raw_text = text

    @property
    def html_content(self) -> str:
        return self._raw_text

    def json(self) -> Any:
        import json as _json

        return _json.loads(self._raw_text)


def _curl_cffi_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    follow_redirects: bool = True,
    data: Any = None,
    json: Any = None,
    params: dict[str, Any] | None = None,
    **_ignored: Any,
) -> _FallbackResponse:
    from curl_cffi import requests as curl_requests

    merged = dict(_FALLBACK_HEADERS)
    if headers:
        merged.update(headers)
    try:
        response = curl_requests.request(
            method,
            url,
            headers=merged,
            timeout=timeout,
            allow_redirects=follow_redirects,
            data=data,
            json=json,
            params=params,
            impersonate=CURL_IMPERSONATE,
        )
    except Exception as exc:
        raise FetchError(f"{method} {url} failed: {exc}", url=url) from exc
    return _FallbackResponse(
        response.text,
        url=str(response.url),
        status=response.status_code,
        headers=dict(response.headers),
    )


def _fallback_request(method: str, url: str, **kwargs: Any) -> _FallbackResponse:
    """Dispatch to the best available fallback transport."""
    if _HAS_CURL_CFFI:
        return _curl_cffi_request(method, url, **kwargs)
    return _httpx_request(method, url, **kwargs)


def _httpx_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    follow_redirects: bool = True,
    data: Any = None,
    json: Any = None,
    params: dict[str, Any] | None = None,
    **_ignored: Any,
) -> _FallbackResponse:
    import httpx

    merged = dict(_FALLBACK_HEADERS)
    if headers:
        merged.update(headers)
    try:
        response = httpx.request(
            method,
            url,
            headers=merged,
            timeout=timeout,
            follow_redirects=follow_redirects,
            data=data,
            json=json,
            params=params,
        )
    except httpx.HTTPError as exc:
        raise FetchError(f"{method} {url} failed: {exc}", url=url) from exc
    return _FallbackResponse(
        response.text,
        url=str(response.url),
        status=response.status_code,
        headers=dict(response.headers),
    )


def _check_status(response: Any, raise_for_status: bool) -> Any:
    if raise_for_status and response.status >= 400:
        raise FetchError(
            f"HTTP {response.status} for {response.url}",
            status=response.status,
            url=response.url,
        )
    return response


def fetch(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    follow_redirects: bool = True,
    raise_for_status: bool = True,
    **kwargs: Any,
) -> Any:
    """GET a URL with stealthy browser-like headers and TLS impersonation."""
    if not _HAS_FETCHER:
        response = _fallback_request(
            "GET",
            url,
            headers=headers,
            timeout=timeout,
            follow_redirects=follow_redirects,
            **kwargs,
        )
        return _check_status(response, raise_for_status)
    request_headers = dict(headers or {})
    request_headers.setdefault("User-Agent", RESOLVER_USER_AGENT)
    try:
        response = Fetcher.get(
            url,
            headers=request_headers,
            timeout=timeout,
            follow_redirects=follow_redirects,
            stealthy_headers=True,
            **kwargs,
        )
    except FetchError:
        raise
    except Exception as exc:
        raise FetchError(f"GET {url} failed: {exc}", url=url) from exc
    return _check_status(response, raise_for_status)


def post(
    url: str,
    *,
    data: dict[str, Any] | str | None = None,
    json: Any = None,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    follow_redirects: bool = True,
    raise_for_status: bool = True,
    **kwargs: Any,
) -> Any:
    """POST to a URL with stealthy browser-like headers and TLS impersonation."""
    if not _HAS_FETCHER:
        response = _fallback_request(
            "POST",
            url,
            headers=headers,
            timeout=timeout,
            follow_redirects=follow_redirects,
            data=data,
            json=json,
            params=params,
            **kwargs,
        )
        return _check_status(response, raise_for_status)
    if json is not None:
        kwargs["json"] = json
    if params is not None:
        kwargs["params"] = params
    request_headers = dict(headers or {})
    request_headers.setdefault("User-Agent", RESOLVER_USER_AGENT)
    try:
        response = Fetcher.post(
            url,
            data=data,
            headers=request_headers,
            timeout=timeout,
            follow_redirects=follow_redirects,
            stealthy_headers=True,
            **kwargs,
        )
    except FetchError:
        raise
    except Exception as exc:
        raise FetchError(f"POST {url} failed: {exc}", url=url) from exc
    return _check_status(response, raise_for_status)


def fetch_json(url: str, **kwargs: Any) -> Any:
    """GET a URL and decode the JSON body."""
    response = fetch(url, **kwargs)
    try:
        return response.json()
    except Exception as exc:
        raise FetchError(f"Invalid JSON from {url}: {exc}", url=url) from exc
