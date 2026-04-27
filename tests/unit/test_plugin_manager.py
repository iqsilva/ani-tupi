import plugin_manager


class PluginSettingsStub:
    disabled_plugins = ["animefire"]
    priority_order = ["sushianimes", "animesdigital", "animefire"]


class SettingsStub:
    plugins = PluginSettingsStub()


def test_plugin_helpers_read_configured_settings(monkeypatch):
    monkeypatch.setattr(plugin_manager, "settings", SettingsStub())
    monkeypatch.setattr(
        plugin_manager,
        "get_all_available_plugins",
        lambda: ["animefire", "animesdigital", "sushianimes"],
    )

    assert plugin_manager.get_enabled_plugins() == ["animesdigital", "sushianimes"]
    assert plugin_manager.get_plugin_priority_order() == [
        "sushianimes",
        "animesdigital",
        "animefire",
    ]
