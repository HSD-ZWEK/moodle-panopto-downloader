# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Hochschule Düsseldorf – University of Applied Sciences
# ZWEK – Centre for Training and Competence Development
# Developed within the KIVi-Azubi research project
"""Derive a German domain vocabulary from a Moodle course's contents.

The vocabulary is harvested from the text the Web Services API returns
(``core_course_get_contents``): section and activity names, labels, page content,
section summaries, resource and link names — and, optionally, the text of attached
PDF/text files. Terms are matched case-insensitively (so lower-case technical adjectives
such as ``isotherm``/``isobar`` are captured), ranked by frequency, with German function
words and Moodle scaffolding removed. The result feeds ``whisper-transcribe-de --vocab``.

:func:`extract_terms`, :func:`iter_file_urls` and :func:`text_from_file` are pure with
respect to the network (no I/O); downloading files is done by the caller.
"""

from __future__ import annotations

import html
import re
from collections import Counter
from collections.abc import Iterable
from typing import Any

from .panopto import iter_strings

_RE_TAG = re.compile(r"<[^>]+>")
_RE_URL = re.compile(r"https?://\S+|www\.\S+")
# Any German word, >= 4 letters (case-insensitive: nouns, adjectives, terms).
_RE_WORD = re.compile(r"\b[A-Za-zÄÖÜäöüß]{4,}\b")

# Moodle/quiz scaffolding and Panopto/plumbing words.
_SCAFFOLD = {
    "aufgabe",
    "aufgaben",
    "frage",
    "fragen",
    "quiz",
    "test",
    "tests",
    "material",
    "materialien",
    "datei",
    "dateien",
    "abschnitt",
    "thema",
    "themen",
    "kurs",
    "kurse",
    "lernpaket",
    "lerneinheit",
    "video",
    "videos",
    "ordner",
    "link",
    "links",
    "seite",
    "seiten",
    "inhalt",
    "inhalte",
    "übung",
    "übungen",
    "lösung",
    "lösungen",
    "beispiel",
    "beispiele",
    "hinweis",
    "hinweise",
    "einführung",
    "überblick",
    "zusammenfassung",
    "bitte",
    "achtung",
    "tipp",
    "tipps",
    "klausur",
    "probeklausur",
    "semester",
    "punkte",
    "wikimedia",
    "commons",
    "quelle",
    "autor",
    "gecheckt",
    "ausprobieren",
    "tricks",
    "eingeben",
    "vorwissen",
    "einstieg",
    "panopto",
    "sessions",
    "pages",
    "viewer",
    "embed",
    "download",
    "online",
    "urls",
    "medienfeld",
    "selbsttest",
    "unterabschnitt",
    "unterabschnitte",
    "erklärung",
    "erklärungen",
    "bestehensgrenze",
    "bestehen",
    "text",
    "panik",
    "geöffnet",
    "geschlossen",
    "lernvideos",
    "literatur",
    "bibliothek",
    "verzeichnisse",
    "direktlink",
    "bonuspunkte",
    "relevant",
    # HTML/CSS/file-format tokens that survive in page or file text.
    "content",
    "application",
    "display",
    "true",
    "false",
    "file",
    "files",
    "filtericon",
    "version",
    "style",
    "class",
    "href",
    "span",
    "html",
    "http",
    "https",
    "www",
    "folie",
    "folien",
    "slide",
    "none",
    "block",
    "width",
    "height",
    # English title-page / affiliation boilerplate.
    "prof",
    "university",
    "applied",
    "sciences",
    "hochschule",
    "fachhochschule",
}

