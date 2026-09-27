"""Tests for the logger module."""

import logging
from unittest.mock import patch

from solis_energy_manager.logger import _DATE_FORMAT, _FORMAT, get_logger


def test_get_logger_returns_named_logger():
    """Test that get_logger returns a logger with the requested name."""
    logger = get_logger("my.module")

    assert isinstance(logger, logging.Logger)
    assert logger.name == "my.module"


def test_get_logger_configures_root_logger_when_no_handlers_exist():
    """Test that get_logger configures logging when no root handlers exist."""
    with (
        patch.object(logging.root, "handlers", []),
        patch("logging.basicConfig") as mock_basic_config,
    ):
        get_logger("test")

        mock_basic_config.assert_called_once_with(
            format=_FORMAT,
            datefmt=_DATE_FORMAT,
            level=logging.INFO,
        )


def test_get_logger_does_not_reconfigure_root_logger_when_handlers_exist():
    """Test that get_logger does not call basicConfig when handlers exist."""
    dummy_handler = logging.StreamHandler()

    with (
        patch.object(logging.root, "handlers", [dummy_handler]),
        patch("logging.basicConfig") as mock_basic_config,
    ):
        get_logger("test")

        mock_basic_config.assert_not_called()


def test_get_logger_does_not_reconfigure_logging():
    """Test that repeated calls to get_logger do not reconfigure logging."""
    dummy_handler = logging.StreamHandler()

    with (
        patch.object(logging.root, "handlers", [dummy_handler]),
        patch("logging.basicConfig") as mock_basic_config,
    ):
        get_logger("first")
        get_logger("second")

        mock_basic_config.assert_not_called()
        assert logging.root.handlers == [dummy_handler]
