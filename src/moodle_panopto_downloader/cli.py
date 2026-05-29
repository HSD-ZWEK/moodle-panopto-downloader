# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Hochschule Düsseldorf – University of Applied Sciences
# ZWEK – Centre for Training and Competence Development
# Developed within the KIVi-Azubi research project
"""Command-line interface and run orchestration."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from . import __version__
from .config import Config, build_config
from .downloader import download, probe
from .errors import MoodleAPIError, MoodlePanoptoError
from .moodle import MoodleClient
from .panopto import PanoptoLink, extract_links
from .utils import configure_logging, get_logger

_log = get_logger()


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    parser = argparse.ArgumentParser(
        prog="moodle-panopto-downloader",
        description="Discover and download Panopto videos linked in Moodle courses.",
    )
    parser.add_argument("courses", nargs="*", help="Moodle course id(s) to process.")
    parser.add_argument("--base-url", help="Moodle base URL (env MOODLE_URL / config).")
    parser.add_argument("--token", help="Web service token (env MOODLE_TOKEN / config / file).")
    parser.add_argument("--token-file", help="Path to a file containing the token.")
    parser.add_argument("--config", help="Path to an ini config file.")
    parser.add_argument(
        "--all-courses",
        action="store_true",
        help="Process every course the token's user is enrolled in.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_only",
        help="Only print the Panopto URLs found (to stdout); do not download.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Print the discovered links as JSON (to stdout); do not download.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve titles and approximate sizes via yt-dlp without downloading.",
    )
    parser.add_argument(
        "--since",
        metavar="DATE",
        help="Only download videos uploaded on/after DATE (YYYY-MM-DD); passed to yt-dlp.",
    )
    parser.add_argument("--write-urls", metavar="FILE", help="Write the discovered URLs to FILE.")
    parser.add_argument("--out", help="Download directory (default: downloads).")
    parser.add_argument("--browser", help="Browser to read Panopto cookies from.")
    parser.add_argument("--cookies-file", help="Netscape cookies.txt for Panopto cookies.")
    parser.add_argument("--panopto-host", help="Fallback Panopto host for bare-id links.")
    parser.add_argument("--archive", help="yt-dlp archive (default: <out>/.downloaded.txt).")
    parser.add_argument("--yt-dlp-args", help="Extra arguments passed verbatim to yt-dlp.")
    parser.add_argument("--jobs", type=int, help="Parallel course scrapes (default: 4).")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (repeatable).",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Only log warnings and errors.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def scrape_course(
    client: MoodleClient, courseid: int, host_fallback: str | None
) -> list[PanoptoLink]:
    """Collect Panopto links from one course (contents + LTI tools)."""
    contents = client.get_course_contents(courseid)
    links: list[PanoptoLink] = list(extract_links(contents, host_fallback))
    if client.has("mod_lti_get_ltis_by_courses"):
        try:
            links += extract_links(client.get_course_ltis(courseid), host_fallback)
        except MoodleAPIError:
            _log.debug("LTI lookup not usable for course %s; skipping.", courseid)
    return links


def scrape_courses(
    client: MoodleClient, course_ids: Sequence[int], host_fallback: str | None, jobs: int
) -> list[PanoptoLink]:
    """Scrape several courses concurrently, preserving input order in the output."""
    results: list[list[PanoptoLink]] = [[] for _ in course_ids]
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        futures = {
            pool.submit(scrape_course, client, cid, host_fallback): i
            for i, cid in enumerate(course_ids)
        }
        for future in futures:
            index = futures[future]
            cid = course_ids[index]
            try:
                links = future.result()
            except MoodlePanoptoError as exc:
                _log.error("Course %s: %s", cid, exc)
                continue
            results[index] = links
            videos = sum(1 for link in links if link.kind == "video")
            _log.info("Course %s: %d video(s) + %d folder(s)", cid, videos, len(links) - videos)
    # Flatten in order and de-duplicate by URL.
    seen: set[str] = set()
    flat: list[PanoptoLink] = []
    for links in results:
        for link in links:
            if link.url not in seen:
                seen.add(link.url)
                flat.append(link)
    return flat


def _resolve_course_ids(
    client: MoodleClient, args: argparse.Namespace, info: dict[str, Any]
) -> list[int]:
    if args.all_courses:
        if not client.has("core_enrol_get_users_courses"):
            raise MoodlePanoptoError(
                "--all-courses needs core_enrol_get_users_courses, which this token's "
                "service does not expose."
            )
        courses = client.get_user_courses(int(info["userid"]))
        ids = [int(c["id"]) for c in courses]
        _log.info("--all-courses: %d enrolled course(s).", len(ids))
        return ids
    if not args.courses:
        raise MoodlePanoptoError("Provide one or more course ids, or use --all-courses.")
    return [int(c) for c in args.courses]


def links_to_json(links: Sequence[PanoptoLink]) -> str:
    """Serialise discovered links as an indented JSON array."""
    return json.dumps(
        [{"kind": link.kind, "id": link.id, "host": link.host, "url": link.url} for link in links],
        indent=2,
        ensure_ascii=False,
    )


def run(args: argparse.Namespace) -> int:
    """Execute a configured run. Returns a process exit code."""
    config: Config = build_config(args)
    client = MoodleClient(config.base_url, config.token)

    info = client.site_info()
    _log.info(
        "Connected as %s @ %s (Moodle %s)",
        info.get("fullname"),
        info.get("sitename"),
        info.get("release"),
    )

    if not client.has("core_course_get_contents"):
        raise MoodlePanoptoError(
            "The token's service lacks core_course_get_contents — add it in Moodle."
        )

    course_ids = _resolve_course_ids(client, args, info)
    links = scrape_courses(client, course_ids, config.panopto_host, config.jobs)
    urls = [link.url for link in links]

    if not urls:
        _log.warning("No Panopto links found.")
        return 0
    _log.info("%d unique Panopto URL(s) total.", len(urls))

    if args.write_urls:
        Path(args.write_urls).write_text("\n".join(urls) + "\n", encoding="utf-8")
        _log.info("Wrote URL list: %s", args.write_urls)

    if args.json_output:
        print(links_to_json(links))
        return 0

    if args.list_only:
        for url in urls:
            print(url)
        return 0

    if args.dry_run:
        rc = probe(urls, config)
        if rc != 0:
            _log.warning("Dry run finished with skips (yt-dlp rc=%d).", rc)
        return 0

    rc = download(urls, config)
    if rc == 0:
        _log.info("Done. Files in: %s/", config.out_dir)
    else:
        _log.warning("Done with skips (yt-dlp rc=%d) — usual for locked/empty videos.", rc)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. Parses arguments, configures logging and runs."""
    args = build_parser().parse_args(argv)
    configure_logging(-1 if args.quiet else args.verbose)
    try:
        return run(args)
    except MoodlePanoptoError as exc:
        _log.error("%s", exc)
        return 1
    except KeyboardInterrupt:  # pragma: no cover
        _log.error("Interrupted.")
        return 130


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
