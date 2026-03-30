"""Unit tests for AniList authentication prompt on unauthenticated access."""

from unittest.mock import MagicMock, patch


class TestAnilistMenuAuthPrompt:
    """Tests for the auth prompt shown when user runs ani-tupi anilist without auth."""

    @patch("commands.anilist.anilist_main_menu")
    @patch("commands.anilist.authenticate_flow")
    @patch("commands.anilist.Confirm.ask")
    @patch("services.anilist_service.anilist_client")
    def test_unauthenticated_user_accepts_connects_then_opens_menu(
        self, mock_client, mock_confirm, mock_auth_flow, mock_menu
    ):
        """Unauthenticated user accepts prompt → auth flow runs → menu opens."""
        from commands.anilist import anilist_menu

        mock_client.is_authenticated.side_effect = [False, True]
        mock_confirm.return_value = True
        mock_menu.return_value = None  # exit immediately after auth

        anilist_menu(MagicMock())

        mock_confirm.assert_called_once()
        mock_auth_flow.assert_called_once()
        mock_menu.assert_called_once()

    @patch("commands.anilist.anilist_main_menu")
    @patch("commands.anilist.authenticate_flow")
    @patch("commands.anilist.Confirm.ask")
    @patch("services.anilist_service.anilist_client")
    def test_unauthenticated_user_refuses_exits_without_menu(
        self, mock_client, mock_confirm, mock_auth_flow, mock_menu
    ):
        """Unauthenticated user refuses prompt → exits without opening menu."""
        from commands.anilist import anilist_menu

        mock_client.is_authenticated.return_value = False
        mock_confirm.return_value = False

        anilist_menu(MagicMock())

        mock_auth_flow.assert_not_called()
        mock_menu.assert_not_called()

    @patch("commands.anilist.anilist_main_menu")
    @patch("commands.anilist.Confirm.ask")
    @patch("services.anilist_service.anilist_client")
    def test_authenticated_user_opens_menu_directly(self, mock_client, mock_confirm, mock_menu):
        """Authenticated user → menu opens directly without prompt."""
        from commands.anilist import anilist_menu

        mock_client.is_authenticated.return_value = True
        mock_menu.return_value = None  # exit immediately

        anilist_menu(MagicMock())

        mock_confirm.assert_not_called()
        mock_menu.assert_called_once()
