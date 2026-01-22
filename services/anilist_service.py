"""AniList API integration - backward compatibility shim.

This module maintains backward compatibility by re-exporting
the new modular AniList client.

New code should import from services.anilist directly:
    from services.anilist import anilist_client, AniListClient
"""

from services.anilist import AniListClient, anilist_client

__all__ = ["AniListClient", "anilist_client"]
