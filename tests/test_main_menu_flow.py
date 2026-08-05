"""Tests for main menu looping behavior."""

from types import SimpleNamespace

import main


def test_main_menu_flow_returns_to_main_menu_after_submenu(monkeypatch):
    """Returning from a submenu should redisplay the main menu."""
    choices = iter(["🔍 Buscar Anime", "⚙️  Gerenciar Fontes"])
    seen = []

    def fake_show_main_menu():
        return next(choices)

    def fake_anime_cmd(args):
        seen.append("anime")

    def fake_manage_sources(args):
        seen.append("sources")
        raise SystemExit(0)

    monkeypatch.setattr(main, "show_main_menu", fake_show_main_menu)
    monkeypatch.setattr(main, "anime_cmd", fake_anime_cmd)
    monkeypatch.setattr(main, "manage_sources_cmd", fake_manage_sources)
    args = SimpleNamespace(continue_watching=False)

    try:
        main.main_menu_flow(args)
    except SystemExit:
        pass

    assert seen == ["anime", "sources"]
