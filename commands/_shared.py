"""Shared post-playback navigation helpers used by anime and local_anime commands."""

# Navigation action labels (used for menu display and matching)
NAV_NEXT = "▶️  Próximo"
NAV_PREV = "◀️  Anterior"
NAV_REPLAY = "🔁 Replay"


def build_nav_options(
    has_next: bool,
    has_prev: bool,
    extra: list[str],
    *,
    back_label: str | None = None,
) -> list[str]:
    """Build ordered nav option list. extra options appended after core navigation.

    When back_label is provided and has_next is False, back_label takes the first
    position instead of NAV_NEXT (preserving the expected option order for callers
    that want a 'safe exit' as the primary action at the last episode).
    """
    opts = []
    if has_next:
        opts.append(NAV_NEXT)
    elif back_label:
        opts.append(back_label)
    if has_prev:
        opts.append(NAV_PREV)
    opts.append(NAV_REPLAY)
    opts.extend(extra)
    return opts


def is_next(choice: str) -> bool:
    return NAV_NEXT in choice


def is_prev(choice: str) -> bool:
    return NAV_PREV in choice


def is_replay(choice: str) -> bool:
    return NAV_REPLAY in choice
