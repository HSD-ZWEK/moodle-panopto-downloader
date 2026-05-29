"""Integration tests driving the client against mocked Web Services responses.

The fixtures in ``tests/fixtures`` mirror the shape of real Moodle API responses
(``core_course_get_contents``, ``mod_lti_get_ltis_by_courses``,
``core_webservice_get_site_info``).
"""

from __future__ import annotations

import json
from pathlib import Path

from moodle_panopto_downloader import cli
from moodle_panopto_downloader.moodle import MoodleClient

FIXTURES = Path(__file__).parent / "fixtures"
HOST = "demo.cloud.panopto.eu"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FixtureResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FixtureSession:
    """Routes Web Services calls to fixture files based on the wsfunction."""

    ROUTES = {
        "core_webservice_get_site_info": "site_info.json",
        "core_course_get_contents": "course_contents.json",
        "mod_lti_get_ltis_by_courses": "course_ltis.json",
    }

    def post(self, url, data=None, timeout=None):
        fixture = self.ROUTES[data["wsfunction"]]
        return FixtureResponse(_load(fixture))


def _client() -> MoodleClient:
    return MoodleClient("https://moodle.example.edu", "token", session=FixtureSession())


def test_scrape_course_finds_all_panopto_forms():
    client = _client()
    client.site_info()  # populate available functions
    links = cli.scrape_course(client, 210, host_fallback=None)
    urls = {link.url for link in links}
    assert urls == {
        f"https://{HOST}/Panopto/Pages/Viewer.aspx?id=11111111-1111-1111-1111-111111111111",
        f"https://{HOST}/Panopto/Pages/Sessions/List.aspx?folderID=22222222-2222-2222-2222-222222222222",
        f"https://{HOST}/Panopto/Pages/Viewer.aspx?id=33333333-3333-3333-3333-333333333333",
        f"https://{HOST}/Panopto/Pages/Sessions/List.aspx?folderID=44444444-4444-4444-4444-444444444444",
    }


def test_non_panopto_resources_are_ignored():
    client = _client()
    client.site_info()
    links = cli.scrape_course(client, 210, host_fallback=None)
    # The PDF resource and pluginfile URL must not appear.
    assert all("panopto" in link.host for link in links)


def test_run_json_output(monkeypatch, capsys):
    monkeypatch.setattr(
        cli, "build_config", lambda args: cli.Config(base_url="https://m", token="t")
    )
    monkeypatch.setattr(cli, "MoodleClient", lambda *a, **k: _client())

    rc = cli.run(cli.build_parser().parse_args(["210", "--json"]))
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 4
    assert {entry["kind"] for entry in payload} == {"video", "folder"}
    assert all(entry["url"].startswith("https://") for entry in payload)
