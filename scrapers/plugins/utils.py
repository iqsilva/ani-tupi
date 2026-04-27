def store_player_source(container: list, event, source: str) -> bool:
    """Append a player source once and signal completion."""
    if event.is_set():
        return False
    container.append(source)
    event.set()
    return True


def load_plugin_if_supported(plugin_cls, languages_dict, register) -> None:
    """Register a plugin only when at least one language matches."""
    if any(language in languages_dict for language in plugin_cls.languages):
        register(plugin_cls())
