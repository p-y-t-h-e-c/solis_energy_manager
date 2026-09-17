"""Project Logging configuration."""

import logging

_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s"
_DATE_FORMAT = "%Y/%m/%d %H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """Return a named logger, configuring the root logger on first call.

    If the root logger has no handlers attached, ``logging.basicConfig`` is
    called with a standard format and ``INFO`` as the default level.
    Subsequent calls skip configuration entirely, so it is safe to call this
    function at module import time in every module.

    The check against ``logging.root.handlers`` means that any logging setup
    performed before the first ``get_logger`` call — by a framework, a test
    fixture, or an entry point — is preserved and not overwritten.

    Args:
        name: Logger name, typically ``__name__`` of the calling module.
            This causes log records to carry the fully qualified module path
            (e.g. ``myproject.pipeline``), making it straightforward to trace
            the origin of a message or filter output by module.

    Returns:
        logging.Logger: A logger instance bound to ``name``.
    """
    if not logging.root.handlers:
        logging.basicConfig(
            format=_FORMAT,
            datefmt=_DATE_FORMAT,
            level=logging.INFO,
        )
    return logging.getLogger(name)


if __name__ == "__main__":
    logger = get_logger(__name__)
    logger.info("Logging configured successfully")
