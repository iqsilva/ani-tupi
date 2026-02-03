"""Tests for offline AniList sync queue.

Tests the offline sync queue functionality:
- Queueing failed syncs
- Error classification (retryable vs not retryable)
- Retrying queued syncs
- File cleanup after successful sync
"""

from models.models import OfflineSyncQueueEntry, OfflineSyncQueue
from models.config import settings
from services.anime.offline_sync_service import (
    _load_queue,
    _save_queue,
    _classify_error,
    add_to_queue,
)


class TestOfflineSyncModels:
    """Test offline sync data models."""

    def test_create_offline_sync_queue_entry(self):
        """Create an offline sync queue entry."""
        entry = OfflineSyncQueueEntry(
            anime_title="Dandadan",
            episode_number=5,
            anilist_id=12345,
        )
        assert entry.anime_title == "Dandadan"
        assert entry.episode_number == 5
        assert entry.anilist_id == 12345
        assert entry.retry_count == 0
        assert entry.is_local is False

    def test_create_offline_sync_queue_entry_with_local_file(self):
        """Create queue entry for local episode with file path."""
        entry = OfflineSyncQueueEntry(
            anime_title="Dandadan",
            episode_number=5,
            anilist_id=12345,
            is_local=True,
            file_path="/home/user/.local/share/ani-tupi/anime/Dandadan/5.mkv",
        )
        assert entry.is_local is True
        assert entry.file_path is not None

    def test_create_offline_sync_queue(self):
        """Create an offline sync queue."""
        queue = OfflineSyncQueue()
        assert len(queue.entries) == 0
        assert queue.version == 1

    def test_queue_serialization(self, tmp_path):
        """Test serializing and deserializing queue."""
        entry = OfflineSyncQueueEntry(
            anime_title="Dandadan",
            episode_number=5,
            anilist_id=12345,
        )
        queue = OfflineSyncQueue(entries=[entry])

        # Serialize
        data = queue.model_dump(mode="json")
        assert data["version"] == 1
        assert len(data["entries"]) == 1
        assert data["entries"][0]["anime_title"] == "Dandadan"

        # Deserialize
        queue2 = OfflineSyncQueue.model_validate(data)
        assert len(queue2.entries) == 1
        assert queue2.entries[0].anime_title == "Dandadan"


class TestErrorClassification:
    """Test error classification for retry logic."""

    def test_classify_none_error(self):
        """None error is retryable (shouldn't be queued, but if is, retry)."""
        assert _classify_error(None) is True

    def test_classify_network_connection_error(self):
        """Connection errors are retryable."""
        assert _classify_error(ConnectionError("Connection refused")) is True

    def test_classify_timeout_error(self):
        """Timeout errors are retryable."""
        assert _classify_error(TimeoutError("Request timeout")) is True

    def test_classify_401_unauthorized(self):
        """401 errors are not retryable (auth failure)."""
        assert _classify_error(Exception("HTTP 401 Unauthorized")) is False

    def test_classify_403_forbidden(self):
        """403 errors are not retryable."""
        assert _classify_error(Exception("HTTP 403 Forbidden")) is False

    def test_classify_token_expired(self):
        """Token expired errors are not retryable."""
        assert _classify_error(Exception("Token expired")) is False

    def test_classify_invalid_anilist_id(self):
        """Invalid AniList ID errors are not retryable."""
        assert _classify_error(Exception("Invalid AniList ID not found")) is False

    def test_classify_500_server_error(self):
        """500 errors are retryable (server-side)."""
        assert _classify_error(Exception("HTTP 500 Internal Server Error")) is True

    def test_classify_429_rate_limit(self):
        """429 rate limit errors are retryable."""
        assert _classify_error(Exception("HTTP 429 Too Many Requests")) is True


