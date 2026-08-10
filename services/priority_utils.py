"""Priority-based sorting utilities for source selection."""


def sort_by_priority(
    items: list,
    priority_order: list[str],
    source_index: int = 1,
    preferred_source: str | None = None,
) -> list:
    """Sort items by source priority.

    Sorts a list of items (tuples or objects with indexed access) by a source's
    priority order. Items with sources not in priority_order are placed last.

    Args:
        items: List of tuples/sequences where source_index indicates the source field
        priority_order: List of source names in priority order (highest first)
        source_index: Index position of the source name in each item (default: 1)
        preferred_source: Optional source name to always rank first (overrides
            priority_order); remaining items keep priority order as fallback

    Returns:
        Sorted list of items, ordered by priority (highest first)

    Example:
        >>> sources = [("url1", "dub"), ("url2", "sub"), ("url3", "dub")]
        >>> priority = ["sub", "dub"]
        >>> sorted_sources = sort_by_priority(sources, priority, source_index=1)
        # Result: [("url2", "sub"), ("url1", "dub"), ("url3", "dub")]
    """
    if not items:
        return []

    def priority_key(item):
        source = item[source_index]
        if preferred_source and source == preferred_source:
            return -1
        if source in priority_order:
            return priority_order.index(source)
        return len(priority_order)

    return sorted(items, key=priority_key)
