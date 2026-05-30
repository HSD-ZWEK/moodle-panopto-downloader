# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Hochschule Düsseldorf – University of Applied Sciences
# ZWEK – Centre for Training and Competence Development
# Developed within the KIVi-Azubi research project
"""Derive a German domain vocabulary from a Moodle course's contents.

The vocabulary is harvested from the text the Web Services API already returns
(``core_course_get_contents``): section and activity names, labels, page content,
section summaries, resource and link names. Capitalised German terms are ranked by
frequency, with generic scaffolding words removed. The result feeds the ``--vocab``
option of whisper-transcribe-de, so transcription is biased towards the terminology
of the very course being processed.

This is pure with respect to the network: :func:`extract_terms` works on the decoded
API structure and contains no I/O.
"""

from __future__ import annotations

import html
import re
from collections import Counter
from typing import Any

from .panopto import iter_strings

_RE_TAG = re.compile(r"<[^>]+>")
_RE_URL = re.compile(r"https?://\S+|www\.\S+")
# Capitalised German word, >= 4 letters (nouns and proper terms).
_RE_WORD = re.compile(r"\b[A-ZÄÖÜ][A-Za-zÄÖÜäöüß]{3,}\b")

# Generic words to drop: German function words (capitalised at sentence start),
# Moodle/quiz scaffolding, and common filler. Domain terms are kept.
_STOP = {
    "Aufgabe",
    "Aufgaben",
    "Frage",
    "Fragen",
    "Quiz",
    "Test",
    "Tests",
    "Material",
    "Materialien",
    "Datei",
    "Dateien",
    "Abschnitt",
    "Thema",
    "Themen",
    "Kurs",
    "Kurse",
    "Lernpaket",
    "Lerneinheit",
    "Video",
    "Videos",
    "Ordner",
    "Link",
    "Links",
    "Seite",
    "Seiten",
    "Inhalt",
    "Inhalte",
    "Übung",
    "Übungen",
    "Lösung",
    "Lösungen",
    "Beispiel",
    "Beispiele",
    "Hinweis",
    "Hinweise",
    "Einführung",
    "Überblick",
    "Zusammenfassung",
    "Hier",
    "Diese",
    "Dieser",
    "Dieses",
    "Damit",
    "Dabei",
    "Außerdem",
    "Somit",
    "Also",
    "Wenn",
    "Dann",
    "Weil",
    "Sodass",
    "Welche",
    "Welcher",
    "Welches",
    "Warum",
    "Wann",
    "Bitte",
    "Achtung",
    "Tipp",
    "Tipps",
    "Klausur",
    "Probeklausur",
    "Semester",
    "Punkte",
    "Eine",
    "Einen",
    "Eines",
    "Einem",
    "Einer",
    "Wikimedia",
    "Commons",
    "Quelle",
    "Autor",
    "Gecheckt",
    "Ausprobieren",
    "Tricks",
    "Eingeben",
    "Vorwissen",
    "Gefühl",
    "Einstieg",
    # Panopto / Moodle plumbing that may survive URL stripping.
    "Panopto",
    "Sessions",
    "Pages",
    "Viewer",
    "Embed",
    "Download",
    "Online",
    "URLs",
    "Medienfeld",
    "Selbsttest",
    "Unterabschnitt",
    "Unterabschnitte",
    "Erklärung",
    "Erklärungen",
    "Bestehensgrenze",
    "Bestehen",
    "Text",
    "Keine",
    "Panik",
    "Geöffnet",
    "Geschlossen",
}


def extract_terms(data: Any, max_terms: int = 200, min_count: int = 1) -> list[str]:
    """Return candidate domain terms from a ``core_course_get_contents`` structure.

    Terms are capitalised German words ranked by frequency (descending), with generic
    scaffolding words removed. ``max_terms`` caps the list; ``min_count`` drops rare
    one-offs when raised.
    """
    counts: Counter[str] = Counter()
    for text in iter_strings(data):
        cleaned = html.unescape(_RE_TAG.sub(" ", _RE_URL.sub(" ", text)))
        for word in _RE_WORD.findall(cleaned):
            if word not in _STOP:
                counts[word] += 1
    ranked = [w for w, c in counts.most_common() if c >= min_count]
    return ranked[:max_terms]


def render_vocab_file(terms: list[str], courses: list[int]) -> str:
    """Render the vocabulary file content (header + one term per line)."""
    ids = ", ".join(str(c) for c in courses)
    header = (
        f"# Domain vocabulary derived from Moodle course(s) {ids} via the Web Services API.\n"
        "# One term per line; '#' comments and blank lines are ignored. Review and trim.\n"
        "# Use with: whisper-transcribe-de <inputs> --vocab <this-file>\n"
    )
    return header + "\n".join(terms) + "\n"
