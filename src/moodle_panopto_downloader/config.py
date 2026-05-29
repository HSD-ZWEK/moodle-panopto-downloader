# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Hochschule Düsseldorf – University of Applied Sciences
# ZWEK – Centre for Training and Competence Development
# Developed within the KIVi-Azubi research project
"""Runtime configuration: resolution from CLI flags, environment and ini file.

Resolution order for every setting is **CLI flag → environment variable →
config file → built-in default**. The functions here are pure with respect to
the environment (the environment mapping and existence check are injectable),
which keeps them unit-testable without touching the real filesystem or process
environment.
"""

from __future__ import annotations

import configparser
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigError
from .utils import default_browser

DEFAULT_CONFIG_PATHS = (
    "mpdl.ini",
    os.path.expanduser("~/.config/moodle-panopto-downloader/config.ini"),
)
DEFAULT_TOKEN_FILES = (
    ".moodle_token",
    os.path.expanduser("~/.config/moodle-panopto-downloader/token"),
)


@dataclass
class Config:
    """Fully resolved configuration for a run."""

    base_url: str
    token: str
    out_dir: str = "downloads"
    browser: str | None = None
    cookies_file: str | None = None
    panopto_host: str | None = None
    archive: str | None = None
    yt_dlp_args: str | None = None
    jobs: int = 4
    since: str | None = None

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        if self.browser is None and not self.cookies_file:
            self.browser = default_browser()
        if self.archive is None:
            self.archive = os.path.join(self.out_dir, ".downloaded.txt")


def load_ini(
    path: str | None,
    *,
    exists: Callable[[str], bool] = os.path.exists,
    read_text: Callable[[str], str] | None = None,
) -> dict[str, str]:
    """Load a flat key/value mapping from an ini file.

    Searches ``DEFAULT_CONFIG_PATHS`` when ``path`` is ``None``. All sections are
    flattened into one mapping (keys are unique across our schema).
    """
    candidates = [path] if path else list(DEFAULT_CONFIG_PATHS)
    for candidate in candidates:
        if candidate and exists(candidate):
            parser = configparser.ConfigParser()
            if read_text is not None:
                parser.read_string(read_text(candidate))
            else:
                parser.read(candidate)
            merged: dict[str, str] = {}
            for section in parser.sections():
                merged.update(parser.items(section))
            return merged
    return {}


def resolve_token(
    *,
    cli_token: str | None,
    token_file: str | None,
    env: Mapping[str, str],
    ini: Mapping[str, str],
    token_files: tuple[str, ...] = DEFAULT_TOKEN_FILES,
    exists: Callable[[str], bool] = os.path.exists,
) -> str:
    """Resolve the Moodle token from the available sources, or raise ConfigError."""
    if cli_token:
        return cli_token.strip()
    if token_file:
        return Path(token_file).read_text(encoding="utf-8").strip()
    if env.get("MOODLE_TOKEN"):
        return env["MOODLE_TOKEN"].strip()
    if ini.get("token"):
        return ini["token"].strip()
    for candidate in token_files:
        if exists(candidate):
            return Path(candidate).read_text(encoding="utf-8").strip()
    raise ConfigError(
        "No Moodle token found. Provide --token, --token-file, the MOODLE_TOKEN "
        "environment variable, or set 'token' in the config file."
    )


def resolve_base_url(
    *, cli_base_url: str | None, env: Mapping[str, str], ini: Mapping[str, str]
) -> str:
    """Resolve the Moodle base URL, or raise ConfigError."""
    url = cli_base_url or env.get("MOODLE_URL") or ini.get("base_url")
    if not url:
        raise ConfigError(
            "No Moodle base URL. Provide --base-url, the MOODLE_URL environment "
            "variable, or set 'base_url' in the config file."
        )
    return url


def build_config(args: object, env: Mapping[str, str] | None = None) -> Config:
    """Build a :class:`Config` from parsed CLI args and the environment."""
    env = os.environ if env is None else env
    ini = load_ini(getattr(args, "config", None))

    def pick(attr: str, ini_key: str, default: str | None = None) -> str | None:
        value = getattr(args, attr, None)
        if value is not None:
            return str(value)
        return ini.get(ini_key, default)

    jobs_value = pick("jobs", "jobs")
    jobs = int(jobs_value) if jobs_value is not None else 4

    base_url = resolve_base_url(cli_base_url=getattr(args, "base_url", None), env=env, ini=ini)
    token = resolve_token(
        cli_token=getattr(args, "token", None),
        token_file=getattr(args, "token_file", None),
        env=env,
        ini=ini,
    )
    return Config(
        base_url=base_url,
        token=token,
        out_dir=pick("out", "out", "downloads") or "downloads",
        browser=pick("browser", "browser"),
        cookies_file=pick("cookies_file", "cookies_file"),
        panopto_host=pick("panopto_host", "panopto_host"),
        archive=pick("archive", "archive"),
        yt_dlp_args=pick("yt_dlp_args", "yt_dlp_args"),
        jobs=jobs,
        since=pick("since", "since"),
    )
