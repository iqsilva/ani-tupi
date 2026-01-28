"""Plugin registry for managing scraper plugins."""


class PluginRegistry:
    """Manages plugin registration and discovery.

    Single responsibility: track which plugins are available.
    Uses singleton pattern to ensure single instance across application.
    """

    _instance = None

    def __new__(cls):
        """Enforce singleton pattern."""
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._plugins = {}
        return cls._instance

    def register(self, plugin) -> None:
        """Register a plugin by name.

        Args:
            plugin: Plugin instance with at least a 'name' attribute
        """
        self._plugins[plugin.name] = plugin

    def get_plugin(self, name: str):
        """Get plugin by name.

        Args:
            name: Plugin name

        Returns:
            Plugin instance or None if not found
        """
        return self._plugins.get(name)

    def get_active_sources(self) -> list[str]:
        """Get sorted list of registered plugin names.

        Returns:
            Sorted list of plugin names (e.g., ["animefire", "animesonlinecc"])
        """
        return sorted(list(self._plugins.keys()))

    def get_all_plugins(self) -> dict[str, object]:
        """Get all registered plugins.

        Returns:
            Dictionary mapping plugin names to plugin instances
        """
        return dict(self._plugins)

    @classmethod
    def reset_singleton(cls) -> None:
        """Reset singleton instance for testing.

        Use only in test fixtures.
        """
        cls._instance = None
