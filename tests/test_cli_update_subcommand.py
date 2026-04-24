"""CLI tests for the update subcommand."""

import sys
from unittest.mock import patch

import pytest

import main


def test_update_subcommand_short_circuits_startup(monkeypatch):
    """`ani-tupi update` should route directly to the update handler."""
    monkeypatch.setattr(sys, "argv", ["ani-tupi", "update"])

    with patch("utils.logging.configure_logging") as mock_configure:
        with patch.object(main, "update_cmd") as mock_update:
            with patch.object(main, "run_startup_update_check") as mock_startup:
                with patch("scrapers.loader.load_plugins") as mock_load_plugins:
                    mock_update.return_value = 0

                    with pytest.raises(SystemExit) as exc_info:
                        main.cli()

    assert exc_info.value.code == 0
    mock_configure.assert_called_once_with(debug=False)
    mock_update.assert_called_once()
    assert mock_startup.call_count == 0
    assert mock_load_plugins.call_count == 0
