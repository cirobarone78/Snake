# STATUS.md

> **Fotografia dello stato corrente.** Non è un diario: la cronaca delle
> sessioni passate vive in [`docs/STATUS_ARCHIVIO.md`](./docs/STATUS_ARCHIVIO.md).
> Chi riprende il lavoro (umano o agente) legge questo file per primo, e tiene
> questo file **sotto le 200 righe**: se cresce, la cronaca si sposta in archivio.

**Ultimo aggiornamento**: 2026-08-24 — WP3 (validazione del ranking): esito **negativo**, registrato

---

## Dove siamo

- **Branch di lavoro**: `claude/wp3-ranking` (PR #58) — base `main` con PR #52,
  WP0, **WP1** (#55) e **WP2** (#56) mergiati. La PR #57 (documentazione) è mergiata.
- **Test**: 566 passati (`uv run pytest -q`), ruff pulito, pyright pulito sui
  moduli core e su `src/ingestion/news`.
- **Milestone corrente**: **Fase 9 — Ranking ETF probabilistico**; WP0/WP1/WP2
  chiusi, **WP3 misurato** (esito sotto, negativo), **il prossimo è WP4**. Il piano operativo è
  [`docs/PIANO_SVILUPPO.md`](./docs/PIANO_SVILUPPO.md): è il riferimento per tutti
  i WP successivi, con decisioni pre-registrate D1–D12 e ipotesi H1–H3 scritte
  **prima** di qualunque backtest.
- **Fasi 0–8**: chiuse o in accumulo dati (`ROADMAP.md`). Il nucleo di ricerca ha
  già risposto alla domanda predittiva daily: **nessun edge direzionale** (sotto).

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
| `etf-dataset.yml` | solo manuale | 🟢 **primo run verde** (21/21 ticker, 93 517 righe) |
| `ranking-backtest.yml` | su push ai modelli | 🟢 attivo (WP3): ricostruisce il panel e rigenera il report |

I cron committano con `[skip ci]`. GitHub schedula con **ritardo variabile** (un
cron delle 07:00 può girare alle 12:36 UTC): fidarsi del timestamp nel report.

## Risultati empirici consolidati

Elenco di ciò che è stato **misurato**, non di ciò che si spera. Gli esiti
negativi contano quanto i positivi e restano qui apposta.

- **Nessun edge di ranking cross-sectional sugli ETF settoriali** (WP3, ADR-034,
  validazione **pre-registrata**: ipotesi committate prima del codice che le
  misura). Walk-forward con embargo, 14 950 previsioni OOS per modello,
  probabilità calibrate isotonic sul solo train. **Barra di adozione NON superata.**
  - Il **momentum relativo 60g è indistinguibile dal caso**: IC Spearman `0,0010`
    (t = 0,08) contro `0,0022` del ranker casuale. H1 passa solo perché formulata
    come `IC > 0` senza magnitudine — lezione registrata in ADR-034: *un'ipotesi
    senza magnitudine è quasi gratis da superare*.
  - **Logistica e ridge mostrano IC ≈ 0,03 (t ≈ 2,5)**, l'unica cosa non-casuale
    del run, ma **non regge**: positiva nella prima metà OOS, svanita o invertita
    nella seconda (a 60 sedute l'IC cambia segno, +0,057 → −0,047).
  - **Le probabilità sono peggio di una costante**: il Brier di *tutti* i modelli
    è sopra la climatologia (0,2501). Il dato più netto è la reliability table:
    dove la logistica predice **0,974** si realizza **0,461**. La calibrazione
    isotonic fit sul train **non trasferisce OOS**.
  - **I costi mangiano il resto**: TMB lordo `ridge` +0,0038 → netto +0,0014
    (−63%), e comunque negativo nella seconda metà.
  - Conferma, ora su base probabilistica e al netto dei costi, del risultato
    descrittivo già noto (bucket `strong` ≈ baseline a 5/21 sedute, **peggio a 63**,
    −2,1 pp di hit-rate): **non inseguire i settori più forti**.
  - **Conseguenza**: WP4 procede col **momentum semplice dichiarato
    non-predittivo**, come §2.1 prescriveva per questo caso. Report:
    [`docs/REPORT_RANKING.md`](./docs/REPORT_RANKING.md).
- **Battere SPY è più difficile di quanto sembri.** Sul panel WP2 (2005→2026,
  20 ETF settoriali) l'outperformance **incondizionata** vs SPY è **0,489 a 20
  sedute** (n=93 117) e **0,482 a 60** (n=92 317): il settore mediano batte SPY
  meno di una volta su due — nel periodo l'S&P cap-weighted è stato trainato
  dalle mega-cap. È la **baseline climatologica** che H2 deve battere in Brier
  score, piantata *prima* di modellare (WP3).

- **Nessun edge direzionale daily.** Modelli tecnici e tecnico+macro su BTC in
  walk-forward OOS: accuracy 0.5007 → 0.5060 (n=2249) — dentro il rumore. La
  macro **non** aggiunge potere predittivo a frequenza daily (il segnale CPI vive
  a frequenza mensile). Nessun leakage: un bug avrebbe gonfiato il delta.
- **Il sentiment news (VADER, Layer 1) non anticipa nulla** con i dati attuali:
  `corr(news_count, |return|) = +0.32` su n=23 è **svanito a n=143** (≈ −0.07 a
  lag 1). Artefatto di piccolo campione, e caso di studio permanente su quanto
  costa concludere presto.
- **È il regime a condizionare, non il momentum.** Forward più alti dopo
  `bear_high_vol` (21g +3%, 63g +7%); il pericolo è `bear_low_vol`. Il rendimento
  BTC è fortemente regime-dipendente (Sharpe `bull_high_vol` **+2.97** vs
  `bear_high_vol` **−1.20**): **la media full-sample mescola mondi opposti**.
  Conoscere il regime però **non** predice: accuracy 0.498 → 0.510, nel rumore.
- **La fase di ciclo crypto (halving) condiziona forte** — forward 126g: early
  mediana +23% (hit 0.64), late +18% (hit 0.66), **mid −29% (hit 0.21)**; "mid =
  zona pericolo" è OOS-stabile in direzione. ⚠️ **Descrittivo, non un edge
  provato**: ~1,5–2 cicli = essenzialmente 2 bear (2018, 2022).
- **Piano di accumulo (ADR-030)**: "compra ciò che è più sotto peso" non ha edge
  di **rendimento** (54,5° percentile su 200 semi casuali) ma ha un effetto
  **reale e OOS-stabile sull'allocazione** (distanza dal target 5,3 pp vs 30,5 pp
  nella metà OOS). Il momentum come regola di scelta è la peggiore (40,5°,
  *sotto* il caso); "buy-the-dip" era 96° in-sample e **ultima OOS** → rimossa.
- **Fondamentali dei progetti (ADR-031)**: descrivono, non predicono; nessun
  backtest onesto è possibile (storia corta, piena di sopravvissuti). Tre trappole
  codificate: sconosciuto ≠ zero; la tesi monetaria (BTC) è esente dall'asse
  "cattura del valore"; zero commit ≠ progetto morto.
- **Lo screen delle candidate è survivorship-biased per costruzione**, non
  risolvibile con questi dati: la classifica di oggi contiene solo i sopravvissuti.
  Dichiarato nel modulo, nel report e nel tab.

## Fase 9 — WP2: dataset ETF point-in-time (fatto)

Il panel su cui WP3 ha addestrato le baseline: `SPY` nel registry (benchmark D2),
`src/features/etf_dataset.py` (19 feature causali, target excess return 20/60
sedute vs SPY, regime 4-stati), CLI `build_etf_dataset`, 24 test offline — il più
importante è quello di **causalità**. Narrativa completa in
[`docs/STATUS_ARCHIVIO.md`](./docs/STATUS_ARCHIVIO.md) e nella PR #56; le
semplificazioni dichiarate sono nel docstring del modulo.

**Validazione live**: 21/21 ticker, **93 517 righe × 27 colonne**, 2005-01-03 →
2026-08-24. Le date di quotazione cadono dove attese (XLC 2018-06-19, BOTZ
2016-09-13, CIBR 2015-07-07, XLRE 2015-10-08, URA 2010-11-05, ICLN 2008-06-25,
ITA 2006-05-05); gli 11 SPDR originali dal 2005-01-03, 5 444 righe. Le feature
mancanti sono solo warm-up: stesse ~1 500 celle NaN in assoluto su ogni simbolo,
cambia solo il denominatore (1,5% storie lunghe, 3,9% XLC).

**Da sapere**: `pyright: strict` puro non è raggiungibile su un modulo
pandas-heavy (`pandas` non ha `py.typed`); i moduli nuovi sono strict **meno le
quattro regole** che ne derivano. Per lo strict pieno servirebbe `pandas-stubs`
come dip. dev — da ADR, non da WP.
## Crescita del repository (risolta in WP1)

Un solo file spiegava il 97,5% del peso (misura WP0, tabella in ADR-032 e in
archivio): `news.parquet` riscritto **integralmente** a ogni run del cron (479
volte dal 2026-05-30), ≈ 26 MB a copia, con costo per run **crescente con la
storia**. **Risolto in WP1** (ADR-033, D8 confermata): partizionamento per mese
(`news_YYYY-MM.parquet`), il cron riscrive **solo le partizioni toccate**, i mesi
passati diventano blob immutabili. Migrazione one-shot verificata: 50 129 righe,
schema/hash per colonna e indice identici, 92 partizioni. La storia git **non** è
stata riscritta: l'1,17 GiB già speso resta, la decisione vale sul futuro.

| Blob riscritto per run del cron | Prima | Dopo | Δ |
|---|---:|---:|---:|
| oggi (24 ago, partizione quasi piena) | 26,66 MB | 6,14 MB | −77,0% |
| media sui prossimi 30 giorni | ~31,4 MB | ~4,0 MB | −87,2% |
| proiezione a 12 mesi (~8 MB/mese) | ~119 MB | ~4 MB | −96,6% |

Il punto non è la percentuale ma la forma: il costo del monolite cresce senza
limite, quello della partizione è **limitato a un mese e si azzera il primo**.

## Blocchi e attese

- **U2 — conferma utente su D4 e D7** (`docs/PIANO_SVILUPPO.md` §2): D8 **risolta**
  (ADR-033 `Accepted`). **D7** (soglia di confidenza) e **D4** servono a WP4 e
  restano da confermare — dopo l'esito di WP3, D7 vale sul fallback momentum.
- **U3 — D9 (provider/budget LLM)**: WP6 resta **gated**.
- **U5 — allowlist `api.llama.fi`**: senza, il tab DCA misura *se* esiste un
  meccanismo di cattura del valore, non *quanto* valga. Il client DefiLlama non è
  stato scritto di proposito: codice verso un host irraggiungibile non è
  verificabile e si romperebbe nel cron.
- **U4 — `holdings_units` reali in `config/dca_plan.yaml`**: finché è `{}` la
  posizione è **stimata**; report e JSON lo dichiarano.
- **Sandbox con egress-allowlist**: `fc.yahoo.com`, `api.llama.fi`,
  `api.tokenterminal.com`, `api.dune.com` **bloccati in locale**, funzionanti in CI
  → ogni nuovo modulo di fetch si sviluppa **fixture-first**, validazione live
  delegata al workflow. WP2 e WP3 ne sono i due casi.
- **WP7 (azioni)** gated su prerequisiti misurabili (piano §5).
- **`category_history` NON partizionato** (annotato da WP1, fuori perimetro): stessa
  dinamica ma 0,3% del totale, e passa dal `write_snapshot` generico di ADR-022,
  condiviso con altri cinque call site. Partizionarlo significa cambiare l'API
  comune: serve una ADR dedicata.
- **Verifica live di WP1** rinviata al primo run del cron post-merge (osservabile
  solo in Actions; offline coperta da 14 test).

## Prossime attività

1. **WP4** — paper portfolio settimanale + **prediction ledger** immutabile, con
   il **momentum semplice** come regola: la barra di WP3 non è stata superata e
   §2.1 prescrive esattamente questo fallback. Servono **D4** e **D7** confermate.
2. **Osservare il primo run del cron `news-history`**: deve riscrivere solo
   `news_2026-08.parquet` (il `git status --porcelain` delle partizioni è ora
   stampato nel log del workflow). È l'unica verifica di WP1 non fattibile offline.
3. **WP5** — viste "Opportunità" e "Modello" in dashboard. Attenzione: dopo WP3
   la vista "Modello" mostra un esito **negativo**, e va disegnata per dirlo
   chiaramente invece di nasconderlo (`public/data/ranking_backtest.json` è pronto).
5. **Filler non bloccanti**: WP-T (debito typing su `src/execution/`, poi
   ingestion) e WP-N (lint dei notebook).

## Come far girare tutto

```bash
uv sync --frozen
uv run pytest -q                      # 566 test
uv run ruff check src tests
uv run pyright src/backtest src/features src/models
uv run python -m src.ingestion.tier1.build_etf_dataset     # panel WP2 (Yahoo: gira in CI)
uv run python -m src.ingestion.tier1.ranking_backtest_cli  # validazione WP3
```

I notebook richiedono prima `fetch_tier1` (dati gitignored) e si eseguono con
`cd notebooks && PYTHONPATH=.. uv run jupyter nbconvert --execute --inplace <nb>`.

## Dove sta il resto

- **Cronaca 2026-05-28 → oggi**: [`docs/STATUS_ARCHIVIO.md`](./docs/STATUS_ARCHIVIO.md)
  · **Piano dei WP**: [`docs/PIANO_SVILUPPO.md`](./docs/PIANO_SVILUPPO.md)
- **Decisioni**: `DECISIONS.md` (ADR-001 → **ADR-034**) — **ADR-035 riservata** a
  WP6, non usarla per altro
- **Domande aperte**: `OPEN_QUESTIONS.md` · **Fasi**: `ROADMAP.md`