# Common German function words and generic content words (not domain terminology).
_GERMAN_STOP = {
    "aber",
    "alle",
    "allem",
    "allen",
    "aller",
    "alles",
    "als",
    "also",
    "andere",
    "anderen",
    "auch",
    "auf",
    "aus",
    "bei",
    "beide",
    "beiden",
    "bereits",
    "besonders",
    "bzw",
    "dabei",
    "dadurch",
    "dafür",
    "daher",
    "damit",
    "danach",
    "dann",
    "daran",
    "darauf",
    "daraus",
    "darin",
    "darüber",
    "darum",
    "dass",
    "davon",
    "dazu",
    "dein",
    "denn",
    "der",
    "deren",
    "des",
    "deshalb",
    "dessen",
    "deswegen",
    "dich",
    "die",
    "dies",
    "diese",
    "diesem",
    "diesen",
    "dieser",
    "dieses",
    "doch",
    "dort",
    "durch",
    "eben",
    "ebenfalls",
    "ebenso",
    "ein",
    "eine",
    "einem",
    "einen",
    "einer",
    "eines",
    "einige",
    "einigen",
    "einiger",
    "entsprechend",
    "entsprechende",
    "entsprechenden",
    "etwa",
    "etwas",
    "folgende",
    "folgenden",
    "folgendes",
    "für",
    "ganz",
    "ganze",
    "ganzen",
    "geben",
    "gegeben",
    "gegen",
    "genau",
    "gerade",
    "gibt",
    "groß",
    "große",
    "großen",
    "gut",
    "gute",
    "guten",
    "haben",
    "hast",
    "hatte",
    "hatten",
    "heißt",
    "hier",
    "hierbei",
    "hoch",
    "hohe",
    "ihm",
    "ihn",
    "ihnen",
    "ihr",
    "ihre",
    "ihrem",
    "ihren",
    "ihrer",
    "immer",
    "indem",
    "innerhalb",
    "insbesondere",
    "ist",
    "jede",
    "jedem",
    "jeden",
    "jeder",
    "jedes",
    "jedoch",
    "jeweils",
    "jeweilige",
    "jeweiligen",
    "kann",
    "kein",
    "keine",
    "keinen",
    "können",
    "könnte",
    "lassen",
    "machen",
    "man",
    "mehr",
    "mein",
    "meist",
    "meistens",
    "mit",
    "möchte",
    "möglich",
    "mögliche",
    "möglichen",
    "muss",
    "müssen",
    "nach",
    "nachdem",
    "neben",
    "nicht",
    "nichts",
    "noch",
    "nun",
    "nur",
    "oben",
    "ober",
    "obwohl",
    "oder",
    "ohne",
    "schon",
    "sehr",
    "sein",
    "seine",
    "seinen",
    "seiner",
    "selbst",
    "sich",
    "sind",
    "soll",
    "sollen",
    "sollte",
    "somit",
    "sondern",
    "sonst",
    "sowie",
    "sowohl",
    "über",
    "überhaupt",
    "übrigens",
    "und",
    "uns",
    "unser",
    "unter",
    "unterschiedliche",
    "verschiedene",
    "verschiedenen",
    "viel",
    "viele",
    "vielen",
    "vom",
    "von",
    "vor",
    "während",
    "war",
    "waren",
    "warum",
    "was",
    "weil",
    "weiter",
    "weitere",
    "weiteren",
    "welche",
    "welchem",
    "welchen",
    "welcher",
    "welches",
    "wenig",
    "wenige",
    "weniger",
    "wenn",
    "werden",
    "wie",
    "wieder",
    "wird",
    "wirklich",
    "wirst",
    "wobei",
    "wodurch",
    "wollen",
    "wollte",
    "worden",
    "wurde",
    "wurden",
    "würde",
    "würden",
    "zeigen",
    "zeigt",
    "zudem",
    "zum",
    "zur",
    "zusammen",
    "zwar",
    "zwischen",
}

# German number words (cardinals/ordinals, >= 4 letters) — not domain terminology.
_NUMBER_WORDS = {
    "null",
    "eins",
    "zwei",
    "drei",
    "vier",
    "fünf",
    "sechs",
    "sieben",
    "acht",
    "neun",
    "zehn",
    "zwölf",
    "dreizehn",
    "vierzehn",
    "fünfzehn",
    "sechzehn",
    "siebzehn",
    "achtzehn",
    "neunzehn",
    "zwanzig",
    "dreißig",
    "vierzig",
    "fünfzig",
    "sechzig",
    "siebzig",
    "achtzig",
    "neunzig",
    "hundert",
    "tausend",
    "million",
    "millionen",
    "milliarde",
    "milliarden",
    "erste",
    "erster",
    "ersten",
    "erstes",
    "zweite",
    "zweiter",
    "zweiten",
    "zweites",
    "dritte",
    "dritter",
    "dritten",
    "drittes",
    "vierte",
    "vierten",
    "fünfte",
    "fünften",
    "sechste",
    "siebte",
    "achte",
    "neunte",
    "zehnte",
    "beiden",
    "drittel",
    "viertel",
}

