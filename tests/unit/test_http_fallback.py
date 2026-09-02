"""Tests for the httpx fallback path in scrapers.core.http."""

from unittest.mock import MagicMock, patch

import pytest

from scrapers.core import http


def _mock_httpx_response(text="<html><body><a href='x'>hi</a></body></html>", status=200, url="https://example.com/"):
    resp = MagicMock()
    resp.text = text
    resp.status_code = status
    resp.url = url
    resp.headers = {"content-type": "text/html"}
    return resp


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
