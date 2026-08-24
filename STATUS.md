# STATUS.md

> **Fotografia dello stato corrente.** Non è un diario: la cronaca delle
> sessioni passate vive in [`docs/STATUS_ARCHIVIO.md`](./docs/STATUS_ARCHIVIO.md).
> Chi riprende il lavoro (umano o agente) legge questo file per primo, e tiene
> questo file **sotto le 200 righe**: se cresce, la cronaca si sposta in archivio.

**Ultimo aggiornamento**: 2026-08-24 — sessione WP1 (storage storico partizionato)

---

## Dove siamo

- **Branch di lavoro**: `claude/wp1-storage-qzjjxd` — base `main` = `66c9eae`
  (WP0 mergiato).
- **Test**: 493 passati (`uv run pytest -q`), ruff pulito, pyright pulito sui
  moduli core e su `src/ingestion/news`.
- **Milestone corrente**: **Fase 9 — Ranking ETF probabilistico**, work package
  **WP1** (questa sessione); WP0 chiuso. Il piano operativo è
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

## Crescita del repository (misurata in WP0)

Storia completa, 812 commit su `main`, di cui **676 (83%) commit automatici dei
cron**. Pack: **1,17 GiB**; contenuto blob non compresso: **7 727 MiB** su 2 927 blob.

| Path | Blob distinti | MiB cumulati | % del totale |
|---|---:|---:|---:|
| `data/news_history/news.parquet` | 479 | 7 532,7 | **97,5%** |
| `public/data/events.json` | 473 | 131,5 | 1,7% |
| `data/category_history/categories_history.parquet` | 86 | 24,7 | 0,3% |
| `public/data/market_series.json` | 81 | 16,5 | 0,2% |
| `STATUS.md` | 71 | 2,9 | 0,04% |
| tutto il resto | — | ~19 | 0,2% |

Un solo file spiega il 97,5% del peso: `news.parquet` era riscritto
**integralmente** a ogni run del cron (479 volte dal 2026-05-30), ≈ 26 MB a copia.
Il costo per run **cresceva con la storia**: crescita quadratica nel tempo.

**Risolto in WP1** (ADR-033, D8 confermata): la storia news è partizionata per
mese di pubblicazione (`data/news_history/news_YYYY-MM.parquet`), il cron
riscrive **solo le partizioni toccate** e i mesi passati diventano blob
immutabili. Migrazione one-shot verificata: 50 129 righe, schema e hash per
colonna identici, indice identico; 92 partizioni. La storia git **non** è stata
riscritta — l'1,17 GiB già speso resta, la decisione vale sul futuro.

| Blob riscritto per run del cron | Prima | Dopo | Δ |
|---|---:|---:|---:|
| oggi (24 ago, partizione quasi piena) | 26,66 MB | 6,14 MB | −77,0% |
| media sui prossimi 30 giorni | ~31,4 MB | ~4,0 MB | −87,2% |
| proiezione a 12 mesi (~8 MB/mese) | ~119 MB | ~4 MB | −96,6% |

Il punto non è la percentuale ma la forma: il costo del monolite cresce senza
limite, quello della partizione è **limitato a un mese di news e si azzera ogni
primo del mese**.

## Blocchi e attese

- **U2 — conferma utente su D4 e D7** (`docs/PIANO_SVILUPPO.md` §2): D8
  **risolta** (partizionamento mensile confermato, ADR-033 `Accepted`, WP1
  chiuso). D4 (target primario) e D7 (soglia di confidenza) servono a WP3/WP4 e
  restano da confermare.
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
- **`category_history` NON partizionato** (annotato da WP1, fuori perimetro).
  `categories_history.parquet` ha la stessa dinamica ma pesa lo 0,3% del totale,
  ed è scritto dal `write_snapshot` generico di ADR-022 — condiviso con macro,
  settori, CoinGecko ed Etherscan. Partizionarlo significa cambiare l'API comune
  e i suoi sei call site: non è il "se banale" previsto dal piano. Se un giorno
  quel file diventa un problema, si applica lo stesso schema a `write_snapshot`
  con una ADR dedicata.
- **Verifica live di WP1 rinviata al primo run del cron post-merge**: che il
  workflow riscriva davvero solo la partizione corrente si può osservare solo in
  Actions. Offline è coperto da 14 test.

## Prossime attività

1. **Osservare il primo run del cron `news-history` dopo il merge**: deve
   riscrivere solo `news_2026-08.parquet` (il `git status --porcelain` delle
   partizioni è ora stampato nel log del workflow). È l'unica verifica di WP1
   che non si può fare offline.
2. **WP2** — dataset ETF point-in-time: `SPY` nel registry asset,
   `src/features/etf_dataset.py` (feature causali + target excess return 20/60
   sedute vs SPY), CLI riproducibile.
3. **WP3** — walk-forward **con embargo/purging** (`src/backtest/splits.py` oggi
   non ce l'ha), baseline di ranking, calibrazione, risposta onesta a H1–H3.
4. **WP4/WP5** — paper portfolio settimanale + prediction ledger, poi le viste
   "Opportunità" e "Modello" in dashboard.
5. **Filler non bloccanti**: WP-T (debito typing su `src/execution/`, poi
   ingestion) e WP-N (lint dei notebook).

## Come far girare tutto

```bash
uv sync --frozen
uv run pytest -q                      # 493 test
uv run ruff check src tests
uv run pyright src/backtest src/features src/models
```

I notebook richiedono prima `uv run python -m src.ingestion.tier1.fetch_tier1`
(dati gitignored) e si eseguono con
`cd notebooks && PYTHONPATH=.. uv run jupyter nbconvert --execute --inplace <nb>`.

## Dove sta il resto

- **Cronaca completa delle sessioni 2026-05-28 → 2026-08-24**:
  [`docs/STATUS_ARCHIVIO.md`](./docs/STATUS_ARCHIVIO.md)
- **Piano dei work package**: [`docs/PIANO_SVILUPPO.md`](./docs/PIANO_SVILUPPO.md)
- **Decisioni**: `DECISIONS.md` (ADR-001 → ADR-033) — **ADR-034/035 sono
  riservate** ai WP3/WP6: non usarle per altro
- **Domande aperte**: `OPEN_QUESTIONS.md` · **Fasi**: `ROADMAP.md`
