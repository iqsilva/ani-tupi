"""Tests for the httpx fallback path in scrapers.core.http."""

from unittest.mock import MagicMock, patch

import pytest

from scrapers.core import http


def _mock_httpx_response(text="<html><body><a href='x'>hi</a></body></html>", status=200, url="https://example.com/"):
    resp = MagicMock()
    resp.text = text
    resp.content = text.encode("utf-8")
    resp.status_code = status
    resp.url = url
    resp.headers = {"content-type": "text/html"}
    return resp


@patch.object(http, "_HAS_FETCHER", False)
@patch.object(http, "_HAS_CURL_CFFI", False)
@patch("httpx.request")
def test_fallback_parses_xml_with_encoding_declaration(mock_request):
    # lxml raises ValueError on str input with an encoding declaration;
    # the fallback must feed bytes to the parser (regression: dattebayo).
    xml = '<?xml version="1.0" encoding="UTF-8"?><html><body><p>ok</p></body></html>'
    mock_request.return_value = _mock_httpx_response(text=xml)

    response = http.fetch("https://example.com/feed")

    assert response.css("p").first.get_all_text(strip=True) == "ok"
    assert response.html_content == xml


@patch.object(http, "_HAS_FETCHER", False)
@patch("httpx.request")
def test_fetch_fallback_returns_selector(mock_request):
    mock_request.return_value = _mock_httpx_response()

    response = http.fetch("https://example.com/")

    assert response.status == 200
    assert response.css("a::attr(href)").get() == "x"
    method, url = mock_request.call_args[0]
    assert method == "GET"
    assert url == "https://example.com/"
    headers = mock_request.call_args[1]["headers"]
    assert "User-Agent" in headers


@patch.object(http, "_HAS_FETCHER", False)
@patch("httpx.request")
def test_fetch_fallback_merges_custom_headers(mock_request):
    mock_request.return_value = _mock_httpx_response()

    http.fetch("https://example.com/", headers={"X-Test": "1"})

    headers = mock_request.call_args[1]["headers"]
    assert headers["X-Test"] == "1"
    assert "User-Agent" in headers


@patch.object(http, "_HAS_FETCHER", False)
@patch("httpx.request")
def test_fetch_fallback_raises_on_bad_status(mock_request):
    mock_request.return_value = _mock_httpx_response(status=404)

    with pytest.raises(http.FetchError) as excinfo:
        http.fetch("https://example.com/")
    assert excinfo.value.status == 404


@patch.object(http, "_HAS_FETCHER", False)
@patch("httpx.request")
def test_fetch_fallback_no_raise_when_disabled(mock_request):
    mock_request.return_value = _mock_httpx_response(status=500)

    response = http.fetch("https://example.com/", raise_for_status=False)
    assert response.status == 500


@patch.object(http, "_HAS_FETCHER", False)
@patch("httpx.request")
def test_fetch_fallback_wraps_network_errors(mock_request):
    import httpx as _httpx

    mock_request.side_effect = _httpx.ConnectError("boom")

    with pytest.raises(http.FetchError):
        http.fetch("https://example.com/")


@patch.object(http, "_HAS_FETCHER", False)
@patch("httpx.request")
def test_post_fallback_passes_data_and_json(mock_request):
    mock_request.return_value = _mock_httpx_response(text='{"ok": true}')

    response = http.post(
        "https://example.com/api",
        data={"a": "1"},
        json=None,
        params={"q": "z"},
    )

    assert response.json() == {"ok": True}
    kwargs = mock_request.call_args[1]
    assert kwargs["data"] == {"a": "1"}
    assert kwargs["params"] == {"q": "z"}
    assert mock_request.call_args[0][0] == "POST"


@patch.object(http, "_HAS_FETCHER", False)
@patch("httpx.request")
def test_fetch_json_fallback(mock_request):
    mock_request.return_value = _mock_httpx_response(text='{"key": "value"}')

    assert http.fetch_json("https://example.com/api") == {"key": "value"}


def test_resolver_user_agent_matches_fallback_headers():
    assert http.resolver_user_agent() == http.RESOLVER_USER_AGENT
    assert http._FALLBACK_HEADERS["User-Agent"] == http.RESOLVER_USER_AGENT


@patch.object(http, "_HAS_FETCHER", False)
@patch.object(http, "_HAS_CURL_CFFI", True)
@patch.object(http, "_curl_cffi_request")
def test_fallback_prefers_curl_cffi(mock_curl):
    mock_curl.return_value = MagicMock(status=200)

    response = http.fetch("https://example.com/")

    assert response.status == 200
    mock_curl.assert_called_once()
    assert mock_curl.call_args[0] == ("GET", "https://example.com/")


@patch.object(http, "_HAS_FETCHER", False)
@patch.object(http, "_HAS_CURL_CFFI", True)
@patch.object(http, "_curl_cffi_request")
def test_post_fallback_prefers_curl_cffi(mock_curl):
    mock_curl.return_value = MagicMock(status=200)

    http.post("https://example.com/api", data={"a": "1"})

    mock_curl.assert_called_once()
    assert mock_curl.call_args[0][0] == "POST"
    assert mock_curl.call_args[1]["data"] == {"a": "1"}


@patch.object(http, "_HAS_FETCHER", False)
@patch.object(http, "_HAS_CURL_CFFI", True)
def test_curl_cffi_request_impersonates_chrome():
    fake_response = MagicMock()
    fake_response.text = "<html></html>"
    fake_response.content = b"<html></html>"
    fake_response.status_code = 200
    fake_response.url = "https://example.com/"
    fake_response.headers = {}

    fake_requests = MagicMock()
    fake_requests.request.return_value = fake_response

    import sys
    from unittest.mock import patch as _patch

    fake_curl_cffi = MagicMock()
    fake_curl_cffi.requests = fake_requests
    with _patch.dict(sys.modules, {"curl_cffi": fake_curl_cffi, "curl_cffi.requests": fake_requests}):
        response = http.fetch("https://example.com/")

    assert response.status == 200
    kwargs = fake_requests.request.call_args[1]
    assert kwargs["impersonate"] == http.CURL_IMPERSONATE
    assert kwargs["headers"]["User-Agent"] == http.RESOLVER_USER_AGENT
    assert kwargs["allow_redirects"] is True


@patch.object(http, "_HAS_FETCHER", False)
@patch.object(http, "_HAS_CURL_CFFI", True)
def test_curl_cffi_request_wraps_errors():
    import sys
    from unittest.mock import patch as _patch

    fake_requests = MagicMock()
    fake_requests.request.side_effect = RuntimeError("boom")
    fake_curl_cffi = MagicMock()
    fake_curl_cffi.requests = fake_requests

    with _patch.dict(sys.modules, {"curl_cffi": fake_curl_cffi, "curl_cffi.requests": fake_requests}):
        with pytest.raises(http.FetchError):
            http.fetch("https://example.com/")


def test_mpv_uses_resolver_user_agent():
    from utils.playback_hints import resolve_mpv_stream_options

    referrer, demuxer = resolve_mpv_stream_options(
        "https://cdn.example.com/x/index.m3u8", "https://ref"
    )
    assert referrer == "https://ref"
    assert demuxer is None
