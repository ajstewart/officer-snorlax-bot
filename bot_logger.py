"""Logging configuration for the bot.

Configures a single "snorlax" logger tree using `logging.config.dictConfig`.
The configured log level (from `bot_settings.log_level`) only applies to the
"snorlax" logger (and its children) - third party loggers are left untouched.
"""

import logging

from logging.config import dictConfig

from settings import bot_settings

LOGGER_NAME = "snorlax"
LOG_FORMAT = "[%(asctime)s] - %(name)s - %(levelname)s - %(message)s"

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        LOGGER_NAME: {
            "handlers": ["console"],
            "level": bot_settings.log_level.upper(),
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}


def setup_logging() -> None:
    """Configure the "snorlax" logger tree via `logging.config.dictConfig`.

    Must be called once (e.g. during bot startup) before the logger is used.
    """
    dictConfig(LOGGING_CONFIG)


def get_logger(name: str | None = None) -> logging.Logger:
    """Get the "snorlax" logger, optionally namespaced under a module name.

    Args:
        name: If provided, the returned logger will be named
            "snorlax.<name>", e.g. calling `get_logger(__name__)` from
            `cogs/initial.py` will return a logger named
            "snorlax.cogs.initial". If omitted, the base "snorlax" logger
            is returned.

    Returns:
        The requested logger instance.
    """
    if name is None:
        return logging.getLogger(LOGGER_NAME)

    return logging.getLogger(f"{LOGGER_NAME}.{name}")
