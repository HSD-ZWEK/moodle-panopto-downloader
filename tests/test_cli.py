"""Tests for CLI orchestration with a fake Moodle client."""

from __future__ import annotations

from moodle_panopto_downloader import cli
from moodle_panopto_downloader.moodle import MoodleClient

HOST = "uni.cloud.panopto.eu"
V1 = f"https://{HOST}/Panopto/Pages/Viewer.aspx?id=11111111-1111-1111-1111-111111111111"
V2 = f"https://{HOST}/Panopto/Pages/Viewer.aspx?id=22222222-2222-2222-2222-222222222222"


class FakeClient(MoodleClient):
    """A MoodleClient whose network calls are replaced by canned data."""

    def __init__(self, contents):
        self._contents = contents
        self.functions = {"core_course_get_contents", "core_enrol_get_users_courses"}

    def site_info(self):
        return {"fullname": "T", "sitename": "S", "release": "5.1", "userid": 2}

    def get_course_contents(self, courseid):
        return self._contents.get(courseid, [])

    def get_user_courses(self, userid):
        return [{"id": cid} for cid in self._contents]


def test_scrape_courses_dedups_across_courses():
    client = FakeClient({1: [V1, V2], 2: [V2]})
    links = cli.scrape_courses(client, [1, 2], None, jobs=2)
    assert sorted(link.url for link in links) == sorted([V1, V2])


def test_run_list_mode_prints_urls(monkeypatch, capsys):
    monkeypatch.setattr(
        cli, "build_config", lambda args: cli.Config(base_url="https://m", token="t")
    )
    monkeypatch.setattr(cli, "MoodleClient", lambda *a, **k: FakeClient({210: [V1]}))

    args = cli.build_parser().parse_args(["210", "--list"])
    rc = cli.run(args)
    assert rc == 0
    assert capsys.readouterr().out.strip() == V1


def test_run_download_mode_invokes_downloader(monkeypatch):
    monkeypatch.setattr(
        cli, "build_config", lambda args: cli.Config(base_url="https://m", token="t")
    )
    monkeypatch.setattr(cli, "MoodleClient", lambda *a, **k: FakeClient({210: [V1]}))
    seen = {}

    def fake_download(urls, cfg):
        seen["urls"] = urls
        return 0

    monkeypatch.setattr(cli, "download", fake_download)

    rc = cli.run(cli.build_parser().parse_args(["210"]))
    assert rc == 0
    assert seen["urls"] == [V1]


def test_main_handles_config_error(monkeypatch):
    def boom(args):
        raise cli.MoodlePanoptoError("no token")

    monkeypatch.setattr(cli, "run", boom)
    assert cli.main(["210"]) == 1
