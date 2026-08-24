# STATUS.md

> **Fotografia dello stato corrente.** Non è un diario: la cronaca delle
> sessioni passate vive in [`docs/STATUS_ARCHIVIO.md`](./docs/STATUS_ARCHIVIO.md).
> Chi riprende il lavoro (umano o agente) legge questo file per primo, e tiene
> questo file **sotto le 200 righe**: se cresce, la cronaca si sposta in archivio.

**Ultimo aggiornamento**: 2026-08-24 — sessione WP2 (dataset ETF point-in-time)

---

## Dove siamo

- **Branch di lavoro**: `claude/wp2-dataset-etf-6m03fa` — base `main` = `66c9eae`
  (WP0 e la PR #52 mergiati).
- **Test**: 507 passati (`uv run pytest -q`), ruff pulito, pyright pulito su
  `src/backtest src/features src/models`.
- **Milestone corrente**: **Fase 9 — Ranking ETF probabilistico**, work package
  **WP2** (questa sessione); WP1 non è ancora partito. Il piano operativo è
  [`docs/PIANO_SVILUPPO.md`](./docs/PIANO_SVILUPPO.md): è il riferimento per tutti
  i WP successivi, con decisioni pre-registrate D1–D12 e ipotesi H1–H3 scritte
  **prima** di qualunque backtest.
- **Fasi 0–8**: chiuse o in accumulo dati (vedi `ROADMAP.md`). Il nucleo di
  ricerca ha già risposto alla domanda predittiva daily: **nessun edge
  direzionale** (dettaglio sotto).

## Workflow (GitHub Actions)

| Workflow | Cadenza | Stato |
|---|---|---|
| `ci.yml` | push/PR | 🟢 verde |
| `news-history.yml` | ogni 3h | 🟢 attivo (ultimo commit bot 2026-08-24) |
| `category-history.yml` | giornaliero | 🟢 attivo (2026-08-24) |
| `sector-history.yml` | giornaliero | 🟢 attivo (2026-08-24) |
| `macro-history.yml` | giornaliero | 🟢 attivo (2026-08-24) |
| `paper-shadow.yml` | giornaliero | 🟢 attivo (2026-08-24) |
| `dca.yml` | giornaliero | ⏳ mergiato con la PR #52, **primo run ancora da osservare** |
| `etf-dataset.yml` | solo manuale | ⏳ aggiunto in WP2, **primo run ancora da fare** |

I cron committano con `[skip ci]`. GitHub schedula con **ritardo variabile** (un
cron delle 07:00 può girare alle 12:36 UTC): fidarsi del timestamp nel report,
non dell'orario nominale.

## Risultati empirici consolidati

Elenco di ciò che è stato **misurato**, non di ciò che si spera. Gli esiti
negativi contano quanto i positivi e restano qui apposta.

- **Nessun edge direzionale daily.** Modelli tecnici e tecnico+macro su BTC in
  walk-forward OOS: accuracy 0.5007 → 0.5060 (n=2249) — dentro il rumore. La
  macro **non** aggiunge potere predittivo a frequenza daily (il segnale CPI vive
  a frequenza mensile). Nessun leakage: un bug avrebbe gonfiato il delta.
- **Il sentiment news (VADER, Layer 1) non anticipa nulla** con i dati attuali.
  Il `corr(news_count, |return|) = +0.32` visto su n=23 è **svanito a n=143**
  (≈ −0.07 a lag 1): artefatto di piccolo campione. Caso di studio permanente su
  quanto costa concludere presto.
- **Il momentum relativo non dà edge cross-sectional** sui 20 ETF settoriali
  (2012→2026): il bucket `strong` ≈ baseline a 5/21 sedute e **fa peggio a 63**
  (−2.1 pp di hit-rate). Con finestre non sovrapposte la differenza svanisce; OOS
  il `strong` resta ultimo a 63g in **entrambe** le metà. L'unico segnale stabile
  è negativo: non inseguire i settori più forti su hold di 3 mesi.
- **È il regime a condizionare, non il momentum.** Forward più alti dopo
  `bear_high_vol` (21g +3%, 63g +7%); il pericolo è `bear_low_vol`. Coerente con
  la Fase 5: il rendimento BTC è fortemente regime-dipendente (Sharpe
  `bull_high_vol` **+2.97** vs `bear_high_vol` **−1.20**) — **la media
  full-sample mescola mondi opposti**. Conoscere il regime però **non** predice:
  accuracy 0.498 → 0.510, nel rumore.
- **La fase di ciclo crypto (halving) condiziona forte** — forward 126g: early
  mediana +23% (hit 0.64), late +18% (hit 0.66), **mid mediana −29% (hit 0.21)**;
  "mid = zona pericolo" è OOS-stabile in direzione. ⚠️ **Descrittivo, non un edge
  provato**: ~1,5–2 cicli di halving = essenzialmente 2 bear (2018, 2022).
- **Piano di accumulo (ADR-030)**: la regola "compra ciò che è più sotto peso"
  non ha edge di **rendimento** (54,5° percentile contro 200 semi casuali) ma ha
  un effetto **reale e OOS-stabile sull'allocazione** (distanza finale dal target
  5,3 pp vs 30,5 pp nella metà OOS). Il momentum come regola di scelta è la
  peggiore (40,5° percentile, *sotto* il caso). La componente "buy-the-dip" era
  96° percentile in-sample e **ultima OOS** → rimossa dal punteggio di default.
