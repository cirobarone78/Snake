"""Offline tests for the education JSON export. No network."""

from __future__ import annotations

from pathlib import Path

from src.features.education_export import build_education, md_to_html


def _make_course(root: Path) -> None:
    lvl = root / "L1_principiante"
    lvl.mkdir(parents=True)
    (lvl / "README.md").write_text("# Livello 1\n\nIntro al livello.\n", encoding="utf-8")
    (lvl / "02_secondo.md").write_text("# L1.02 — Secondo\n\nTesto due.\n", encoding="utf-8")
    (lvl / "01_primo.md").write_text(
        "# L1.01 — Primo\n\nUna **tabella**:\n\n| a | b |\n|---|---|\n| 1 | 2 |\n",
        encoding="utf-8",
    )


def test_md_to_html_renders_tables_and_bold() -> None:
    html = md_to_html("**ciao**\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
    assert "<strong>ciao</strong>" in html
    assert "<table>" in html and "<td>1</td>" in html


def test_build_education_structure_and_ordering(tmp_path: Path) -> None:
    _make_course(tmp_path)
    payload = build_education(root=tmp_path)
    assert payload["disclaimer"].startswith("Contenuti educativi")
    assert len(payload["levels"]) == 1
    level = payload["levels"][0]
    assert level["id"] == "L1"
    assert level["name"] == "Principiante"
    assert "Intro al livello" in level["intro_html"]
    # chapters sorted by leading number, README excluded
    titles = [c["title"] for c in level["chapters"]]
    assert titles == ["L1.01 — Primo", "L1.02 — Secondo"]
    assert level["chapters"][0]["order"] == 1
    assert "<table>" in level["chapters"][0]["html"]


def test_build_education_skips_missing_levels(tmp_path: Path) -> None:
    # empty root -> no levels, but a valid payload
    payload = build_education(root=tmp_path)
    assert payload["levels"] == []
    assert "generated_at" in payload
