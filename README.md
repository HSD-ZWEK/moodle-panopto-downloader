# moodle-panopto-downloader

🇩🇪 German documentation: [README.de.md](README.de.md)

[![CI](https://github.com/HSD-ZWEK/moodle-panopto-downloader/actions/workflows/ci.yml/badge.svg)](https://github.com/HSD-ZWEK/moodle-panopto-downloader/actions/workflows/ci.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](pyproject.toml)

Moodle Panopto Downloader is a command-line tool for discovering and downloading
Panopto videos embedded in Moodle courses using the Moodle Web Services API.

> **Disclaimer.** This tool is intended for Panopto recordings that the operator is
> authorized to access and permitted to download — for example, when Panopto's download
> setting is enabled and the operator or their institution holds the rights to the
> recordings. It uses the official Moodle Web Services API together with the operator's
> own credentials and does not bypass authentication or any technical protection measure.
> Use is at the operator's own responsibility and subject to the applicable terms of use,
> copyright, and data protection rules.

## Overview

The tool queries a Moodle server with an access token, identifies the Panopto
resources linked in one or more courses, and passes the resulting URLs to
[`yt-dlp`](https://github.com/yt-dlp/yt-dlp) for downloading. It supports both
individual videos and folder-based content structures.

The Moodle base URL, the access token, the Panopto host and the browser used for
Panopto cookies are configurable. The Panopto host is derived from the discovered
links, so the tool is not bound to a specific institution. The set of available API
functions reported by the server is taken into account, which allows operation across
a wide range of Moodle versions.

## Features

- Discovery of Panopto links from course contents and LTI embeddings via the Moodle
  REST API.
- Recognition of the `Viewer.aspx`, `Embed.aspx` and `Sessions/List.aspx` URL forms
  (individual videos and folders) as well as bare ids with host derivation.
- Processing of several courses per invocation and of all courses of the token account.
- Concurrent course queries and a reused HTTP connection.
- Resumable downloads via an archive file.
- Adaptation to the API functions provided by the server.

## Requirements

- Python 3.10 or newer.
- `yt-dlp` and `ffmpeg` available on `PATH`. `yt-dlp` is installed as a dependency;
  `ffmpeg` is provided separately.
- A Moodle Web Services token whose service includes at least
  `core_webservice_get_site_info` and `core_course_get_contents`. The functions
  `mod_lti_get_ltis_by_courses` and `core_enrol_get_users_courses` are used when
  available.

## Installation

Installation from the source directory with pip:

```bash
pip install .
```

Installation directly from the Git repository:

```bash
pip install "git+https://github.com/HSD-ZWEK/moodle-panopto-downloader.git"
```

`ffmpeg` is provided per platform:

```bash
# Linux (Debian/Ubuntu)
sudo apt install ffmpeg

# macOS (Homebrew)
brew install ffmpeg

# Windows (winget)
winget install Gyan.FFmpeg
```

After installation the command `moodle-panopto-downloader` is available. The tool can
also be invoked through `python -m moodle_panopto_downloader`.

A Moodle token is created in the Moodle web interface under
*Site administration → Server → Web services → Manage tokens → Create token*, for the
own user account, on a service that contains the functions listed above (the built-in
*Moodle Mobile* service is sufficient). The `moodle/webservice:createtoken` capability
is required; otherwise the Moodle administration creates the token. The token is to be
treated like a password.

## Configuration

Each setting is resolved in the following order:
**CLI option → environment variable → configuration file → default**.

The configuration file is searched at `mpdl.ini` in the working directory or at
`~/.config/moodle-panopto-downloader/config.ini`. A template is provided in
[`config.example.ini`](config.example.ini):

```ini
[moodle]
base_url = https://moodle.example.edu

[download]
browser = safari
out = downloads
jobs = 4
```

The token is additionally read from a local `.moodle_token` file when present. The
configuration file and the token file are excluded from version control by
`.gitignore`.

## Usage

Base URL and token are supplied through environment variables. Linux and macOS:

```bash
export MOODLE_URL="https://moodle.example.edu"
export MOODLE_TOKEN="0123456789abcdef0123456789abcdef"
```

Windows (PowerShell):

```powershell
$env:MOODLE_URL   = "https://moodle.example.edu"
$env:MOODLE_TOKEN = "0123456789abcdef0123456789abcdef"
```

Downloaded files are stored as `<output>/<Panopto folder name>/<video title>.mp4`.
Individual videos without a folder are stored under `<output>/Single Videos/`.

### Panopto authentication

Downloading requires an authenticated Panopto session. Two methods are available:

- `--browser <name>` reads cookies from a browser that is logged in to Panopto. The
  default depends on the platform (Safari on macOS, Chrome on Windows, Firefox on
  Linux).
- `--cookies-file <path>` uses a cookie export in Netscape format instead of a live
  browser.

### Options

| Option | Description |
|---|---|
| `--base-url URL` | Moodle base URL (or `MOODLE_URL` / configuration). |
| `--token TOKEN` | Web service token (or `MOODLE_TOKEN` / `--token-file` / configuration). |
| `--token-file PATH` | File that contains the token. |
| `--config PATH` | Path to an ini configuration file. |
| `--all-courses` | Process all courses of the token account. |
| `--list` | Print the discovered URLs to stdout; do not download. |
| `--json` | Print the discovered links as JSON to stdout; do not download. |
| `--dry-run` | Resolve titles and approximate sizes via yt-dlp without downloading. |
| `--since DATE` | Only download videos uploaded on/after DATE (`YYYY-MM-DD`); passed to yt-dlp. |
| `--write-urls FILE` | Write the discovered URLs to a file. |
| `--out DIR` | Output directory (default `downloads`). |
| `--browser NAME` | Browser for the Panopto cookies. |
| `--cookies-file PATH` | `cookies.txt` in Netscape format instead of a browser. |
| `--panopto-host HOST` | Fallback host for bare-id links if detection fails. |
| `--archive PATH` | yt-dlp archive file (default `<out>/.downloaded.txt`). |
| `--yt-dlp-args "..."` | Additional arguments passed verbatim to yt-dlp. |
| `--jobs N` | Number of courses queried in parallel (default 4). |
| `-v`, `--verbose` | Increase log verbosity (repeatable). |
| `-q`, `--quiet` | Log warnings and errors only. |

## Examples

```bash
# Print the Panopto URLs of a course without downloading:
moodle-panopto-downloader 210 --list

# Download all videos of a course:
moodle-panopto-downloader 210

# Process several courses in one invocation:
moodle-panopto-downloader 210 233 477

# Process all courses of the token account:
moodle-panopto-downloader --all-courses

# Select the browser for Panopto cookies, set the output directory, save the URL list:
moodle-panopto-downloader 210 --browser chrome --out ~/videos --write-urls urls_210.txt

# Pipe the discovered URLs into a file:
moodle-panopto-downloader 210 --list > urls_210.txt

# Emit the discovered links as JSON for further processing:
moodle-panopto-downloader 210 --json > links_210.json

# Resolve titles and sizes without downloading:
moodle-panopto-downloader 210 --dry-run

# Download only videos uploaded on or after a date:
moodle-panopto-downloader 210 --since 2024-10-01
```

### How it works

1. `core_webservice_get_site_info` validates the token and reports account details,
   the Moodle version and the set of available API functions.
2. `core_course_get_contents` retrieves the structure of each course.
3. When available, `mod_lti_get_ltis_by_courses` adds Panopto links embedded as LTI
   tools.
4. All text fields of the responses are scanned for Panopto links; the host is read
   along and the URLs are reconstructed canonically.
5. The de-duplicated URL list is passed to `yt-dlp`. Panopto folders are resolved to
   their individual videos. An archive file makes interrupted runs resumable.

## Troubleshooting

- **Connection fails or token invalid.** Verify the base URL and the token. Ensure that
  web services and the REST protocol are enabled on the server.
- **`core_course_get_contents` not available.** Add the function to the token's
  external service in Moodle.
- **No links found.** The course may embed Panopto in a form the API does not expose
  (for example inside file attachments). Inspection with `--list` or `--all-courses`
  helps to narrow down the cause.
- **`yt-dlp` not found.** Install `yt-dlp` and `ffmpeg` and make them available on
  `PATH`.
- **Download requests authentication.** Log in to Panopto in the selected browser or
  pass `--cookies-file`.

## Privacy and Legal Considerations

The tool does not bypass authentication; it uses only access that the executing person
already legitimately holds. Use is limited to servers and content for which both an
access authorization and a download permission exist — for example, where the Panopto
download setting is enabled and the relevant rights are held.

Downloaded videos are subject to the copyright and terms of use of the respective
institution. For recordings that contain identifiable persons, the applicable data
protection regulations apply. Responsibility for lawful use rests with the executing
person.

## Project Background

This software was developed at Hochschule Düsseldorf (University of Applied Sciences)
by ZWEK – Centre for Training and Competence Development (Zentrum für Weiterbildung und
Kompetenzentwicklung) within the KIVi-Azubi research project.

```
Copyright (c) Hochschule Düsseldorf – University of Applied Sciences
ZWEK – Centre for Training and Competence Development
Developed within the KIVi-Azubi research project
```

## Research Context

The tool was developed within the KIVi-Azubi research project at Hochschule Düsseldorf
(University of Applied Sciences), ZWEK – Centre for Training and Competence Development.
The project conducts a media-pedagogical analysis of digital teaching and learning
infrastructures — Moodle courses, parametric STACK quizzes, interactive simulations and
Panopto videos — and derives recommendations for teaching, support, and the targeted use
of AI and VR where these add genuine didactic value.

A central method is the systematic analysis of Moodle learning units through two
established frameworks: the revised Bloom taxonomy (Anderson & Krathwohl) for cognitive
demand, and TPACK (Mishra & Koehler) for the interplay of content, pedagogy and
technology. Panopto explanatory videos are part of the analysed course material.
Retrieving them locally enables transcription and the assessment of how far they support
concept understanding, and it supports reproducible research data management with stable
references to the analysed media.

Authorship and provenance are documented in [`CITATION.cff`](CITATION.cff) and
[`AUTHORS.md`](AUTHORS.md).

## Contributing

Notes on the development environment, tests and pull requests are provided in
[`CONTRIBUTING.md`](CONTRIBUTING.md). Short form:

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## Citation

Machine-readable citation metadata are provided in [`CITATION.cff`](CITATION.cff),
validated against CFF schema 1.2.0. GitHub renders a "Cite this repository" entry from
this file and produces APA and BibTeX output.

For a persistently verifiable reference, a release is archived on
[Zenodo](https://zenodo.org). The GitHub–Zenodo integration mints a DOI per release and
a version-independent concept DOI. The DOI is then added to `CITATION.cff` (under
`identifiers`) and to the BibTeX entry (`doi = {...}`). Until then, the repository URL
serves as the reference.

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
  % doi     = {10.5281/zenodo.0000000}  % add after archiving a release on Zenodo
}
```

`version` and `date-released` in `CITATION.cff`, and `version` and `doi` in the BibTeX
entry, are updated for each release.

## License

Released under the [GNU General Public License v3.0 or later](LICENSE). As a copyleft
license, the GPL requires that redistributions and modified versions are also licensed
under the GPL.