- **Fondamentali dei progetti (ADR-031)**: descrivono, non predicono, e non è
  possibile un backtest onesto (storia corta, piena di sopravvissuti). Tre
  trappole codificate: sconosciuto ≠ zero; la tesi monetaria (BTC) è esente
  dall'asse "cattura del valore"; zero commit ≠ progetto morto.
- **Lo screen delle candidate è survivorship-biased per costruzione** e non è
  risolvibile con questi dati: la classifica di oggi contiene solo i sopravvissuti.
  È scritto nel modulo, nel report e nel tab.

## Crescita del repository

Misurata in WP0 e archiviata: storia completa 812 commit su `main`, di cui **676
(83%) automatici dei cron**; pack **1,17 GiB**, contenuto blob non compresso
**7 727 MiB**, di cui **97,5% un solo file** (`data/news_history/news.parquet`,
riscritto integralmente a ogni run). Tabella completa in **ADR-032** e in
[`docs/STATUS_ARCHIVIO.md`](./docs/STATUS_ARCHIVIO.md); è il contesto da citare
nell'**ADR-033** (WP1).

## Cosa ha fatto WP2 (dataset ETF point-in-time)

Il primo pezzo di **codice** della Fase 9: il panel su cui WP3 addestrerà le
baseline. Nessun risultato empirico qui — WP2 costruisce il dataset, non lo interroga.

- **`SPY` nel registry asset** (tier 3): benchmark di D2, gemello *comprabile* di
  `SPX` (un indice non si detiene).
- **`src/features/etf_dataset.py`** (nuovo, funzioni pure, nessuna rete):
  `build_feature_panel` (19 feature causali), `build_targets` (excess return e
  segno a 20/60 sedute vs SPY), `assemble` (join + regime 4-stati per data),
  `coverage_report`, `dataset_metadata`. Long-form `(date, symbol)`.
- **`src/ingestion/tier1/build_etf_dataset.py`**: CLI che scarica i 20
  `SECTOR_ETFS` + SPY da Yahoo dal 2005 e scrive `data/processed/etf_panel.parquet`
  + `etf_panel_meta.json` (gitignored: derivati, ricostruibili dal comando).
- **`etf-dataset.yml`, solo `workflow_dispatch`**: la sandbox non raggiunge Yahoo,
  quindi la validazione live della CLI passa da qui. Non è un cron: il panel non
  si committa, e il runner ricorrente è di WP4.
- **24 test offline**, sintetici e deterministici. Il test che conta è quello di
  **causalità**: ricostruito il panel su una storia troncata a `t`, ogni feature
  fino a `t` è identica a quella del panel completo. Un secondo test verifica il
  contrario sul target (perturbare una barra futura *deve* muovere
  `excess_ret_20`): così il primo non passa per un errore di confronto.

**Semplificazioni dichiarate** (nel docstring del modulo, non nascoste): prezzi
`auto_adjust` ⇒ rendimenti di fatto **total return** (standard per la forza
relativa, ma un quote price-only non li replica); universo = ETF **esistenti
oggi** ⇒ survivorship residuo basso ma non nullo, di direzione ottimistica;
storie corte (XLC 2018, BOTZ/CIBR ~2016, URA 2010, ICLN 2008, ITA 2006) **tenute**
con NaN sulle finestre lunghe, perché escluderle rimodellerebbe l'universo nel
tempo.

**Da sapere alla prossima sessione**:

