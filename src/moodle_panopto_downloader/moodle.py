# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Hochschule Düsseldorf – University of Applied Sciences
# ZWEK – Centre for Training and Competence Development
# Developed within the KIVi-Azubi research project
"""A thin client for the Moodle Web Services REST API.

The client is intentionally small and defensive:

- A single :class:`requests.Session` is reused for connection pooling.
- The token is always sent in the POST body, never in the URL/query string, so
  it does not leak into server access logs.
- The set of available functions (reported by ``core_webservice_get_site_info``)
  is cached and used to skip calls a given token/server cannot serve — this is
  what makes the tool resilient across Moodle versions.
"""

from __future__ import annotations

import re
from typing import Any

import requests

from .errors import MoodleAPIError, MoodleConnectionError
from .utils import get_logger

# qbank_gitsync echoes its version in a version-mismatch error message.
_GITSYNC_VERSION_RE = re.compile(r"installed in Moodle \(([^)]+)\)")

_log = get_logger()


class MoodleClient:
    """Minimal Moodle Web Services client (REST, JSON)."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: int = 60,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/webservice/rest/server.php"
        self._token = token
        self.timeout = timeout
        self._session = session or requests.Session()
        self.functions: set[str] = set()

    def call(self, wsfunction: str, **params: Any) -> Any:
        """Call a web service function and return the decoded JSON.

        Raises:
            MoodleConnectionError: on transport/protocol failures.
            MoodleAPIError: when Moodle returns an exception payload.
        """
        data = {
            "wstoken": self._token,
            "wsfunction": wsfunction,
            "moodlewsrestformat": "json",
            **params,
        }
        _log.debug("WS call: %s params=%s", wsfunction, sorted(params))
        try:
            response = self._session.post(self.endpoint, data=data, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise MoodleConnectionError(f"Request to Moodle failed: {exc}") from exc
        except ValueError as exc:  # JSON decode error
            raise MoodleConnectionError(
                f"Moodle returned a non-JSON response for {wsfunction}."
            ) from exc

        if isinstance(payload, dict) and payload.get("exception"):
            raise MoodleAPIError(wsfunction, payload.get("errorcode"), payload.get("message", ""))
        return payload

    # -- convenience wrappers ------------------------------------------------
    def site_info(self) -> dict[str, Any]:
        """Verify the token and cache the available function names."""
        info: dict[str, Any] = self.call("core_webservice_get_site_info")
        self.functions = {f["name"] for f in info.get("functions", [])}
        return info

    def has(self, function: str) -> bool:
        """Whether the token/server exposes ``function``.

        If the function list is unknown (some servers omit it), assume available
        and let the actual call fail gracefully instead.
        """
        return not self.functions or function in self.functions

    def get_course_contents(self, courseid: int) -> Any:
        """Return the full content tree of a course."""
        return self.call("core_course_get_contents", courseid=courseid)

    def get_user_courses(self, userid: int) -> list[dict[str, Any]]:
        """Return the courses a user is enrolled in."""
        courses: list[dict[str, Any]] = self.call("core_enrol_get_users_courses", userid=userid)
        return courses

    def get_course_ltis(self, courseid: int) -> Any:
        """Return LTI (external tool) instances of a course."""
        return self.call("mod_lti_get_ltis_by_courses", **{"courseids[0]": courseid})

    def fetch_file(self, fileurl: str) -> bytes:
        """Download a course file via its token-authenticated pluginfile URL."""
        sep = "&" if "?" in fileurl else "?"
        url = f"{fileurl}{sep}token={self._token}"
        try:
            response = self._session.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise MoodleConnectionError(f"File download failed: {exc}") from exc
        return response.content

    # -- qbank_gitsync question export (optional plugin) ---------------------
    def supports_gitsync(self) -> bool:
        """Whether the token can list and export questions via qbank_gitsync."""
        return self.has("qbank_gitsync_get_question_list") and self.has(
            "qbank_gitsync_export_question"
        )

    def gitsync_server_version(self) -> str | None:
        """Detect the server's qbank_gitsync version.

        qbank_gitsync requires the caller to send a matching ``localversion``. A
        deliberate mismatch makes it echo its own version in the error message, which we
        parse — so no hard-coded version is needed.
        """
        try:
            self.call(
                "qbank_gitsync_get_question_list",
                localversion="0",
                contextlevel="50",
                instanceid="0",
                qcategoryname="top",
                coursename="",
                modulename="",
                coursecategory="",
                qcategoryid="",
                contextonly=1,
                ignorecat="",
                **{"qbankentryids[0]": ""},
            )
        except MoodleAPIError as exc:
            match = _GITSYNC_VERSION_RE.search(str(exc))
            return match.group(1) if match else None
        return None

    def get_question_list(self, cmid: int, version: str, modulename: str = "") -> Any:
        """List questions of a module's question bank (context level 70)."""
        return self.call(
            "qbank_gitsync_get_question_list",
            contextlevel="70",
            instanceid=str(cmid),
            localversion=version,
            qcategoryname="top",
            coursename="",
            modulename=modulename,
            coursecategory="",
            qcategoryid="",
            contextonly=0,
            ignorecat="",
            **{"qbankentryids[0]": ""},
        )

    def export_question(self, questionbankentryid: str) -> Any:
        """Export one question (Moodle XML, including its text)."""
        return self.call(
            "qbank_gitsync_export_question",
            questionbankentryid=str(questionbankentryid),
            includecategory=0,
        )
