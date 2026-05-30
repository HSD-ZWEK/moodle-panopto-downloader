"""Tests for deriving a domain vocabulary from Moodle course contents."""

from __future__ import annotations

from moodle_panopto_downloader.vocab import (
    extract_terms,
    iter_file_urls,
    render_vocab_file,
    text_from_file,
)


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


def test_captures_lowercase_technical_terms():
    # Lower-case adjectives must be captured (the previous version missed them).
    data = ["Die Zustandsänderung ist isotherm, isobar oder isochor. isotherm bleibt isotherm."]
    terms = extract_terms(data)
    assert "isotherm" in terms
    assert "isobar" in terms
    assert "isochor" in terms


def test_extra_texts_are_included():
    terms = extract_terms({"name": "Kurs"}, extra_texts=["Adiabatengleichung Adiabatengleichung"])
    assert "Adiabatengleichung" in terms


def test_iter_file_urls_filters_by_suffix():
    data = [
        {
            "modules": [
                {
                    "contents": [
                        {
                            "filename": "skript.pdf",
                            "fileurl": "https://m/pluginfile.php/1/skript.pdf",
                        },
                        {"filename": "clip.mp4", "fileurl": "https://m/pluginfile.php/1/clip.mp4"},
                    ]
                }
            ]
        }
    ]
    urls = iter_file_urls(data)
    assert urls == [("https://m/pluginfile.php/1/skript.pdf", "skript.pdf")]


def test_text_from_file_text_and_html():
    assert "Wärme" in text_from_file("a.txt", "Wärme".encode())
    assert text_from_file("a.html", b"<b>Enthalpie</b>").strip() == "Enthalpie"


def test_render_vocab_file():
    out = render_vocab_file(["Gase", "Druck"], [210])
    assert out.startswith("#")
    assert "course(s) 210" in out
    assert out.rstrip().endswith("Druck")