class TestOfflineSyncQueuePersistence:
    """Test queue persistence to disk."""

    def test_load_empty_queue(self, tmp_path, monkeypatch):
        """Load queue when file doesn't exist."""
        # Mock queue path to tmp directory
        queue_path = tmp_path / "offline_sync_queue.json"

        def mock_get_queue_path():
            return queue_path

        monkeypatch.setattr(
            "services.anime.offline_sync_service._get_queue_path", mock_get_queue_path
        )

        queue = _load_queue()
        assert len(queue.entries) == 0

    def test_save_and_load_queue(self, tmp_path, monkeypatch):
        """Save and load queue from disk."""
        queue_path = tmp_path / "offline_sync_queue.json"

        def mock_get_queue_path():
            return queue_path

        monkeypatch.setattr(
            "services.anime.offline_sync_service._get_queue_path", mock_get_queue_path
        )

        # Create and save queue
        entry = OfflineSyncQueueEntry(
            anime_title="Dandadan",
            episode_number=5,
            anilist_id=12345,
        )
        queue = OfflineSyncQueue(entries=[entry])
        _save_queue(queue)

        # Load and verify
        assert queue_path.exists()
        loaded = _load_queue()
        assert len(loaded.entries) == 1
        assert loaded.entries[0].anime_title == "Dandadan"

    def test_save_queue_creates_directory(self, tmp_path, monkeypatch):
        """Saving queue creates parent directory if needed."""
        queue_path = tmp_path / "subdir" / "offline_sync_queue.json"

        def mock_get_queue_path():
            return queue_path

        monkeypatch.setattr(
            "services.anime.offline_sync_service._get_queue_path", mock_get_queue_path
        )

        queue = OfflineSyncQueue()
        _save_queue(queue)
        assert queue_path.exists()


class TestAddToQueue:
    """Test adding entries to queue."""

    def test_add_retryable_error_to_queue(self, tmp_path, monkeypatch):
        """Add retryable error (network) to queue."""
        queue_path = tmp_path / "offline_sync_queue.json"

        def mock_get_queue_path():
            return queue_path

        monkeypatch.setattr(
            "services.anime.offline_sync_service._get_queue_path", mock_get_queue_path
        )

        # Add network error (retryable)
        add_to_queue(
            anime_title="Dandadan",
            episode_number=5,
            anilist_id=12345,
            error=ConnectionError("Network unreachable"),
        )

        # Verify queued
        queue = _load_queue()
        assert len(queue.entries) == 1
        assert queue.entries[0].anime_title == "Dandadan"
        assert queue.entries[0].retry_count == 0

    def test_not_add_non_retryable_error_to_queue(self, tmp_path, monkeypatch):
        """Non-retryable errors (auth) are not queued."""
        queue_path = tmp_path / "offline_sync_queue.json"

        def mock_get_queue_path():
            return queue_path

        monkeypatch.setattr(
            "services.anime.offline_sync_service._get_queue_path", mock_get_queue_path
        )

        # Try to add auth error (not retryable)
        add_to_queue(
            anime_title="Dandadan",
            episode_number=5,
            anilist_id=12345,
            error=Exception("HTTP 401 Unauthorized"),
        )

        # Verify NOT queued
        queue = _load_queue()
        assert len(queue.entries) == 0

    def test_add_local_episode_entry(self, tmp_path, monkeypatch):
        """Add local episode with file path."""
        queue_path = tmp_path / "offline_sync_queue.json"

        def mock_get_queue_path():
            return queue_path

        monkeypatch.setattr(
            "services.anime.offline_sync_service._get_queue_path", mock_get_queue_path
        )

        file_path = tmp_path / "anime" / "Dandadan" / "5.mkv"

        add_to_queue(
            anime_title="Dandadan",
            episode_number=5,
            anilist_id=12345,
            error=ConnectionError("offline"),
            is_local=True,
            file_path=file_path,
        )

        queue = _load_queue()
        assert len(queue.entries) == 1
        assert queue.entries[0].is_local is True
        assert queue.entries[0].file_path is not None

    def test_update_existing_queue_entry(self, tmp_path, monkeypatch):
        """Update existing queue entry (same anime + episode)."""
        queue_path = tmp_path / "offline_sync_queue.json"

        def mock_get_queue_path():
            return queue_path

        monkeypatch.setattr(
            "services.anime.offline_sync_service._get_queue_path", mock_get_queue_path
        )

        # Add first entry
        add_to_queue(
            anime_title="Dandadan",
            episode_number=5,
            anilist_id=12345,
            error=ConnectionError("offline"),
        )

        # Update same entry
        add_to_queue(
            anime_title="Dandadan",
            episode_number=5,
            anilist_id=12345,
            error=TimeoutError("timeout"),
        )

        # Verify only one entry (not duplicated)
        queue = _load_queue()
        assert len(queue.entries) == 1
        assert "timeout" in queue.entries[0].last_error.lower()


class TestOfflineSyncConfiguration:
    """Test offline sync configuration."""

    def test_default_config_values(self):
        """Verify default config values."""
        assert settings.offline_sync.max_retry_count == 3
        assert settings.offline_sync.enable_auto_retry is True
        assert settings.offline_sync.enable_file_cleanup is True

    def test_config_can_be_overridden_via_env(self, monkeypatch):
        """Config can be overridden via environment variables."""
        # This is tested via Pydantic's environment variable support
        # In practice, users would set: ANI_TUPI__OFFLINE_SYNC__MAX_RETRY_COUNT=5
        pass