_STOP_FOLDED = {w.casefold() for w in _SCAFFOLD | _GERMAN_STOP | _NUMBER_WORDS}

# File types worth reading for vocabulary (others are skipped).
TEXT_SUFFIXES = (".pdf", ".txt", ".md", ".csv", ".html", ".htm")


def extract_terms(
    data: Any,
    extra_texts: Iterable[str] | None = None,
    *,
    max_terms: int = 250,
    min_count: int = 1,
) -> list[str]:
    """Return candidate domain terms from a course-contents structure (+ extra texts).

    Words are matched case-insensitively and counts merged across cases; the most
    frequent surface form is kept (so a noun stays capitalised, an adjective stays
    lower-case). German function words and Moodle scaffolding are removed. ``max_terms``
    caps the list; ``min_count`` drops rare one-offs when raised.
    """
    fold_counts: Counter[str] = Counter()
    surfaces: dict[str, Counter[str]] = {}
    streams: Iterable[str] = iter_strings(data)
    if extra_texts is not None:
        streams = (*streams, *extra_texts)
    for text in streams:
        cleaned = html.unescape(_RE_TAG.sub(" ", _RE_URL.sub(" ", text)))
        for word in _RE_WORD.findall(cleaned):
            fold = word.casefold()
            if fold in _STOP_FOLDED:
                continue
            fold_counts[fold] += 1
            surfaces.setdefault(fold, Counter())[word] += 1
    ranked = [fold for fold, count in fold_counts.most_common() if count >= min_count]
    terms = [surfaces[fold].most_common(1)[0][0] for fold in ranked]
    return terms[:max_terms]


def iter_file_urls(data: Any) -> list[tuple[str, str]]:
    """Return ``(fileurl, filename)`` for readable file resources in course contents."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for section in data if isinstance(data, list) else []:
        for module in section.get("modules", []):
            for content in module.get("contents", []) or []:
                url = content.get("fileurl")
                name = content.get("filename") or ""
                if url and url not in seen and name.lower().endswith(TEXT_SUFFIXES):
                    seen.add(url)
                    found.append((url, name))
    return found


def text_from_file(filename: str, data: bytes) -> str:
    """Extract plain text from a downloaded file (PDF via pypdf; text/HTML decoded)."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        import io

        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    text = data.decode("utf-8", errors="replace")
    if lower.endswith((".html", ".htm")):
        text = _RE_TAG.sub(" ", text)
    return text


_RE_CDATA = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.DOTALL)
_RE_TEXT_NODE = re.compile(r"<text>(.*?)</text>", re.DOTALL | re.IGNORECASE)


def text_from_question_xml(xml: str) -> str:
    """Extract the human-readable text from a Moodle question XML (all ``<text>`` nodes)."""
    parts: list[str] = []
    for node in _RE_TEXT_NODE.findall(xml):
        node = _RE_CDATA.sub(r"\1", node)
        parts.append(_RE_TAG.sub(" ", html.unescape(node)))
    return "\n".join(parts)


def iter_question_entry_ids(data: Any) -> list[str]:
    """Collect, in order and de-duplicated, all ``questionbankentryid`` values in ``data``."""
    ids: list[str] = []
    seen: set[str] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "questionbankentryid" and isinstance(value, (str, int)):
                    sid = str(value)
                    if sid not in seen:
                        seen.add(sid)
                        ids.append(sid)
                else:
                    walk(value)
        elif isinstance(obj, (list, tuple)):
            for value in obj:
                walk(value)

    walk(data)
    return ids


def render_vocab_file(terms: list[str], courses: list[int]) -> str:
    """Render the vocabulary file content (header + one term per line)."""
    ids = ", ".join(str(c) for c in courses)
    header = (
        f"# Domain vocabulary derived from Moodle course(s) {ids} via the Web Services API.\n"
        "# One term per line; '#' comments and blank lines are ignored. Review and trim.\n"
        "# Use with: whisper-transcribe-de <inputs> --vocab <this-file>\n"
    )
    return header + "\n".join(terms) + "\n"
