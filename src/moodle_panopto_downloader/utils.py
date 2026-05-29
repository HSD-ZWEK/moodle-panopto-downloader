# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Hochschule Düsseldorf – University of Applied Sciences
# ZWEK – Centre for Training and Competence Development
# Developed within the KIVi-Azubi research project
"""Small, dependency-free helpers: logging setup and platform defaults."""

from __future__ import annotations

import logging
import sys

LOGGER_NAME = "moodle_panopto_downloader"


def get_logger() -> logging.Logger:
    """Return the package logger."""
    return logging.getLogger(LOGGER_NAME)


def configure_logging(verbosity: int = 0) -> None:
    """Configure logging to stderr.

    Args:
        verbosity: ``-1`` quiet (warnings only), ``0`` info (default),
            ``1`` or more debug.
    """
    if verbosity < 0:
        level = logging.WARNING
    elif verbosity == 0:
        level = logging.INFO
    else:
        level = logging.DEBUG

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    logger = get_logger()
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False


def default_browser() -> str:
    """Best-effort default browser for reading Panopto cookies, by platform."""
    return {"darwin": "safari", "win32": "chrome"}.get(sys.platform, "firefox")
