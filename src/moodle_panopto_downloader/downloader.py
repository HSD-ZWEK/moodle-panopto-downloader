# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Hochschule Düsseldorf – University of Applied Sciences
# ZWEK – Centre for Training and Competence Development
# Developed within the KIVi-Azubi research project
"""Download backend: build and run the yt-dlp commands.

Command construction is separated from execution so the argument lists can be
unit-tested without invoking yt-dlp. Commands are always built as argument lists
(never a shell string), so course/host values cannot cause shell injection.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from collections.abc import Callable, Sequence
from typing import Any

from .config import Config
from .errors import DownloaderError
from .utils import get_logger

_log = get_logger()

OUTPUT_TEMPLATE = "%(playlist_title|Single Videos)s/%(title)s.%(ext)s"
# Names files by the Panopto session id, so transcripts can carry provenance back to it.
OUTPUT_TEMPLATE_BY_ID = "%(playlist_title|Single Videos)s/%(id)s.%(ext)s"
PROBE_TEMPLATE = (
    "%(playlist_title|Single Videos)s\t%(title)s\t%(duration_string)s\t%(filesize_approx)s"
)

# A callable that runs an argument list and returns an object exposing ``returncode``.
Runner = Callable[..., "subprocess.CompletedProcess[Any]"]


def normalize_since(since: str | None) -> str | None:
    """Normalise a ``--since`` value to the ``YYYYMMDD`` form yt-dlp expects.

    Accepts ``YYYY-MM-DD`` and ``YYYYMMDD``; other values (e.g. yt-dlp's relative
    ``today-2weeks``) are passed through unchanged.
    """
    if not since:
        return None
    compact = since.replace("-", "")
    if len(compact) == 8 and compact.isdigit():
        return compact
    return since


def _auth_args(config: Config) -> list[str]:
    if config.cookies_file:
        return ["--cookies", config.cookies_file]
    if config.browser:
        return ["--cookies-from-browser", config.browser]
    return []


def build_command(urls: Sequence[str], config: Config, *, yt_dlp_path: str = "yt-dlp") -> list[str]:
    """Build the yt-dlp argument list to download ``urls`` according to ``config``."""
    cmd: list[str] = [
        yt_dlp_path,
        "--ignore-errors",
        "--no-overwrites",
        "--download-archive",
        str(config.archive),
        "--output",
        f"{config.out_dir}/{OUTPUT_TEMPLATE_BY_ID if config.id_filenames else OUTPUT_TEMPLATE}",
        "--restrict-filenames",
        "--concurrent-fragments",
        "4",
        "--retries",
        "10",
        "--newline",
    ]
    since = normalize_since(config.since)
    if since:
        cmd += ["--dateafter", since]
    cmd += _auth_args(config)
    if config.yt_dlp_args:
        cmd += shlex.split(config.yt_dlp_args)
    cmd += list(urls)
    return cmd


def build_probe_command(
    urls: Sequence[str], config: Config, *, yt_dlp_path: str = "yt-dlp"
) -> list[str]:
    """Build a yt-dlp argument list that reports titles/sizes without downloading."""
    cmd: list[str] = [
        yt_dlp_path,
        "--ignore-errors",
        "--skip-download",
        "--no-warnings",
        "--print",
        PROBE_TEMPLATE,
    ]
    since = normalize_since(config.since)
    if since:
        cmd += ["--dateafter", since]
    cmd += _auth_args(config)
    cmd += list(urls)
    return cmd


def _resolve_yt_dlp(yt_dlp_path: str | None) -> str:
    resolved = yt_dlp_path or shutil.which("yt-dlp")
    if not resolved:
        raise DownloaderError(
            "yt-dlp not found on PATH. Install it, e.g. 'pip install yt-dlp' or "
            "'brew install yt-dlp'. ffmpeg is also required."
        )
    return resolved


def download(
    urls: Sequence[str],
    config: Config,
    *,
    yt_dlp_path: str | None = None,
    runner: Runner = subprocess.run,
) -> int:
    """Download ``urls`` with yt-dlp and return its exit code.

    A non-zero exit code is normal when individual videos are skipped (locked or
    empty) because of ``--ignore-errors``; callers should treat it as a warning.

    Raises:
        DownloaderError: if yt-dlp is not installed.
    """
    resolved = _resolve_yt_dlp(yt_dlp_path)
    cmd = build_command(urls, config, yt_dlp_path=resolved)
    _log.info("Downloading %d URL(s) into %s/", len(urls), config.out_dir)
    _log.debug("yt-dlp command: %s", " ".join(shlex.quote(c) for c in cmd))
    return runner(cmd).returncode


def probe(
    urls: Sequence[str],
    config: Config,
    *,
    yt_dlp_path: str | None = None,
    runner: Runner = subprocess.run,
) -> int:
    """Report titles and approximate sizes for ``urls`` without downloading.

    Raises:
        DownloaderError: if yt-dlp is not installed.
    """
    resolved = _resolve_yt_dlp(yt_dlp_path)
    cmd = build_probe_command(urls, config, yt_dlp_path=resolved)
    _log.info("Dry run: resolving %d URL(s) (no download)…", len(urls))
    _log.debug("yt-dlp command: %s", " ".join(shlex.quote(c) for c in cmd))
    return runner(cmd).returncode
