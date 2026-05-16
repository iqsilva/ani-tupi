"""Unit tests for AniList integration playback menus."""

import importlib


def test_build_anilist_post_playback_options_middle_episode():
    """Middle episode should include next and previous navigation."""
    mod = importlib.import_module("services.anime.anilist_integration")

    opts = mod.build_anilist_post_playback_options(current_episode_idx=4, num_episodes=12)

    assert any("▶️  Próximo" == opt for opt in opts)
    assert any("◀️  Anterior" == opt for opt in opts)
    assert "🔁 Replay" in opts


def test_build_anilist_post_playback_options_last_episode_prioritizes_back_option():
    """Last episode should offer a safe back option as the first choice."""
    mod = importlib.import_module("services.anime.anilist_integration")

    opts = mod.build_anilist_post_playback_options(current_episode_idx=6, num_episodes=7)

    assert opts[0] == "↩️  Voltar ao menu anterior"
    assert not any("▶️  Próximo" == opt for opt in opts)
    assert any("◀️  Anterior" == opt for opt in opts)
    assert "🔁 Replay" in opts
