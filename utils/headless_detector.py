"""Headless authentication support.

Always uses headless mode (no browser) for AniList authentication.
Displays authorization URL and waits for token input via stdin.
"""

import getpass


def get_token_from_user(auth_url: str) -> str | None:
    """Prompt user to visit auth URL and provide token.

    Args:
        auth_url: The authorization URL to display

    Returns:
        Token string if provided, None if cancelled
    """
    print("\n" + "=" * 70)
    print("🔐 AniList Authentication")
    print("=" * 70)
    print("\n1. Visit this URL in your browser:\n")
    print(f"   {auth_url}\n")
    print("2. Authorize the application")
    print("3. Copy the access token from the URL (or from the page)")
    print("4. Paste it below when prompted\n")

    try:
        # Use getpass to mask token input (similar to password input)
        token = getpass.getpass("Paste token here (letters wont appear): ").strip()
        return token if token else None
    except (KeyboardInterrupt, EOFError):
        print("\n❌ Authentication cancelled.")
        return None
