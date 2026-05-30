"""Tests for deriving a domain vocabulary from Moodle course contents."""

from __future__ import annotations

from moodle_panopto_downloader.vocab import extract_terms, render_vocab_file


def test_extract_terms_ranks_and_filters():
    data = {
        "name": "Thermodynamik",
        "modules": [
            {
                "name": "Ideale Gase",
                "description": "<p>Die Zustandsgleichung der idealen Gase. Gase, Gase.</p>",
            },
            {"name": "Quiz", "description": "Aufgabe Frage Material"},  # scaffolding -> dropped
        ],
    }
    terms = extract_terms(data)
    assert "Gase" in terms
    assert "Zustandsgleichung" in terms
    assert not ({"Quiz", "Aufgabe", "Frage", "Material"} & set(terms))
    # Frequency ordering: Gase (3x) before Zustandsgleichung (1x).
    assert terms.index("Gase") < terms.index("Zustandsgleichung")


def test_html_is_stripped():
    data = ["<b>Wärmekapazität</b> <a href='x'>Enthalpie</a>"]
    terms = extract_terms(data)
    assert "Wärmekapazität" in terms and "Enthalpie" in terms


def test_min_count_drops_rare_terms():
    data = ["Druck Druck Volumen"]
    assert extract_terms(data, min_count=2) == ["Druck"]


def test_render_vocab_file():
    out = render_vocab_file(["Gase", "Druck"], [210])
    assert out.startswith("#")
    assert "course(s) 210" in out
    assert out.rstrip().endswith("Druck")
