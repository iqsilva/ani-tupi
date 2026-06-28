DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


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
