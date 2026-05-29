"""Documentation sync check: README.md and README.de.md must stay structurally aligned."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]


def _level2_headings(path: Path) -> list[str]:
    return [
        line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("## ")
    ]


def test_both_readmes_exist():
    assert (ROOT / "README.md").is_file()
    assert (ROOT / "README.de.md").is_file()


def test_readmes_have_matching_section_count():
    en = _level2_headings(ROOT / "README.md")
    de = _level2_headings(ROOT / "README.de.md")
    assert len(en) == len(de), (
        "README.md and README.de.md have a different number of '##' sections; "
        "keep both languages in sync."
    )


def test_readmes_cross_link_each_other():
    assert "README.de.md" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "README.md" in (ROOT / "README.de.md").read_text(encoding="utf-8")
