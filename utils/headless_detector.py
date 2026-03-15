"""Headless authentication support.

Always uses headless mode (no browser) for AniList authentication.
Displays authorization URL and waits for token input via stdin.
"""

import getpass
from utils.logging import get_logger

logger = get_logger(__name__)


def get_token_from_user(auth_url: str) -> str | None:
    """Prompt user to visit auth URL and provide token.

    Args:
        auth_url: The authorization URL to display

    Returns:
        Token string if provided, None if cancelled
    """
    logger.info("\n" + "=" * 70)
    logger.info("🔐 AniList Authentication")
    logger.info("=" * 70)
    logger.info("\n1. Visit this URL in your browser:\n")
    logger.info(f"   {auth_url}\n")
    logger.info("2. Authorize the application")
    logger.info("3. Copy the access token from the URL (or from the page)")
    logger.info("4. Paste it below when prompted\n")

    try:
        # Use getpass to mask token input (similar to password input)
        token = getpass.getpass("Paste token here (letters wont appear): ").strip()
        return token if token else None
    except (KeyboardInterrupt, EOFError):
        logger.info("\n❌ Authentication cancelled.")
        return None