- `pyright: strict` puro non è raggiungibile su un modulo pandas-heavy: `pandas`
  non ha `py.typed`, quindi in strict *ogni* membro pandas diventa unknown (74
  errori, nessuno imputabile a questo codice; anche i moduli strict esistenti,
  es. `src/ingestion/snapshot.py`, ne portano). Il modulo è `strict` **meno le
  quattro regole** che derivano solo da quella mancanza. Per lo strict pieno
  servirebbe `pandas-stubs` come dip. dev: decisione da ADR, non da WP.
- `outperform_h` è il **segno stretto** dell'excess (1.0 se > 0), NaN dove
  l'excess è NaN: la coda non realizzata è dato mancante, non una perdita. D4
  resta da confermare, ma il dataset espone entrambe le forme (regressiva e
  binaria) a 20 e 60 sedute → WP3 non è bloccato.
- **Fuori perimetro, annotato e non toccato** (§0.2 del piano): `combine_regimes`
  perde la prima barra della serie (il classificatore di volatilità non ha un
  rendimento lì). `assemble` la etichetta `unknown` — corretto, ma è
  un'asimmetria da conoscere.

## Blocchi e attese

- **U2 — conferma utente su D4, D7, D8** (`docs/PIANO_SVILUPPO.md` §2): D8
  (partizionamento mensile dei parquet) blocca l'**implementazione** di WP1;
  l'ADR-033 può nascere `Proposed` senza attendere. D4/D7 servono a WP3/WP4.
- **U3 — D9 (provider e budget LLM)**: WP6 resta **gated**, non si parte.
- **U5 — allowlist `api.llama.fi`**: senza, il tab DCA misura *se* esiste un
  meccanismo di cattura del valore, non *quanto* valga. Il client DefiLlama non è
  stato scritto di proposito (codice HTTP verso un host irraggiungibile non è
  verificabile e si romperebbe nel cron).
- **U4 — `holdings_units` reali in `config/dca_plan.yaml`**: finché è `{}` la
  posizione è **stimata** replicando il piano; report e JSON lo dichiarano.
- **Sandbox con egress-allowlist**: `fc.yahoo.com` (cookie bootstrap di yfinance),
  `api.llama.fi`, `api.tokenterminal.com`, `api.dune.com` **bloccati in locale**,
  funzionanti in CI. Conseguenza operativa: ogni nuovo modulo di fetch si sviluppa
  **fixture-first**, validazione live delegata al workflow.
- **WP7 (azioni)** gated su prerequisiti misurabili (piano §5): nessun codice
  speculativo prima.

## Prossime attività

1. **Far girare `etf-dataset` una volta** (dispatch manuale) e leggere il report
   di copertura nel job summary: è la prima verifica che i 20 ticker + SPY
   scarichino davvero e che le storie corte compaiano dove attese.
2. **WP1** — ADR-033 (`Proposed`) sul partizionamento mensile degli storici, poi
   implementazione **solo dopo l'ok utente su D8**. È l'intervento che ferma la
   crescita da 7,5 GiB di blob riscritti.
3. **WP3** — walk-forward **con embargo/purging** (`src/backtest/splits.py` oggi
   non ce l'ha), baseline di ranking, calibrazione, risposta onesta a H1–H3.
   Parte dal panel di WP2: `build_etf_dataset` è il suo input riproducibile.
4. **WP4/WP5** — paper portfolio settimanale + prediction ledger, poi le viste
   "Opportunità" e "Modello" in dashboard.
5. **Filler non bloccanti**: WP-T (debito typing su `src/execution/`, poi
   ingestion) e WP-N (lint dei notebook).

## Come far girare tutto

```bash
uv sync --frozen
uv run pytest -q                      # 507 test
uv run ruff check src tests
uv run pyright src/backtest src/features src/models
uv run python -m src.ingestion.tier1.build_etf_dataset   # WP2 (richiede Yahoo: in CI)
```

I notebook richiedono prima `uv run python -m src.ingestion.tier1.fetch_tier1`
(dati gitignored) e si eseguono con
`cd notebooks && PYTHONPATH=.. uv run jupyter nbconvert --execute --inplace <nb>`.

## Dove sta il resto

- **Cronaca completa delle sessioni 2026-05-28 → 2026-08-24**:
  [`docs/STATUS_ARCHIVIO.md`](./docs/STATUS_ARCHIVIO.md)
- **Piano dei work package**: [`docs/PIANO_SVILUPPO.md`](./docs/PIANO_SVILUPPO.md)
- **Decisioni**: `DECISIONS.md` (ADR-001 → ADR-032) — **ADR-033/034/035 sono
  riservate** ai WP1/WP3/WP6: non usarle per altro
- **Domande aperte**: `OPEN_QUESTIONS.md` · **Fasi**: `ROADMAP.md`
