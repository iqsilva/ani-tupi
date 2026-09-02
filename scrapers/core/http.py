"""HTTP fetch shim over Scrapling's Fetcher.

Single transport layer for all scraper plugins. Wraps Scrapling so plugins
(and tests) depend on this module instead of a specific HTTP library.

The returned ``Response`` is also a Scrapling ``Selector``: it supports
``.css()``, ``.find_all()``, ``.json()``, ``.re()``, plus ``.status``,
``.headers`` and ``.html_content`` (raw HTML string).
"""

from typing import Any

from scrapling.engines.toolbelt.custom import Response
from scrapling.fetchers import Fetcher

DEFAULT_TIMEOUT = 30


class FetchError(Exception):
    """Raised when an HTTP request fails (network error or bad status)."""

    def __init__(self, message: str, status: int | None = None, url: str | None = None):
        super().__init__(message)
        self.status = status
        self.url = url


def _check_status(response: Response, raise_for_status: bool) -> Response:
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
) -> Response:
    """GET a URL with stealthy browser-like headers and TLS impersonation."""
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
) -> Response:
    """POST to a URL with stealthy browser-like headers and TLS impersonation."""
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
