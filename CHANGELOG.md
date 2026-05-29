# Changelog

All notable changes to this project are documented in this file. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-29

First public release.

### Added

- Command-line tool to discover and download Panopto videos linked in Moodle courses
  via the Moodle Web Services API (`moodle-panopto-downloader`,
  `python -m moodle_panopto_downloader`).
- Discovery from course contents and LTI embeddings; recognition of `Viewer.aspx`,
  `Embed.aspx` and `Sessions/List.aspx` URL forms and of bare ids with host derivation.
- Processing of multiple courses and of all enrolled courses (`--all-courses`).
- Concurrent course queries (`--jobs`) and a reused HTTP connection.
- Resumable downloads via a yt-dlp archive file.
- Configuration via CLI options, environment variables and an ini file.
- Test suite (pytest), linting (ruff) and continuous integration on Linux, macOS and
  Windows for Python 3.10–3.12.
- Bilingual documentation (`README.md`, `README.de.md`) and citation metadata
  (`CITATION.cff`).

[1.0.0]: https://github.com/HSD-ZWEK/moodle-panopto-downloader/releases/tag/v1.0.0
