"""Shared pytest fixtures."""

import logging

import pytest


@pytest.fixture
def isolated_root_logger():
    """Provide an isolated root logger and restore its state after the test."""
    root_logger = logging.getLogger()

    original_handlers = root_logger.handlers.copy()
    original_level = root_logger.level

    root_logger.handlers.clear()
    root_logger.setLevel(logging.NOTSET)

    try:
        yield root_logger
    finally:
        root_logger.handlers.clear()
        root_logger.handlers.extend(original_handlers)
        root_logger.setLevel(original_level)
