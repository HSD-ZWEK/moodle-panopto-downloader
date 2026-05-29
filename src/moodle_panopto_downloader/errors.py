# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Hochschule Düsseldorf – University of Applied Sciences
# ZWEK – Centre for Training and Competence Development
# Developed within the KIVi-Azubi research project
"""Exception hierarchy for moodle-panopto-downloader.

All errors raised intentionally by the package derive from
:class:`MoodlePanoptoError`, so callers (including the CLI) can catch the whole
family with a single ``except``.
"""

from __future__ import annotations


class MoodlePanoptoError(Exception):
    """Base class for all errors raised by this package."""


class ConfigError(MoodlePanoptoError):
    """Configuration is missing or inconsistent (e.g. no base URL or token)."""


class MoodleAPIError(MoodlePanoptoError):
    """A Moodle Web Services call returned an exception payload.

    Attributes:
        function: The web service function that failed.
        errorcode: Moodle's machine-readable error code, if any.
    """

    def __init__(self, function: str, errorcode: str | None, message: str) -> None:
        self.function = function
        self.errorcode = errorcode
        super().__init__(f"{function}: {errorcode or 'error'} — {message}")


class MoodleConnectionError(MoodlePanoptoError):
    """The Moodle server could not be reached or returned an invalid response."""


class DownloaderError(MoodlePanoptoError):
    """The download backend (yt-dlp) is unavailable or failed to start."""
