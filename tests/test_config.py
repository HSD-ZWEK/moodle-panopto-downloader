"""Tests for configuration resolution."""

from __future__ import annotations

import pytest

from moodle_panopto_downloader.config import Config, resolve_base_url, resolve_token
from moodle_panopto_downloader.errors import ConfigError


def test_token_precedence_cli_over_env_and_ini():
    token = resolve_token(
        cli_token="cli",
        token_file=None,
        env={"MOODLE_TOKEN": "env"},
        ini={"token": "ini"},
    )
    assert token == "cli"


def test_token_from_env_then_ini():
    assert (
        resolve_token(
            cli_token=None, token_file=None, env={"MOODLE_TOKEN": "env"}, ini={"token": "ini"}
        )
        == "env"
    )
    assert resolve_token(cli_token=None, token_file=None, env={}, ini={"token": "ini"}) == "ini"


def test_token_from_file(tmp_path):
    path = tmp_path / "tok"
    path.write_text("filetoken\n")
    assert resolve_token(cli_token=None, token_file=str(path), env={}, ini={}) == "filetoken"


def test_token_from_default_file(tmp_path):
    path = tmp_path / ".moodle_token"
    path.write_text("defaulttoken\n")
    token = resolve_token(
        cli_token=None,
        token_file=None,
        env={},
        ini={},
        token_files=(str(path),),
    )
    assert token == "defaulttoken"


def test_token_missing_raises():
    with pytest.raises(ConfigError):
        resolve_token(cli_token=None, token_file=None, env={}, ini={}, token_files=())


def test_base_url_precedence_and_missing():
    assert (
        resolve_base_url(cli_base_url="https://a", env={"MOODLE_URL": "https://b"}, ini={})
        == "https://a"
    )
    assert (
        resolve_base_url(cli_base_url=None, env={"MOODLE_URL": "https://b"}, ini={}) == "https://b"
    )
    with pytest.raises(ConfigError):
        resolve_base_url(cli_base_url=None, env={}, ini={})


def test_config_post_init_defaults():
    cfg = Config(base_url="https://m.example/", token="t")
    assert cfg.base_url == "https://m.example"  # trailing slash stripped
    assert cfg.archive == "downloads/.downloaded.txt"  # derived from out_dir
    assert cfg.browser is not None  # platform default filled in


def test_config_browser_not_set_when_cookies_file_given():
    cfg = Config(base_url="https://m", token="t", cookies_file="c.txt")
    assert cfg.browser is None
