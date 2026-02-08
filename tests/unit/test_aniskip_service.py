"""Tests for AniSkipService."""

import pytest
from unittest.mock import Mock, patch
import httpx

from services.anime.aniskip_service import AniSkipService
from models.models import SkipTimes


@pytest.fixture
def aniskip_service():
    """Create AniSkipService instance for testing."""
    return AniSkipService()


def test_get_skip_times_success(aniskip_service):
    """Test successful skip times retrieval."""
    mock_response = {
        "found": True,
        "results": [
            {
                "interval": {"startTime": 90.0, "endTime": 180.0},
                "skipType": "op",
                "episodeLength": 1420.0,
            },
            {
                "interval": {"startTime": 1320.0, "endTime": 1420.0},
                "skipType": "ed",
                "episodeLength": 1420.0,
            },
        ],
        "statusCode": 200,
    }

    with patch.object(httpx.Client, "get") as mock_get:
        mock_get.return_value = Mock(
            status_code=200, json=lambda: mock_response, raise_for_status=lambda: None
        )

        result = aniskip_service.get_skip_times(mal_id=12345, episode=1)

    assert result is not None
    assert isinstance(result, SkipTimes)
    assert result.op_start == 90.0
    assert result.op_end == 180.0
    assert result.ed_start == 1320.0
    assert result.ed_end == 1420.0


def test_get_skip_times_not_found(aniskip_service):
    """Test handling of 404 (no skip data available)."""
    with patch.object(httpx.Client, "get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        mock_get.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )

        result = aniskip_service.get_skip_times(mal_id=99999, episode=1)

    assert result is None


def test_get_skip_times_api_error(aniskip_service):
    """Test handling of API errors (500, etc)."""
    with patch.object(httpx.Client, "get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        mock_get.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=mock_response
        )

        result = aniskip_service.get_skip_times(mal_id=12345, episode=1)

    assert result is None


def test_get_skip_times_timeout(aniskip_service):
    """Test handling of timeout."""
    with patch.object(httpx.Client, "get") as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Timeout")

        result = aniskip_service.get_skip_times(mal_id=12345, episode=1)

    assert result is None


def test_get_skip_times_network_error(aniskip_service):
    """Test handling of network errors."""
    with patch.object(httpx.Client, "get") as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection failed")

        result = aniskip_service.get_skip_times(mal_id=12345, episode=1)

    assert result is None


def test_get_skip_times_cache(aniskip_service):
    """Test that skip times are cached per session."""
    mock_response = {
        "found": True,
        "results": [
            {
                "interval": {"startTime": 90.0, "endTime": 180.0},
                "skipType": "op",
                "episodeLength": 1420.0,
            }
        ],
        "statusCode": 200,
    }

    with patch.object(httpx.Client, "get") as mock_get:
        mock_get.return_value = Mock(
            status_code=200, json=lambda: mock_response, raise_for_status=lambda: None
        )

        # First call
        result1 = aniskip_service.get_skip_times(mal_id=12345, episode=1)
        # Second call (should be cached)
        result2 = aniskip_service.get_skip_times(mal_id=12345, episode=1)

    # API should only be called once due to caching
    assert mock_get.call_count == 1
    assert result1 is not None
    assert result2 is not None
    assert result1.op_start == result2.op_start


def test_get_skip_times_only_op(aniskip_service):
    """Test skip times with only OP (no ED)."""
    mock_response = {
        "found": True,
        "results": [
            {
                "interval": {"startTime": 90.0, "endTime": 180.0},
                "skipType": "op",
                "episodeLength": 1420.0,
            }
        ],
        "statusCode": 200,
    }

    with patch.object(httpx.Client, "get") as mock_get:
        mock_get.return_value = Mock(
            status_code=200, json=lambda: mock_response, raise_for_status=lambda: None
        )

        result = aniskip_service.get_skip_times(mal_id=12345, episode=1)

    assert result is not None
    assert result.op_start == 90.0
    assert result.op_end == 180.0
    assert result.ed_start is None
    assert result.ed_end is None


def test_get_skip_times_only_ed(aniskip_service):
    """Test skip times with only ED (no OP)."""
    mock_response = {
        "found": True,
        "results": [
            {
                "interval": {"startTime": 1320.0, "endTime": 1420.0},
                "skipType": "ed",
                "episodeLength": 1420.0,
            }
        ],
        "statusCode": 200,
    }

    with patch.object(httpx.Client, "get") as mock_get:
        mock_get.return_value = Mock(
            status_code=200, json=lambda: mock_response, raise_for_status=lambda: None
        )

        result = aniskip_service.get_skip_times(mal_id=12345, episode=1)

    assert result is not None
    assert result.op_start is None
    assert result.op_end is None
    assert result.ed_start == 1320.0
    assert result.ed_end == 1420.0


def test_get_skip_times_empty_results(aniskip_service):
    """Test handling of empty results (no skip times found)."""
    mock_response = {
        "found": False,
        "results": [],
        "statusCode": 200,
    }

    with patch.object(httpx.Client, "get") as mock_get:
        mock_get.return_value = Mock(
            status_code=200, json=lambda: mock_response, raise_for_status=lambda: None
        )

        result = aniskip_service.get_skip_times(mal_id=12345, episode=999)

    assert result is None


def test_clear_cache(aniskip_service):
    """Test cache clearing."""
    mock_response = {
        "found": True,
        "results": [
            {
                "interval": {"startTime": 90.0, "endTime": 180.0},
                "skipType": "op",
                "episodeLength": 1420.0,
            }
        ],
        "statusCode": 200,
    }

    with patch.object(httpx.Client, "get") as mock_get:
        mock_get.return_value = Mock(
            status_code=200, json=lambda: mock_response, raise_for_status=lambda: None
        )

        # Populate cache
        aniskip_service.get_skip_times(mal_id=12345, episode=1)
        assert mock_get.call_count == 1

        # Clear cache
        aniskip_service.clear_cache()

        # Next call should hit API again
        aniskip_service.get_skip_times(mal_id=12345, episode=1)
        assert mock_get.call_count == 2
