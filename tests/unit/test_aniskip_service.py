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


def test_get_skip_times_error_scenarios(aniskip_service):
    """Test handling of various error scenarios (404, 500, timeout, network)."""
    # Scenario 1: 404 Not Found
    with patch.object(httpx.Client, "get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        mock_get.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )
        result = aniskip_service.get_skip_times(mal_id=99999, episode=1)
        assert result is None

    # Scenario 2: 500 Server Error
    with patch.object(httpx.Client, "get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        mock_get.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=mock_response
        )
        result = aniskip_service.get_skip_times(mal_id=12345, episode=1)
        assert result is None

    # Scenario 3: Timeout
    with patch.object(httpx.Client, "get") as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Timeout")
        result = aniskip_service.get_skip_times(mal_id=12345, episode=1)
        assert result is None

    # Scenario 4: Network Error
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


def test_get_skip_available_batch_mixed(aniskip_service):
    """Test batch checking with mixed results (some have skip, some don't)."""

    def mock_get_skip_times(mal_id: int, episode: int):
        """Mock: episodes 1, 3, 5 have skip times."""
        if episode in [1, 3, 5]:
            return SkipTimes(op_start=90.0, op_end=180.0, ed_start=None, ed_end=None)
        return None

    with patch.object(aniskip_service, "get_skip_times", side_effect=mock_get_skip_times):
        result = aniskip_service.get_skip_available_batch(mal_id=12345, max_episode=5)

    assert result == {1: True, 2: False, 3: True, 4: False, 5: True}


def test_get_skip_available_batch_all_have_skip(aniskip_service):
    """Test batch checking where all episodes have skip times."""

    def mock_get_skip_times(mal_id: int, episode: int):
        """Mock: all episodes have skip times."""
        return SkipTimes(op_start=90.0, op_end=180.0, ed_start=None, ed_end=None)

    with patch.object(aniskip_service, "get_skip_times", side_effect=mock_get_skip_times):
        result = aniskip_service.get_skip_available_batch(mal_id=12345, max_episode=3)

    assert result == {1: True, 2: True, 3: True}


def test_get_skip_available_batch_none_have_skip(aniskip_service):
    """Test batch checking where no episodes have skip times."""

    def mock_get_skip_times(mal_id: int, episode: int):
        """Mock: no episodes have skip times."""
        return None

    with patch.object(aniskip_service, "get_skip_times", side_effect=mock_get_skip_times):
        result = aniskip_service.get_skip_available_batch(mal_id=12345, max_episode=3)

    assert result == {1: False, 2: False, 3: False}


def test_get_skip_available_batch_empty(aniskip_service):
    """Test batch checking with zero episodes."""
    with patch.object(aniskip_service, "get_skip_times"):
        result = aniskip_service.get_skip_available_batch(mal_id=12345, max_episode=0)

    assert result == {}


def test_get_skip_available_batch_error_handling(aniskip_service):
    """Test batch checking gracefully handles errors on individual episodes."""

    def mock_get_skip_times(mal_id: int, episode: int):
        """Mock: episode 2 throws error, others work."""
        if episode == 2:
            raise Exception("API error")
        return (
            SkipTimes(op_start=90.0, op_end=180.0, ed_start=None, ed_end=None)
            if episode in [1, 3]
            else None
        )

    with patch.object(aniskip_service, "get_skip_times", side_effect=mock_get_skip_times):
        result = aniskip_service.get_skip_available_batch(mal_id=12345, max_episode=3)

    # Episode 2 should be False (error treated as no skip)
    assert result == {1: True, 2: False, 3: True}


def test_get_skip_available_batch_specific_episodes(aniskip_service):
    """Test batch checking with specific episode list (optimization)."""

    def mock_get_skip_times(mal_id: int, episode: int):
        """Mock: episodes 1, 3, 5 have skip times."""
        if episode in [1, 3, 5]:
            return SkipTimes(op_start=90.0, op_end=180.0, ed_start=None, ed_end=None)
        return None

    with patch.object(aniskip_service, "get_skip_times", side_effect=mock_get_skip_times):
        # Only check episodes 1, 3, 5
        result = aniskip_service.get_skip_available_batch(
            mal_id=12345, max_episode=10, episodes_to_check=[1, 3, 5]
        )

    # Should only have results for requested episodes
    assert result == {1: True, 3: True, 5: True}
    assert len(result) == 3  # Only 3 episodes checked


def test_get_skip_available_batch_three_episodes_optimization(aniskip_service):
    """Test optimization: checking only next/current/previous."""

    def mock_get_skip_times(mal_id: int, episode: int):
        """Mock: episodes 120, 121, 122 have skip times."""
        if episode in [120, 121, 122]:
            return SkipTimes(op_start=90.0, op_end=180.0, ed_start=None, ed_end=None)
        return None

    with patch.object(aniskip_service, "get_skip_times", side_effect=mock_get_skip_times):
        # Optimization: Only check próximo (121), atual (120), anterior (119)
        result = aniskip_service.get_skip_available_batch(
            mal_id=12345, max_episode=148, episodes_to_check=[119, 120, 121]
        )

    # Fast: only 3 API calls instead of 148
    assert result == {119: False, 120: True, 121: True}
    assert len(result) == 3


def test_get_skip_available_batch_empty_list(aniskip_service):
    """Test batch checking with empty episode list."""
    with patch.object(aniskip_service, "get_skip_times") as mock_get:
        result = aniskip_service.get_skip_available_batch(
            mal_id=12345, max_episode=100, episodes_to_check=[]
        )

    # Should return empty dict without any API calls
    assert result == {}
    assert mock_get.call_count == 0
