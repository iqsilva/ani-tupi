"""CLI tests for the config subcommand."""

import sys
from unittest.mock import patch

import pytest

import main


def test_config_subcommand_short_circuits_startup(monkeypatch):
    """`ani-tupi config` should route directly to config handler."""
    monkeypatch.setattr(sys, "argv", ["ani-tupi", "config"])

    with patch("utils.logging.configure_logging") as mock_configure:
        with patch.object(main, "config_cmd") as mock_config:
            with patch.object(main, "run_startup_update_check") as mock_startup:
                with patch("scrapers.loader.load_plugins") as mock_load_plugins:
                    mock_config.return_value = 0

                    with pytest.raises(SystemExit) as exc_info:
                        main.cli()

    assert exc_info.value.code == 0
    mock_configure.assert_called_once_with(debug=False)
    mock_config.assert_called_once()
    assert mock_startup.call_count == 0
    assert mock_load_plugins.call_count == 0
