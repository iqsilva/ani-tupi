"""Tests for history service behavior."""

from utils.persistence import JSONStore


class TestHistoryService:
    def test_save_history_persists_all_source_urls(self, temp_dir, repository, monkeypatch):
        from services import history_service

        history_store = JSONStore(temp_dir / "history.json")
        monkeypatch.setattr(history_service, "_history_store", history_store)
        monkeypatch.setattr(history_service, "rep", repository)

        repository.add_anime("Goblin Slayer", "https://example.com/animefire", "animefire", {})
        repository.add_anime(
            "Goblin Slayer", "https://example.com/animesdigital", "animesdigital", {}
        )

        history_service.save_history("Goblin Slayer", 1, source="animefire")

        stored = history_store.load({})
        assert stored["Goblin Slayer"][5] == {
            "animefire": "https://example.com/animefire",
            "animesdigital": "https://example.com/animesdigital",
        }
