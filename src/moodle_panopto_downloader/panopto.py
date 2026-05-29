# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Hochschule Düsseldorf – University of Applied Sciences
# ZWEK – Centre for Training and Competence Development
# Developed within the KIVi-Azubi research project
"""Pure functions for finding Panopto links inside arbitrary Moodle API data.

This module is deliberately free of any network or I/O code so that link
extraction can be unit-tested in isolation. It recognises the common Panopto
URL shapes and rebuilds them canonically, capturing the host so the result works
for any institution (``*.cloud.panopto.eu`` or self-hosted).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

# A Panopto session/folder id is a standard UUID.
_UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"

# Full URLs (host captured). Query-parameter order is irrelevant thanks to the
# non-greedy prefix, so links survive Panopto query-string changes.
RE_VIEWER_URL = re.compile(
    rf"https?://([^/\s\"'<>]+)/Panopto/Pages/(?:Viewer|Embed)\.aspx\?[^\s\"'<>]*?\b(?:id|pid)=({_UUID})",
    re.IGNORECASE,
)
RE_FOLDER_URL = re.compile(
    rf"https?://([^/\s\"'<>]+)/Panopto/Pages/Sessions/List\.aspx\?[^\s\"'<>]*?folderID=({_UUID})",
    re.IGNORECASE,
)
# Bare references (no scheme/host) — only usable with a known fallback host.
RE_VIEWER_BARE = re.compile(rf"(?:Viewer|Embed)\.aspx\?(?:id|pid)=({_UUID})", re.IGNORECASE)
RE_FOLDER_BARE = re.compile(rf"folderID=({_UUID})", re.IGNORECASE)
# Any Panopto host, used as a fallback source for the host of bare references.
RE_ANY_HOST = re.compile(r"https?://([a-z0-9.-]*panopto[a-z0-9.-]*)", re.IGNORECASE)

VIDEO = "video"
FOLDER = "folder"


@dataclass(frozen=True)
class PanoptoLink:
    """A single discovered Panopto resource."""

    kind: str  # VIDEO or FOLDER
    id: str
    host: str

    @property
    def url(self) -> str:
        """Canonical Panopto URL for this resource."""
        if self.kind == FOLDER:
            return f"https://{self.host}/Panopto/Pages/Sessions/List.aspx?folderID={self.id}"
        return f"https://{self.host}/Panopto/Pages/Viewer.aspx?id={self.id}"


def iter_strings(obj: Any) -> Iterator[str]:
    """Yield every string contained in a nested dict/list/str structure."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from iter_strings(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            yield from iter_strings(value)


def detect_hosts(data: Any) -> set[str]:
    """Return the set of Panopto hosts referenced anywhere in ``data``."""
    hosts: set[str] = set()
    for text in iter_strings(data):
        hosts.update(h.lower() for h in RE_ANY_HOST.findall(text))
    return hosts


def extract_links(data: Any, host_fallback: str | None = None) -> list[PanoptoLink]:
    """Extract all Panopto links from a Moodle API response structure.

    Full URLs (with host) are preferred. Bare ``Viewer.aspx?id=…`` /
    ``folderID=…`` references are only resolved if a host is known — either from
    ``host_fallback`` or from any full Panopto URL found in the same data.

    The result is de-duplicated by ``(kind, id)`` and returned in a stable,
    deterministic order (videos first, then folders, each sorted by id).
    """
    found: dict[tuple[str, str], PanoptoLink] = {}

    # Pass 1: fully-qualified URLs (most reliable; carry their own host).
    for text in iter_strings(data):
        for host, vid in RE_VIEWER_URL.findall(text):
            found.setdefault((VIDEO, vid.lower()), PanoptoLink(VIDEO, vid.lower(), host.lower()))
        for host, fid in RE_FOLDER_URL.findall(text):
            found.setdefault((FOLDER, fid.lower()), PanoptoLink(FOLDER, fid.lower(), host.lower()))

    # Pass 2: bare references, attached to a known host.
    host = host_fallback or _pick_host(detect_hosts(data))
    if host:
        for text in iter_strings(data):
            for vid in RE_VIEWER_BARE.findall(text):
                found.setdefault((VIDEO, vid.lower()), PanoptoLink(VIDEO, vid.lower(), host))
            for fid in RE_FOLDER_BARE.findall(text):
                found.setdefault((FOLDER, fid.lower()), PanoptoLink(FOLDER, fid.lower(), host))

    return sorted(found.values(), key=lambda link: (link.kind != VIDEO, link.id))


def _pick_host(hosts: set[str]) -> str | None:
    """Deterministically pick one host from a set (first when sorted)."""
    return sorted(hosts)[0] if hosts else None
