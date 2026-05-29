"""Tests for yt-dlp command construction and invocation."""

from __future__ import annotations

import pytest

from moodle_panopto_downloader.config import Config
from moodle_panopto_downloader.downloader import (
    build_command,
    build_probe_command,
    download,
    normalize_since,
)
from moodle_panopto_downloader.errors import DownloaderError


def _config(**kw) -> Config:
    return Config(base_url="https://m", token="t", **kw)


def test_command_contains_core_flags():
    cmd = build_command(["u1", "u2"], _config(out_dir="dl"), yt_dlp_path="yt-dlp")
    assert cmd[0] == "yt-dlp"
    assert "--download-archive" in cmd and "dl/.downloaded.txt" in cmd
    assert "--ignore-errors" in cmd
    assert cmd[-2:] == ["u1", "u2"]


def test_output_template_title_vs_id():
    out = cmd_output(build_command(["u"], _config()))
    assert "%(title)s" in out
    out_id = cmd_output(build_command(["u"], _config(id_filenames=True)))
    assert "%(id)s" in out_id and "%(title)s" not in out_id


def cmd_output(cmd):
    return cmd[cmd.index("--output") + 1]


def test_command_uses_browser_by_default():
    cmd = build_command(["u"], _config(browser="firefox"))
    assert "--cookies-from-browser" in cmd
    assert cmd[cmd.index("--cookies-from-browser") + 1] == "firefox"


def test_command_prefers_cookies_file_over_browser():
    cmd = build_command(["u"], _config(browser="firefox", cookies_file="c.txt"))
    assert "--cookies" in cmd and "--cookies-from-browser" not in cmd


def test_command_appends_extra_args():
    cmd = build_command(["u"], _config(yt_dlp_args="--limit-rate 2M"))
    assert "--limit-rate" in cmd and "2M" in cmd


def test_download_raises_without_yt_dlp(monkeypatch):
    monkeypatch.setattr("moodle_panopto_downloader.downloader.shutil.which", lambda _: None)
    with pytest.raises(DownloaderError):
        download(["u"], _config())


def test_download_returns_runner_exit_code():
    class _Result:
        returncode = 3

    calls = {}

    def fake_runner(cmd):
        calls["cmd"] = cmd
        return _Result()

    rc = download(["u"], _config(), yt_dlp_path="/usr/bin/yt-dlp", runner=fake_runner)
    assert rc == 3
    assert calls["cmd"][0] == "/usr/bin/yt-dlp"


def test_normalize_since():
    assert normalize_since("2024-01-15") == "20240115"
    assert normalize_since("20240115") == "20240115"
    assert normalize_since("today-2weeks") == "today-2weeks"  # passed through
    assert normalize_since(None) is None


def test_command_includes_dateafter_when_since_set():
    cmd = build_command(["u"], _config(since="2024-01-15"))
    assert "--dateafter" in cmd
    assert cmd[cmd.index("--dateafter") + 1] == "20240115"


def test_probe_command_does_not_download():
    cmd = build_probe_command(["u1", "u2"], _config(browser="firefox"), yt_dlp_path="yt-dlp")
    assert "--skip-download" in cmd
    assert "--print" in cmd
    assert "--download-archive" not in cmd
    assert "--output" not in cmd
    assert cmd[-2:] == ["u1", "u2"]
