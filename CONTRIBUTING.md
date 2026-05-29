# Mitwirken

Beiträge sind willkommen – Fehlerberichte, Verbesserungsvorschläge und Pull
Requests. Dieses Dokument beschreibt den Entwicklungsablauf.

## Entwicklungsumgebung

```bash
git clone https://github.com/HSD-ZWEK/moodle-panopto-downloader.git
cd moodle-panopto-downloader
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Tests und Linting

```bash
pytest                 # Testsuite
pytest --cov=moodle_panopto_downloader       # mit Coverage
ruff check .           # Linting
ruff format .          # Formatierung
```

Die CI führt Linting und Tests auf Linux, macOS und Windows über mehrere
Python-Versionen aus. Pull Requests müssen die CI bestehen.

## Konventionen

- Code folgt PEP 8; Formatierung und Lint-Regeln werden über `ruff` durchgesetzt.
- Öffentliche Funktionen und Klassen erhalten Type-Hints und Docstrings.
- Netzwerk- und I/O-Code bleibt von der Kernlogik getrennt, damit Letztere ohne
  externe Abhängigkeiten testbar bleibt (siehe `panopto.py`, `config.py`).
- Neue Funktionalität wird durch Tests abgedeckt.

## Pull-Request-Ablauf

1. Issue anlegen oder vorhandenes referenzieren.
2. Feature-Branch von `main` erstellen.
3. Änderungen mit Tests versehen, `pytest` und `ruff check` lokal ausführen.
4. Pull Request mit Beschreibung der Änderung und Motivation öffnen.

## Sicherheitsrelevante Meldungen

Sicherheitslücken werden nicht über öffentliche Issues gemeldet, sondern über die
in `SECURITY.md` beschriebene Kontaktmöglichkeit (sofern vorhanden) bzw. direkt an
die Maintainer.
