"""CLI tests for --version flag behavior."""

import sys
from unittest.mock import patch

import pytest

import main


def test_version_flag_shows_info_and_exits(monkeypatch):
    """--version should show version info and exit before normal startup flow."""
    monkeypatch.setattr(sys, "argv", ["ani-tupi", "--version"])

    with patch("utils.logging.configure_logging") as mock_configure:
        with patch.object(main, "show_version_info") as mock_show_version:
            with patch.object(main, "run_startup_update_check") as mock_update:
                with patch("scrapers.loader.load_plugins") as mock_load_plugins:
                    with pytest.raises(SystemExit) as exc_info:
                        main.cli()

    assert exc_info.value.code == 0
    mock_configure.assert_called_once_with(debug=False)
    mock_show_version.assert_called_once()
    assert mock_update.call_count == 0
    assert mock_load_plugins.call_count == 0
