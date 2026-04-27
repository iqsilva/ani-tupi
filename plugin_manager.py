"""Plugin/source management helpers."""

from models.config import settings
from services.repository import rep
from ui.components import menu_navigate
from utils.logging import get_logger

logger = get_logger(__name__)


def get_all_available_plugins() -> list[str]:
    """Get list of all available plugins (by scanning plugins/ directory).

    Returns:
        List of plugin names (sorted alphabetically)
    """
    from os import listdir
    from os.path import isfile, join

    from scrapers.loader import get_resource_path

    # Scan plugins directory
    path = get_resource_path("plugins/")
    system = {"__init__.py", "utils.py"}

    try:
        all_plugins = [
            file[:-3]
            for file in listdir(path)
            if isfile(join(path, file)) and file.endswith(".py") and file not in system
        ]
        return sorted(all_plugins)
    except Exception:
        # Fallback: get from repository if directory scan fails
        return sorted(rep.get_active_sources())


def plugin_management_menu() -> None:
    """Show configured plugin status and priority order."""
    all_plugins = get_all_available_plugins()
    disabled_plugins = set(settings.plugins.disabled_plugins)
    priority_order = settings.plugins.priority_order

    if not all_plugins:
        logger.info("\n❌ Nenhum plugin encontrado!")
        input("\nPressione Enter para continuar...")
        return

    priority_index = {plugin: index for index, plugin in enumerate(priority_order)}
    ordered_plugins = sorted(
        all_plugins,
        key=lambda plugin: (priority_index.get(plugin, len(priority_order)), plugin),
    )
    options = [
        f"{'❌' if plugin in disabled_plugins else '✅'} {plugin}" for plugin in ordered_plugins
    ]
    options.append("Voltar")

    menu_navigate(
        options,
        msg="Fontes configuradas via ANI_TUPI__PLUGINS__DISABLED_PLUGINS / PRIORITY_ORDER",
    )


def get_enabled_plugins() -> list[str]:
    """Get list of enabled plugin names (excluding disabled ones)."""
    disabled_plugins = set(settings.plugins.disabled_plugins)
    return [plugin for plugin in get_all_available_plugins() if plugin not in disabled_plugins]


def get_plugin_priority_order() -> list[str]:
    """Get plugin priority order from settings."""
    return settings.plugins.priority_order
