"""HTTP fetch shim over Scrapling's Fetcher.

Single transport layer for all scraper plugins. Wraps Scrapling so plugins
(and tests) depend on this module instead of a specific HTTP library.

The returned ``Response`` is also a Scrapling ``Selector``: it supports
``.css()``, ``.find_all()``, ``.json()``, ``.re()``, plus ``.status``,
``.headers`` and ``.html_content`` (raw HTML string).

On platforms where Scrapling's Fetcher cannot be imported (e.g. armv7l,
where playwright/curl_cffi wheels don't exist), we transparently fall back
to a plain httpx transport returning a Scrapling ``Selector`` subclass with
the same ``.status``/``.headers``/``.json()`` surface.
"""

import logging
from typing import Any

from scrapling.parser import Selector

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30

try:  # pragma: no cover - depends on platform
    from scrapling.fetchers import Fetcher

    _HAS_FETCHER = True
except (ImportError, ModuleNotFoundError):  # playwright/curl_cffi missing
    Fetcher = None  # type: ignore[assignment]
    _HAS_FETCHER = False
    logger.warning(
        "Scrapling Fetcher unavailable (missing playwright/curl_cffi); "
        "falling back to httpx transport without TLS impersonation."
    )

_FALLBACK_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux armv7l) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}


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
        response = _httpx_request(
            "GET",
            url,
            headers=headers,
            timeout=timeout,
            follow_redirects=follow_redirects,
            **kwargs,
        )
        return _check_status(response, raise_for_status)
    try:
        response = Fetcher.get(
            url,
            headers=headers or {},
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
        response = _httpx_request(
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
    try:
        response = Fetcher.post(
            url,
            data=data,
            headers=headers or {},
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
