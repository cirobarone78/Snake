"""Export the education modules to JSON for the static dashboard (Fase 7).

Walks the ``education/`` tree (the multi-level didactic course, ADR-015) and emits
``public/data/education.json``: per level, an intro plus each chapter rendered to
HTML, so the dashboard can show the lessons to novices without a Markdown runtime.

Build-time only (the JSON is committed); the conversion uses the pure-python
``markdown`` library. Pure functions over the filesystem; unit-testable offline.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import markdown as _md
import pandas as pd

from src.features.report_json import write_report_json

EDU_ROOT = Path("education")
JSON_PATH = Path("public/data/education.json")

# Stable level metadata (folder -> id, name, subtitle). The course has 4 levels.
_LEVELS: list[tuple[str, str, str, str]] = [
    ("L1_principiante", "L1", "Principiante", "Investor 101"),
    ("L2_intermedio", "L2", "Intermedio", "Smart Investor"),
    ("L3_avanzato", "L3", "Avanzato", "Quantitative Investor"),
    ("L4_esperto", "L4", "Esperto", "Professional"),
]

_MD_EXTENSIONS = ["extra", "sane_lists"]


def md_to_html(text: str) -> str:
    """Render Markdown to HTML (tables, fenced code, lists), build-time only."""
    return _md.markdown(text, extensions=_MD_EXTENSIONS, output_format="html")


def _title_of(raw: str, fallback: str) -> str:
    """First ``# H1`` line as the chapter title, else a humanised fallback."""
    for line in raw.splitlines():
        m = re.match(r"^#\s+(.*)$", line.strip())
        if m:
            return m.group(1).strip()
    return fallback.replace("_", " ").strip()


def _order_of(filename: str) -> int:
    """Leading ``NN_`` number for ordering chapters (0 if absent)."""
    m = re.match(r"^(\d+)", filename)
    return int(m.group(1)) if m else 0


def build_education(root: Path = EDU_ROOT) -> dict[str, Any]:
    """Assemble the education payload: levels, intros, and HTML-rendered chapters."""
    levels: list[dict[str, Any]] = []
    for folder, level_id, name, subtitle in _LEVELS:
        directory = root / folder
        if not directory.exists():
            continue
        readme = directory / "README.md"
        intro_html = md_to_html(readme.read_text(encoding="utf-8")) if readme.exists() else ""
        chapters: list[dict[str, Any]] = []
        for path in sorted(directory.glob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            raw = path.read_text(encoding="utf-8")
            chapters.append(
                {
                    "order": _order_of(path.name),
                    "slug": path.stem,
                    "title": _title_of(raw, path.stem),
                    "html": md_to_html(raw),
                }
            )
        chapters.sort(key=lambda c: c["order"])
        levels.append(
            {
                "id": level_id,
                "name": name,
                "subtitle": subtitle,
                "intro_html": intro_html,
                "chapters": chapters,
            }
        )
    return {
        "generated_at": pd.Timestamp.now(tz="UTC").floor("min").isoformat(),
        "title": "Modulo didattico — Mercati & analisi quantitativa",
        "disclaimer": "Contenuti educativi. Non è consulenza finanziaria.",
        "levels": levels,
    }


def main() -> None:
    write_report_json(build_education(), JSON_PATH)


if __name__ == "__main__":
    main()
