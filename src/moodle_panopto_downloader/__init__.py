# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Hochschule Düsseldorf – University of Applied Sciences
# ZWEK – Centre for Training and Competence Development
# Developed within the KIVi-Azubi research project
"""moodle-panopto-downloader — discover and download Panopto videos linked in Moodle courses.

The package exposes a small, testable API:

- :class:`~moodle_panopto_downloader.config.Config` — resolved runtime configuration.
- :class:`~moodle_panopto_downloader.moodle.MoodleClient` — thin Moodle Web Services client.
- :func:`~moodle_panopto_downloader.panopto.extract_links` — pure Panopto link extraction.
- :func:`~moodle_panopto_downloader.downloader.download` — yt-dlp invocation.

The command-line entry point lives in :mod:`moodle_panopto_downloader.cli`.
"""

from __future__ import annotations

__all__ = ["__version__"]
__version__ = "1.0.0"
