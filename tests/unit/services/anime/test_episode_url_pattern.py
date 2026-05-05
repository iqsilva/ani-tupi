"""Tests for services/anime/episode_url_pattern.py"""

from unittest.mock import MagicMock, patch


from services.anime.episode_url_pattern import (
    derive_episode_url,
    detect_episode_pattern,
    validate_episode_url,
)


CDN_URL = "https://cdn-s01.example.net/stream/y/my-anime/11.mp4/index.m3u8"
CDN_URL_PADDED = "https://cdn-s01.example.net/stream/y/my-anime/08.mp4/index.m3u8"
NO_PATTERN_URL = "https://example.com/player/embed/abc123"


class TestDetectEpisodePattern:
    def test_detects_unpadded_episode(self):
        info = detect_episode_pattern(CDN_URL)
        assert info is not None
        assert info["episode"] == 11
        assert info["padded"] is False
        assert info["width"] == 0

    def test_detects_padded_episode(self):
        info = detect_episode_pattern(CDN_URL_PADDED)
        assert info is not None
        assert info["episode"] == 8
        assert info["padded"] is True
        assert info["width"] == 2

    def test_returns_none_for_no_pattern(self):
        assert detect_episode_pattern(NO_PATTERN_URL) is None

    def test_returns_none_for_empty_string(self):
        assert detect_episode_pattern("") is None

    def test_three_digit_episode(self):
        url = "https://cdn.example.net/stream/123.mp4/index.m3u8"
        info = detect_episode_pattern(url)
        assert info is not None
        assert info["episode"] == 123
        assert info["padded"] is False


class TestDeriveEpisodeUrl:
    def test_unpadded_substitution(self):
        result = derive_episode_url(CDN_URL, 12)
        assert result == "https://cdn-s01.example.net/stream/y/my-anime/12.mp4/index.m3u8"

    def test_padded_substitution_preserves_padding(self):
        result = derive_episode_url(CDN_URL_PADDED, 9)
        assert result == "https://cdn-s01.example.net/stream/y/my-anime/09.mp4/index.m3u8"

    def test_padded_substitution_two_digits(self):
        result = derive_episode_url(CDN_URL_PADDED, 12)
        assert result == "https://cdn-s01.example.net/stream/y/my-anime/12.mp4/index.m3u8"

    def test_returns_none_for_no_pattern(self):
        assert derive_episode_url(NO_PATTERN_URL, 5) is None

    def test_single_digit_to_single_digit(self):
        url = "https://cdn.example.net/stream/y/anime/5.mp4/index.m3u8"
        result = derive_episode_url(url, 6)
        assert result == "https://cdn.example.net/stream/y/anime/6.mp4/index.m3u8"


class TestValidateEpisodeUrl:
    def test_returns_true_on_200(self):
        mock_response = MagicMock()
        mock_response.is_success = True

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.head.return_value = mock_response
            mock_client_cls.return_value = mock_client

            assert (
                validate_episode_url("https://cdn.example.net/stream/y/anime/11.mp4/index.m3u8")
                is True
            )

    def test_returns_false_on_404(self):
        mock_response = MagicMock()
        mock_response.is_success = False

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.head.return_value = mock_response
            mock_client_cls.return_value = mock_client

            assert (
                validate_episode_url("https://cdn.example.net/stream/y/anime/999.mp4/index.m3u8")
                is False
            )

    def test_returns_false_on_timeout(self):
        import httpx as _httpx

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.head.side_effect = _httpx.TimeoutException("timed out")
            mock_client.get.side_effect = _httpx.TimeoutException("timed out")
            mock_client_cls.return_value = mock_client

            assert (
                validate_episode_url("https://cdn.example.net/stream/y/anime/11.mp4/index.m3u8")
                is False
            )

    def test_returns_false_on_connection_error(self):
        import httpx as _httpx

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.head.side_effect = _httpx.ConnectError("refused")
            mock_client.get.side_effect = _httpx.ConnectError("refused")
            mock_client_cls.return_value = mock_client

            assert (
                validate_episode_url("https://cdn.example.net/stream/y/anime/11.mp4/index.m3u8")
                is False
            )

    def test_fallback_to_get_range_when_head_blocked(self):
        mock_head = MagicMock()
        mock_head.status_code = 405
        mock_head.is_success = False

        mock_get = MagicMock()
        mock_get.status_code = 206
        mock_get.is_success = True

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.head.return_value = mock_head
            mock_client.get.return_value = mock_get
            mock_client_cls.return_value = mock_client

            assert (
                validate_episode_url("https://cdn.example.net/stream/y/anime/11.mp4/index.m3u8")
                is True
            )

            mock_client.get.assert_called_once_with(
                "https://cdn.example.net/stream/y/anime/11.mp4/index.m3u8",
                headers={"Range": "bytes=0-1"},
            )

    def test_fallback_to_get_range_when_head_raises(self):
        import httpx as _httpx

        mock_get = MagicMock()
        mock_get.status_code = 206
        mock_get.is_success = True

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.head.side_effect = _httpx.TimeoutException("timed out")
            mock_client.get.return_value = mock_get
            mock_client_cls.return_value = mock_client

            assert (
                validate_episode_url("https://cdn.example.net/stream/y/anime/11.mp4/index.m3u8")
                is True
            )
