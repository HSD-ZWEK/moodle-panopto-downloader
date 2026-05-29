# moodle-panopto-downloader

🇬🇧 English documentation: [README.md](README.md)

[![CI](https://github.com/HSD-ZWEK/moodle-panopto-downloader/actions/workflows/ci.yml/badge.svg)](https://github.com/HSD-ZWEK/moodle-panopto-downloader/actions/workflows/ci.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](pyproject.toml)

Der Moodle Panopto Downloader ist ein Kommandozeilenwerkzeug zum Auffinden und
Herunterladen von in Moodle-Kursen eingebetteten Panopto-Videos. Die Erkennung erfolgt
über die Moodle-Webservice-API.

## Überblick

Das Werkzeug fragt einen Moodle-Server mit einem Zugriffstoken ab, ermittelt die in
einem oder mehreren Kursen verlinkten Panopto-Ressourcen und übergibt die resultierenden
URLs an [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) zum Herunterladen. Unterstützt
werden sowohl Einzelvideos als auch ordnerbasierte Inhaltsstrukturen.

Moodle-Basis-URL, Zugriffstoken, Panopto-Host und der für die Panopto-Cookies genutzte
Browser sind konfigurierbar. Der Panopto-Host wird aus den gefundenen Links abgeleitet,
sodass keine Bindung an eine bestimmte Hochschule besteht. Die vom Server gemeldeten
verfügbaren API-Funktionen werden berücksichtigt, was den Einsatz über viele
Moodle-Versionen hinweg ermöglicht.

## Funktionen

- Erkennung von Panopto-Links aus Kursinhalten und LTI-Einbettungen über die
  Moodle-REST-API.
- Erkennung der URL-Formen `Viewer.aspx`, `Embed.aspx` und `Sessions/List.aspx`
  (Einzelvideos und Ordner) sowie reiner IDs mit Host-Ableitung.
- Verarbeitung mehrerer Kurse pro Aufruf sowie aller Kurse des Token-Kontos.
- Nebenläufige Kursabfragen und wiederverwendete HTTP-Verbindung.
- Fortsetzbare Downloads über eine Archivdatei.
- Anpassung an die vom Server bereitgestellten API-Funktionen.

## Voraussetzungen

- Python 3.10 oder neuer.
- `yt-dlp` und `ffmpeg` im Suchpfad (`PATH`). `yt-dlp` wird als Abhängigkeit
  mitinstalliert; `ffmpeg` ist separat bereitzustellen.
- Ein Moodle-Webservice-Token, dessen Service mindestens
  `core_webservice_get_site_info` und `core_course_get_contents` umfasst. Die Funktionen
  `mod_lti_get_ltis_by_courses` und `core_enrol_get_users_courses` werden genutzt, sofern
  verfügbar.

## Installation

Installation aus dem Quellverzeichnis mit pip:

```bash
pip install .
```

Installation direkt aus dem Git-Repository:

```bash
pip install "git+https://github.com/HSD-ZWEK/moodle-panopto-downloader.git"
```

`ffmpeg` wird je Plattform bereitgestellt:

```bash
# Linux (Debian/Ubuntu)
sudo apt install ffmpeg

# macOS (Homebrew)
brew install ffmpeg

# Windows (winget)
winget install Gyan.FFmpeg
```

Nach der Installation steht der Befehl `moodle-panopto-downloader` zur Verfügung. Der
Aufruf über `python -m moodle_panopto_downloader` ist ebenfalls möglich.

Ein Moodle-Token wird in der Moodle-Weboberfläche erzeugt unter
*Website-Administration → Server → Webservices → Tokens verwalten → Token erstellen*,
für das eigene Benutzerkonto, auf einem Service mit den oben genannten Funktionen (der
eingebaute Dienst *Moodle Mobile* genügt). Die Berechtigung
`moodle/webservice:createtoken` ist erforderlich; andernfalls erstellt die
Moodle-Administration das Token. Das Token ist wie ein Passwort zu behandeln.

## Konfiguration

Jede Einstellung wird in folgender Reihenfolge aufgelöst:
**CLI-Option → Umgebungsvariable → Konfigurationsdatei → Vorgabewert**.

Die Konfigurationsdatei wird unter `mpdl.ini` im Arbeitsverzeichnis oder unter
`~/.config/moodle-panopto-downloader/config.ini` gesucht. Eine Vorlage liegt in
[`config.example.ini`](config.example.ini):

```ini
[moodle]
base_url = https://moodle.example.edu

[download]
browser = safari
out = downloads
jobs = 4
```

Das Token wird zusätzlich aus einer lokalen Datei `.moodle_token` gelesen, sofern
vorhanden. Konfigurationsdatei und Token-Datei sind durch `.gitignore` von der
Versionsverwaltung ausgenommen.

## Verwendung

Basis-URL und Token werden über Umgebungsvariablen bereitgestellt. Linux und macOS:

```bash
export MOODLE_URL="https://moodle.example.edu"
export MOODLE_TOKEN="0123456789abcdef0123456789abcdef"
```

Windows (PowerShell):

```powershell
$env:MOODLE_URL   = "https://moodle.example.edu"
$env:MOODLE_TOKEN = "0123456789abcdef0123456789abcdef"
```

Heruntergeladene Dateien werden als `<Zielordner>/<Panopto-Ordnername>/<Videotitel>.mp4`
abgelegt. Einzelvideos ohne Ordnerzuordnung liegen unter `<Zielordner>/Single Videos/`.

### Panopto-Authentifizierung

Der Download erfordert eine angemeldete Panopto-Sitzung. Zwei Verfahren stehen zur
Verfügung:

- `--browser <name>` liest die Cookies aus einem Browser, in dem eine Anmeldung bei
  Panopto besteht. Der Vorgabewert richtet sich nach der Plattform (Safari unter macOS,
  Chrome unter Windows, Firefox unter Linux).
- `--cookies-file <pfad>` verwendet einen Cookie-Export im Netscape-Format anstelle
  eines aktiven Browsers.

### Optionen

| Option | Beschreibung |
|---|---|
| `--base-url URL` | Moodle-Basis-URL (oder `MOODLE_URL` / Konfiguration). |
| `--token TOKEN` | Webservice-Token (oder `MOODLE_TOKEN` / `--token-file` / Konfiguration). |
| `--token-file PFAD` | Datei, die das Token enthält. |
| `--config PFAD` | Pfad zu einer ini-Konfigurationsdatei. |
| `--all-courses` | Alle Kurse des Token-Kontos verarbeiten. |
| `--list` | Gefundene URLs nach stdout ausgeben; nicht herunterladen. |
| `--json` | Gefundene Links als JSON nach stdout ausgeben; nicht herunterladen. |
| `--dry-run` | Titel und ungefähre Größen via yt-dlp ermitteln, ohne herunterzuladen. |
| `--since DATUM` | Nur Videos ab Upload-Datum laden (`JJJJ-MM-TT`); an yt-dlp übergeben. |
| `--write-urls DATEI` | Gefundene URLs in eine Datei schreiben. |
| `--out ORDNER` | Zielordner (Vorgabe `downloads`). |
| `--browser NAME` | Browser für die Panopto-Cookies. |
| `--cookies-file PFAD` | `cookies.txt` im Netscape-Format statt eines Browsers. |
| `--panopto-host HOST` | Ersatz-Host für reine ID-Links, falls die Erkennung fehlschlägt. |
| `--archive PFAD` | yt-dlp-Archivdatei (Vorgabe `<out>/.downloaded.txt`). |
| `--yt-dlp-args "..."` | Zusätzliche Argumente direkt an yt-dlp. |
| `--jobs N` | Anzahl parallel abgefragter Kurse (Vorgabe 4). |
| `-v`, `--verbose` | Höhere Protokollausführlichkeit (mehrfach steigerbar). |
| `-q`, `--quiet` | Nur Warnungen und Fehler protokollieren. |

## Beispiele

```bash
# Panopto-URLs eines Kurses ausgeben, ohne herunterzuladen:
moodle-panopto-downloader 210 --list

# Alle Videos eines Kurses herunterladen:
moodle-panopto-downloader 210

# Mehrere Kurse in einem Aufruf verarbeiten:
moodle-panopto-downloader 210 233 477

# Alle Kurse des Token-Kontos verarbeiten:
moodle-panopto-downloader --all-courses

# Browser für Panopto-Cookies wählen, Zielordner setzen, URL-Liste speichern:
moodle-panopto-downloader 210 --browser chrome --out ~/videos --write-urls urls_210.txt

# Gefundene URLs in eine Datei umleiten:
moodle-panopto-downloader 210 --list > urls_210.txt

# Gefundene Links als JSON zur Weiterverarbeitung ausgeben:
moodle-panopto-downloader 210 --json > links_210.json

# Titel und Größen ermitteln, ohne herunterzuladen:
moodle-panopto-downloader 210 --dry-run

# Nur Videos ab einem Datum herunterladen:
moodle-panopto-downloader 210 --since 2024-10-01
```

### Funktionsweise

1. `core_webservice_get_site_info` prüft das Token und liefert Kontoangaben, die
   Moodle-Version und die Menge der verfügbaren API-Funktionen.
2. `core_course_get_contents` ruft die Struktur jedes Kurses ab.
3. Sofern verfügbar, ergänzt `mod_lti_get_ltis_by_courses` die als LTI-Werkzeug
   eingebetteten Panopto-Links.
4. Alle Textfelder der Antworten werden nach Panopto-Links durchsucht; der Host wird
   mitgelesen und die URLs werden kanonisch rekonstruiert.
5. Die entdoppelte URL-Liste wird an `yt-dlp` übergeben. Panopto-Ordner werden zu ihren
   einzelnen Videos aufgelöst. Eine Archivdatei macht abgebrochene Läufe fortsetzbar.

## Fehlerbehebung

- **Verbindung schlägt fehl oder Token ungültig.** Basis-URL und Token prüfen.
  Sicherstellen, dass Webservices und das REST-Protokoll am Server aktiviert sind.
- **`core_course_get_contents` nicht verfügbar.** Die Funktion dem externen Service des
  Tokens in Moodle hinzufügen.
- **Keine Links gefunden.** Der Kurs bettet Panopto möglicherweise in einer Form ein,
  die die API nicht ausgibt (etwa in Dateianhängen). Eine Prüfung mit `--list` oder
  `--all-courses` grenzt die Ursache ein.
- **`yt-dlp` nicht gefunden.** `yt-dlp` und `ffmpeg` installieren und im `PATH`
  bereitstellen.
- **Download verlangt eine Anmeldung.** Im gewählten Browser bei Panopto anmelden oder
  `--cookies-file` übergeben.

## Datenschutz und rechtliche Hinweise

Das Werkzeug umgeht keine Authentifizierung; es nutzt ausschließlich Zugänge, die der
ausführenden Person bereits rechtmäßig zustehen. Der Einsatz ist auf Server und Inhalte
beschränkt, für die eine Zugriffsberechtigung besteht.

Heruntergeladene Videos unterliegen dem Urheberrecht und den Nutzungsbedingungen der
jeweiligen Einrichtung. Bei Aufzeichnungen mit erkennbaren Personen sind die
einschlägigen Datenschutzbestimmungen zu beachten. Verantwortung für die rechtmäßige
Nutzung liegt bei der ausführenden Person.

## Projekthintergrund

Diese Software wurde an der Hochschule Düsseldorf (University of Applied Sciences) durch
ZWEK – Centre for Training and Competence Development (Zentrum für Weiterbildung und
Kompetenzentwicklung) im Forschungsprojekt KIVi-Azubi entwickelt.

```
Copyright (c) Hochschule Düsseldorf – University of Applied Sciences
ZWEK – Centre for Training and Competence Development
Developed within the KIVi-Azubi research project
```

## Forschungskontext

Das Werkzeug wurde im Forschungsprojekt KIVi-Azubi an der Hochschule Düsseldorf
(University of Applied Sciences), ZWEK – Centre for Training and Competence Development,
entwickelt. Das Projekt führt eine medienpädagogische Analyse digitaler
Lehr-/Lerninfrastrukturen durch — Moodle-Kurse, parametrische STACK-Quizze, interaktive
Simulationen und Panopto-Videos — und leitet Empfehlungen für Lehre, Support und den
gezielten Einsatz von KI und VR dort ab, wo ein echter didaktischer Mehrwert entsteht.

Eine zentrale Methode ist die systematische Analyse von Moodle-Lerneinheiten anhand
zweier etablierter Rahmenmodelle: der revidierten Bloom-Taxonomie (Anderson & Krathwohl)
für die kognitive Anforderungstiefe und TPACK (Mishra & Koehler) für das Zusammenspiel
von Inhalt, Didaktik und Technologie. Panopto-Erklärvideos sind Teil des analysierten
Kursmaterials. Ihre lokale Beschaffung ermöglicht die Transkription und die Bewertung,
inwieweit sie das Begriffsverständnis stützen, und unterstützt ein reproduzierbares
Forschungsdatenmanagement mit stabilen Referenzen auf die analysierten Medien.

Autorenschaft und Herkunft sind in [`CITATION.cff`](CITATION.cff) und
[`AUTHORS.md`](AUTHORS.md) dokumentiert.

## Mitwirken

Hinweise zu Entwicklungsumgebung, Tests und Pull Requests stehen in
[`CONTRIBUTING.md`](CONTRIBUTING.md). Kurzfassung:

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## Zitation

Die maschinenlesbaren Zitationsmetadaten liegen in [`CITATION.cff`](CITATION.cff),
validiert gegen das CFF-Schema 1.2.0. GitHub erzeugt daraus „Cite this repository" sowie
APA- und BibTeX-Ausgaben.

Für eine dauerhaft verifizierbare Referenz wird ein Release über
[Zenodo](https://zenodo.org) archiviert. Die GitHub–Zenodo-Integration vergibt pro
Release eine DOI sowie eine versionsübergreifende Concept-DOI. Die DOI wird anschließend
in `CITATION.cff` (Abschnitt `identifiers`) und in den BibTeX-Eintrag (`doi = {...}`)
eingetragen. Bis dahin dient die Repository-URL als Referenz.

APA:

```
Steier, C.-M. (2026). moodle-panopto-downloader (Version 1.0.0) [Software].
ZWEK – Centre for Training and Competence Development, Hochschule Düsseldorf –
University of Applied Sciences. https://github.com/HSD-ZWEK/moodle-panopto-downloader
```

BibTeX:

```bibtex
@software{steier2026moodlepanoptodownloader,
  author    = {Steier, Christian-Maximilian},
  title     = {moodle-panopto-downloader},
  version   = {1.0.0},
  year      = {2026},
  publisher = {ZWEK -- Centre for Training and Competence Development,
               Hochschule D\"usseldorf -- University of Applied Sciences},
  url       = {https://github.com/HSD-ZWEK/moodle-panopto-downloader},
  note      = {Developed within the KIVi-Azubi research project}
  % doi     = {10.5281/zenodo.0000000}  % nach Zenodo-Archivierung ergänzen
}
```

`version` und `date-released` in `CITATION.cff` sowie `version` und `doi` im
BibTeX-Eintrag werden je Release aktualisiert.

## Lizenz

Veröffentlicht unter der [GNU General Public License v3.0 oder später](LICENSE). Als
Copyleft-Lizenz verpflichtet die GPL dazu, dass Weitergaben und abgewandelte Versionen
ebenfalls unter der GPL stehen.
