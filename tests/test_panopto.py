"""Tests for Panopto link extraction (pure logic, no network)."""

from __future__ import annotations

from moodle_panopto_downloader.panopto import (
    FOLDER,
    VIDEO,
    PanoptoLink,
    detect_hosts,
    extract_links,
)

HOST = "uni.cloud.panopto.eu"


def test_extracts_viewer_and_folder_full_urls():
    data = {
        "modules": [
            {
                "description": f'<a href="https://{HOST}/Panopto/Pages/Viewer.aspx?id=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee">v</a>'
            },
            {
                "contents": [
                    {
                        "fileurl": f"https://{HOST}/Panopto/Pages/Sessions/List.aspx?folderID=11111111-2222-3333-4444-555555555555"
                    }
                ]
            },
        ]
    }
    links = extract_links(data)
    kinds = {(link.kind, link.id) for link in links}
    assert (VIDEO, "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee") in kinds
    assert (FOLDER, "11111111-2222-3333-4444-555555555555") in kinds
    assert all(link.host == HOST for link in links)


def test_embed_url_is_treated_as_video():
    data = [f"https://{HOST}/Panopto/Pages/Embed.aspx?id=0be13721-4a31-4f1d-b812-aba00144ccda&v=1"]
    links = extract_links(data)
    assert len(links) == 1
    assert links[0].kind == VIDEO
    assert (
        links[0].url
        == f"https://{HOST}/Panopto/Pages/Viewer.aspx?id=0be13721-4a31-4f1d-b812-aba00144ccda"
    )


def test_query_param_order_is_irrelevant():
    data = [
        f"https://{HOST}/Panopto/Pages/Viewer.aspx?query=foo&id=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    ]
    assert extract_links(data)[0].id == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_deduplicates_by_kind_and_id():
    uid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    data = [f"https://{HOST}/Panopto/Pages/Viewer.aspx?id={uid}"] * 3
    assert len(extract_links(data)) == 1


def test_bare_id_uses_detected_host():
    data = {
        "a": f"see https://{HOST}/Panopto/Pages/Viewer.aspx?id=11111111-1111-1111-1111-111111111111",
        "b": "also Viewer.aspx?id=22222222-2222-2222-2222-222222222222",
    }
    links = {link.id: link for link in extract_links(data)}
    assert links["22222222-2222-2222-2222-222222222222"].host == HOST


def test_bare_id_without_host_is_ignored():
    data = ["Viewer.aspx?id=22222222-2222-2222-2222-222222222222"]
    assert extract_links(data) == []


def test_bare_id_with_explicit_fallback_host():
    data = ["folderID=33333333-3333-3333-3333-333333333333"]
    links = extract_links(data, host_fallback="x.panopto.eu")
    assert links[0].kind == FOLDER
    assert links[0].host == "x.panopto.eu"


def test_detect_hosts():
    data = [f"https://{HOST}/Panopto/Pages/Viewer.aspx?id=11111111-1111-1111-1111-111111111111"]
    assert detect_hosts(data) == {HOST}


def test_ordering_is_deterministic_videos_first():
    data = [
        f"https://{HOST}/Panopto/Pages/Sessions/List.aspx?folderID=bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        f"https://{HOST}/Panopto/Pages/Viewer.aspx?id=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    ]
    kinds = [link.kind for link in extract_links(data)]
    assert kinds == [VIDEO, FOLDER]


def test_link_url_property():
    assert PanoptoLink(VIDEO, "abc", HOST).url.endswith("/Viewer.aspx?id=abc")
    assert PanoptoLink(FOLDER, "abc", HOST).url.endswith("/List.aspx?folderID=abc")
