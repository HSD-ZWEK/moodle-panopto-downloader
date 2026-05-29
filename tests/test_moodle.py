"""Tests for the Moodle client using a fake requests session."""

from __future__ import annotations

import pytest
import requests

from moodle_panopto_downloader.errors import MoodleAPIError, MoodleConnectionError
from moodle_panopto_downloader.moodle import MoodleClient


class FakeResponse:
    def __init__(self, json_data=None, exc=None):
        self._json = json_data
        self._exc = exc

    def raise_for_status(self):
        pass

    def json(self):
        if self._exc:
            raise self._exc
        return self._json


class FakeSession:
    def __init__(self, response=None, raises=None):
        self.response = response
        self.raises = raises
        self.last = None

    def post(self, url, data=None, timeout=None):
        self.last = {"url": url, "data": data, "timeout": timeout}
        if self.raises:
            raise self.raises
        return self.response


def _client(session) -> MoodleClient:
    return MoodleClient("https://m.example/", "secret-token", session=session)


def test_call_returns_payload_and_keeps_token_in_body():
    session = FakeSession(FakeResponse({"ok": True}))
    client = _client(session)
    assert client.call("core_webservice_get_site_info") == {"ok": True}
    assert session.last["data"]["wstoken"] == "secret-token"
    assert "secret-token" not in session.last["url"]  # token never in URL


def test_call_raises_on_exception_payload():
    payload = {"exception": "x", "errorcode": "invalidtoken", "message": "bad"}
    session = FakeSession(FakeResponse(payload))
    with pytest.raises(MoodleAPIError) as info:
        _client(session).call("core_course_get_contents", courseid=1)
    assert info.value.errorcode == "invalidtoken"


def test_call_wraps_transport_errors():
    session = FakeSession(raises=requests.RequestException("boom"))
    with pytest.raises(MoodleConnectionError):
        _client(session).call("core_webservice_get_site_info")


def test_call_wraps_non_json():
    session = FakeSession(FakeResponse(exc=ValueError("not json")))
    with pytest.raises(MoodleConnectionError):
        _client(session).call("core_webservice_get_site_info")


def test_site_info_caches_functions():
    payload = {"functions": [{"name": "core_course_get_contents"}, {"name": "other"}]}
    client = _client(FakeSession(FakeResponse(payload)))
    client.site_info()
    assert client.has("core_course_get_contents")
    assert not client.has("mod_lti_get_ltis_by_courses")


def test_has_assumes_available_when_unknown():
    client = _client(FakeSession(FakeResponse({})))
    assert client.has("anything")  # no functions cached yet
