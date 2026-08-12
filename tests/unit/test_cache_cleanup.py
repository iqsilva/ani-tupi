def test_clear_cache_all_uses_unified_cache(monkeypatch):
    from utils import cache_manager

    called = {"clear": False}
    monkeypatch.setattr(cache_manager, "_clear_all", lambda: called.__setitem__("clear", True))

    cache_manager.clear_cache_all()

    assert called["clear"]
