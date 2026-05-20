def store_player_source(container: list, event, source: str) -> bool:
    """Append a player source once and signal completion."""
    if event.is_set():
        return False
    container.append(source)
    event.set()
    return True


def load_plugin(plugin_cls, register) -> None:
    """Register an anime plugin."""
    register(plugin_cls())
