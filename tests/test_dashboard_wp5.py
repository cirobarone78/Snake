"""Guards for the WP5 dashboard views (Opportunità + Modello).

The dashboard is plain files, not a build: nothing else would catch a renderer
pointing at an id that no longer exists in the markup, or a copywriting slip
that turns a descriptive ranking into a forecast. These checks are cheap and
they encode two acceptance criteria of WP5 that are otherwise only human-eyed:
the payload contract the renderers read, and the language rules of §12 of
``docs/PIANO_SVILUPPO.md``.
"""

from __future__ import annotations

import re
from pathlib import Path

APP_JS = Path("public/app.js")
INDEX_HTML = Path("public/index.html")

# Il blocco WP5 di app.js: dal suo marcatore fino alla sezione footer.
WP5_START = "/* ---------- Opportunità: classifica descrittiva"
WP5_END = "/* ---------- Footer ---------- */"

# Vietati dalla §12 del piano: la classifica descrive, non promette.
FORBIDDEN = [
    re.compile(r"\bcompr(a|are|ala|alo|iamo|ate)\b", re.IGNORECASE),
    re.compile(r"\bsalir[àa]\b", re.IGNORECASE),
    re.compile(r"\bprevist[oiae]\b", re.IGNORECASE),
    re.compile(r"\bprevediamo\b", re.IGNORECASE),
]


def _wp5_block() -> str:
    text = APP_JS.read_text(encoding="utf-8")
    start = text.index(WP5_START)
    end = text.index(WP5_END, start)
    return text[start:end]


def _opportunita_panel() -> str:
    html = INDEX_HTML.read_text(encoding="utf-8")
    start = html.index('<section id="opportunita"')
    return html[start : html.index("</section>", start)]


def test_ranking_sources_point_at_existing_payloads() -> None:
    app = APP_JS.read_text(encoding="utf-8")
    for key in ("ranking", "rankingModel", "rankingBacktest"):
        match = re.search(rf'{key}:\s*"(data/[^"]+)"', app)
        assert match, f"SOURCES.{key} mancante in app.js"
        assert (Path("public") / match.group(1)).exists(), match.group(1)


def test_opportunita_tab_and_containers_exist() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'data-tab="opportunita"' in html
    assert '<section id="opportunita"' in html
    for container in re.findall(r'getElementById\("([a-z0-9-]+)"\)', _wp5_block()):
        assert f'id="{container}"' in html, f"il renderer cerca #{container}, assente nel markup"


def test_ranking_table_exposes_no_forecast_column() -> None:
    """I campi di previsione sono null per contratto (ADR-036): niente colonne."""
    block = _wp5_block()
    columns = block[block.index("const RANK_COLUMNS"):block.index("];", block.index("const RANK_COLUMNS"))]
    for field in ("probability_outperform", "expected_excess_return", "expected_volatility"):
        assert field not in columns, f"{field} non deve essere una colonna della classifica"


def test_non_predictive_notice_is_always_rendered() -> None:
    """Il banner sta nel flusso della pagina, non dietro un tooltip o un hover."""
    block = _wp5_block()
    assert "banners.appendChild(nonPredictiveBanner(report));" in block
    assert "non_predictive_notice" in block
    css = Path("public/styles.css").read_text(encoding="utf-8")
    banner = css[css.index(".rk-banner {"):css.index(".rk-banner-title")]
    assert "display: none" not in banner
    assert ":hover" not in banner


def test_stale_status_has_its_own_banner() -> None:
    block = _wp5_block()
    assert 'report.status !== "ok"' in block
    assert "Dati non aggiornati, nessun nuovo ranking emesso" in block


def test_missing_payload_falls_back_to_an_empty_state() -> None:
    block = _wp5_block()
    assert "if (!report) {" in block
    assert "Dati non ancora disponibili" in block


def test_ui_language_never_promises_a_forecast() -> None:
    for name, text in (("app.js (blocco WP5)", _wp5_block()), ("index.html", _opportunita_panel())):
        for pattern in FORBIDDEN:
            found = pattern.search(text)
            assert found is None, f"linguaggio vietato in {name}: {found.group(0) if found else ''}"


def test_plain_language_help_covers_the_ranking_jargon() -> None:
    """The most technical tab carries a plain-language layer (user feedback,
    2026-08-28: "leggendo le sezioni spesso non capisco niente"). The glossary
    must define the jargon the table headers actually use, and the box must
    open by saying the page is about US equities, not crypto — the single
    biggest reported confusion."""
    panel = _opportunita_panel()
    assert panel.count('class="plain-help"') == 2, "un box per Opportunità e uno per Modello"
    assert "non di criptovalute" in panel
    for term in ("ETF", "SPY", "Momentum", "Percentile", "volatilità", "Peso",
                 "Brier", "Fuori campione", "Calibrazione"):
        assert term.lower() in panel.lower(), f"glossario senza il termine: {term}"


def test_ui_uses_the_prescribed_wording() -> None:
    block = _wp5_block() + _opportunita_panel()
    for phrase in ("classifica descrittiva", "Probabilità stimata", "non è sufficiente per un segnale"):
        assert phrase.lower() in block.lower(), f"manca la formula prescritta: {phrase}"
