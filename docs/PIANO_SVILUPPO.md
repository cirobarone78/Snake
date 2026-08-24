# Piano operativo — Ranking ETF probabilistico

> Piano di sviluppo derivato dall'handoff di analisi esterna (Codex, 2026-08-24),
> verificato contro lo stato reale del repository e strutturato in **work package
> autonomi** pensati per essere eseguiti da agenti separati (Claude Code / Opus),
> uno per PR, con il minimo di esplorazione ripetuta.
>
> Commissionato dall'utente il 2026-08-24. Questo file è il riferimento operativo;
> le convenzioni di `CLAUDE.md` e le ADR in `DECISIONS.md` prevalgono sempre.

---

## 0. Come usare questo piano (istruzioni per l'agente esecutore)

Sei un agente incaricato di **un solo work package** (WP). Regole vincolanti:

1. **Leggi prima, nell'ordine**: `CLAUDE.md`, poi la sezione di questo file del tuo
   WP (inclusa la §1 "Stato di partenza", la §2 "Decisioni pre-registrate", la §3
   "Mappa componenti" e la §4 "Vincoli d'ambiente"). `STATUS.md` solo la testa
   (prime ~120 righe). **Non** leggere `notebooks/`, `education/`, `uv.lock` né i
   moduli non elencati nel tuo WP: la mappa in §3 è già verificata sulle firme
   reali — fidati di essa e apri un file solo se devi modificarlo o estenderlo.
2. **Perimetro**: implementa i deliverable del tuo WP, tutti e soli. Se scopri un
   problema fuori perimetro, annotalo in `STATUS.md` (sezione della tua sessione)
   e fermati lì.
3. **Un WP = un branch = una PR** (draft), nominata `claude/wp<N>-<slug>`. Base:
   `main` (dopo il merge della PR #52 — vedi §1). Commit message in inglese,
   convenzione `feat:`/`fix:`/`data:`/`docs:` come da storia del repo.
4. **Verifica prima di consegnare** (obbligatoria, nessuna eccezione):
   ```bash
   uv sync --frozen
   uv run ruff check src tests
   uv run pyright src/backtest src/features src/models <tuoi nuovi moduli core>
   uv run pytest -q
   ```
   Ogni nuovo modulo deve essere **pyright-clean dal primo commit**. Se tocchi la
   dashboard: `node -e "new Function(require('fs').readFileSync('public/app.js','utf8'))"`
   e verifica visiva con Playwright (Chromium preinstallato, vedi §4) in tema
   chiaro, scuro e mobile 390px.
5. **A fine WP**: aggiorna `STATUS.md` (cosa fatto / cosa resta / cosa sapere),
   marca il deliverable in `ROADMAP.md`, registra l'eventuale ADR con il numero
   riservato in §5 del tuo WP. Non creare file `.md` non elencati nei deliverable.
6. **Lingue**: codice/commit/log in inglese; documentazione e UI in italiano.
7. **Metodo (non negoziabile, da `CLAUDE.md`)**: ipotesi scritte prima dei
   risultati; mai conclusioni senza out-of-sample; documentare anche ciò che NON
   funziona; nessuna promessa di previsione; nessun trade reale.

**Prompt di lancio suggerito per ogni agente** (l'utente lo incolla, cambiando N):

> Leggi `CLAUDE.md` e poi `docs/PIANO_SVILUPPO.md`: sezioni 1–4 e il work package
> WP<N>. Esegui solo WP<N>, rispettando perimetro, test e criteri di accettazione
> scritti lì. Crea il branch `claude/wp<N>-<slug>` da `main`, apri una PR draft,
> e aggiorna STATUS/ROADMAP/DECISIONS come previsto dal piano.

---

## 1. Stato di partenza verificato (2026-08-24)

### 1.1 Dove siamo davvero

- `main` = `a621f5c` (dopo `edc94a4` analizzato dall'handoff: solo commit dati).
- **PR #52 aperta** (branch `claude/mercato-finanziario-project-g8gc3y`, head
  `103d933`): piano di accumulo crypto (ADR-030) + fondamentali dei progetti
  (ADR-031). CI verde, **483 test** (l'handoff ne riporta 417 perché ha analizzato
  `main` prima della PR).
- Workflow attivi e verdi: `ci`, `category-history`, `macro-history`,
  `news-history`, `paper-shadow`, `sector-history`, più `dca` (nella PR #52).

### 1.2 Correzioni fattuali all'handoff (verificate in sessione)

| Claim handoff | Stato reale |
|---|---|
| 417 test | 483 sul branch della PR #52; usare quel numero come base |
| ADR fino a 029 | ADR-030 e ADR-031 esistono nella PR #52; **il prossimo numero libero è 032** |
| "estendere `conditional_outcomes`" | esiste ed è già OOS-capable (`split_by_date`); riusarlo, non riscriverlo |
| walk-forward esistente | `walk_forward_splits` c'è ma **non ha embargo/purging**: va aggiunto (WP3) |
| benchmark SPY | **SPY non esiste** nel registry asset; c'è `SPX` (`^GSPC`, indice). SPY va aggiunto (WP2) |

### 1.3 Prerequisito P0 (azione dell'utente, blocca tutto il resto)

**Merge della PR #52.** I WP di questo piano partono da `main` post-merge: la PR
tocca `STATUS.md`, `DECISIONS.md`, `ROADMAP.md`, `OPEN_QUESTIONS.md`, `public/` —
partire prima del merge garantisce conflitti su ogni WP. Se l'utente decide di NON
mergiarla, va detto esplicitamente all'agente di WP0, che baserà su `main` e
rinumererà le ADR (032→030 ecc.).

---

## 2. Decisioni pre-registrate

Adottate come **default operativi** (dall'handoff §19, confermati come ragionevoli
dall'analisi del repo). L'utente può cambiarle **finché il WP che le usa non è
partito**; dopo, cambiarle significa rifare il WP. Nessun agente deve riaprirle in
autonomia.

| # | Decisione | Default adottato | Usata da | Conferma utente |
|---|---|---|---|---|
| D1 | Universo | i 20 ETF di `SECTOR_ETFS` (XLK XLE XLF XLV XLI XLU XLP XLY XLB XLRE XLC SMH URA ICLN XOP ITA BOTZ CIBR XBI GDX) | WP2 | consigliata |
| D2 | Benchmark | **SPY** (nuovo `Asset`, ETF, yahoo `SPY`) | WP2 | consigliata |
| D3 | Orizzonte primario | **20 sedute** (secondario 60) | WP2-3 | consigliata |
| D4 | Target primario | `P(excess_return > 0)` a 20 sedute (secondari: excess return regressivo, top-quintile) | WP3 | **richiesta** |
| D5 | Frequenza decisione | settimanale, lunedì pre-apertura (cron 07:00 UTC lun) | WP4 | consigliata |
| D6 | Portafoglio paper | top 5 equal-weight, cap 20%/asset, fill t+1, costi `default_cost_model()` | WP4 | consigliata |
| D7 | Soglia di confidenza | nessun acquisto se `P(outperform) < 0.55` per il 5° classificato → si resta in liquidità parziale | WP4 | **richiesta** |
| D8 | Storage storico | partizionamento mensile dei parquet in-repo (dettaglio WP1); storage esterno rinviato | WP1 | **richiesta** |
| D9 | LLM per event extraction | **non deciso** — WP6 è bloccato finché l'utente non conferma budget e provider (rif. Q19/ADR-021) | WP6 | **richiesta** |
| D10 | Rename repository | fuori scope di questo piano (non prerequisito) | — | — |
| D11 | Dipendenze | nessuna nuova dipendenza per WP0-5: logistica/ridge/isotonic sono già in scikit-learn (in `pyproject.toml`). Boosting (LightGBM) solo con ADR dedicata dopo che le baseline sono stabili | tutti | — |
| D12 | Macro point-in-time | in M1/M2 il condizionamento è **solo da prezzi** (regime SPX trend×vol, già causale). Le serie FRED entrano solo in fase 2 con regola di ritardo pubblicazione ≥45gg, mai col valore revisionato alla data di riferimento | WP2-3 | consigliata |

### 2.1 Ipotesi pre-registrate per WP3 (scritte ORA, prima di qualunque risultato)

Registrate qui per vincolo metodologico (`CLAUDE.md`: le ipotesi si scrivono
prima). L'agente di WP3 le copia **verbatim** nell'ADR-034 prima di eseguire il
primo backtest. I pali non si spostano post-hoc (precedente: nb 12 / FinBERT).

- **H1**: il ranking per momentum relativo 60gg ha IC di Spearman medio OOS > 0
  a 20 sedute sull'universo D1.
- **H2**: la logistica regolarizzata sulle feature di WP2 batte il momentum puro
  in Brier score OOS (probabilità calibrate su train con isotonic).
- **H3**: lo spread top-quintile − bottom-quintile, **al netto dei costi** D6, è
  positivo in *entrambe* le metà temporali dell'OOS.
- **Metrica primaria**: Brier score vs baseline climatologica (frequenza storica
  di outperformance nel train) + IC Spearman. Le altre metriche (§WP3) sono
  diagnostiche.
- **Barra di adozione** (il modello entra nel paper portfolio di WP4 solo se):
  IC Spearman medio OOS ≥ 0.03 **e** H3 vera **e** Brier ≤ baseline
  climatologica. Altrimenti WP4 procede con il **momentum semplice** come regola
  dichiaratamente non-predittiva (il ledger e l'infrastruttura valgono comunque)
  e l'esito negativo viene documentato in STATUS/ADR come da convenzione.

---

## 3. Mappa dei componenti riutilizzabili (firme verificate il 2026-08-24)

Questa mappa è stata verificata leggendo i sorgenti. **Non ri-esplorare**: usa i
moduli così, apri il file solo se lo estendi.

### Dati e asset
| Componente | Cosa offre | Usato da |
|---|---|---|
| `src/assets/sectors.py` — `SECTOR_ETFS`, `get_sector_by_symbol(symbol)` | i 20 ETF (D1) come `Asset` con `yahoo_symbol` | WP2 |
| `src/assets/asset.py` — `Asset`, `TIER1_ASSETS`, `CONTEXT_ASSETS`, `get_asset_by_symbol` | modello pydantic; `SPX` = `^GSPC` è tra i context | WP2 (aggiunge SPY) |
| `src/ingestion/tier1/yahoo_finance.py` — `YahooFinanceSource.fetch_ohlcv(asset, start, end=None, interval="1d") -> DataFrame` | OHLCV daily, indice UTC tz-aware, colonne `open high low close volume`, `auto_adjust=True` | WP2, WP4 |
| `src/ingestion/freshness.py` — `check_freshness(...) -> FreshnessResult` (campi: `name,last_timestamp,age_days,max_age_days,is_fresh`; metodo `message()`) | guardia anti-feed-congelato. ⚠️ **Non ha `.reason`** — un bug reale è già nato da questa assunzione | WP2, WP4 |
| `src/ingestion/snapshot.py` — `write_snapshot` | pattern latest+history (ADR-022) | WP1 |

### Feature e regime
| Componente | Cosa offre | Usato da |
|---|---|---|
| `src/features/regime.py` — `classify_regime(prices, window=200)`, `classify_vol_regime(...)`, `combine_regimes(trend, vol)` | regime bull/bear × vol da soli prezzi (causale → ok point-in-time) | WP2 |
| `src/features/indicators.py` | SMA/EMA/RSI/ATR ecc. | WP2 |
| `src/features/conditional_outcomes.py` — `forward_return(close, horizon)`, `momentum(close, lookback)`, `rotation_observations(...)`, `conditional_outcome_table(...)`, `split_by_date(...)` | forward return causale, bucket cross-sectional, check OOS | WP2, WP3 |
| `src/features/sector_screener.py` — `build_sector_frame(...)`, `screen_sectors(frame, top_n)` | snapshot momentum 5/21gg (resta separato: descrive l'oggi, non predice) | — |
| `src/features/report_json.py` — `iso_timestamp`, `write_report_json` | scrittura payload dashboard | WP4, WP5 |

### Backtest e modelli
| Componente | Cosa offre | Usato da |
|---|---|---|
| `src/backtest/splits.py` — `Split(train_slice, test_slice)`, `walk_forward_splits(n_samples, train_size, test_size, step=None, *, expanding=False)` | fold walk-forward. **Manca embargo**: WP3 aggiunge il parametro senza rompere i 9 test esistenti | WP3 |
| `src/backtest/costs.py` — `FeeModel`, `SlippageModel`, `TransactionCostModel.cost(...)`, `estimate_half_spread_bps` | modello costi completo | WP3, WP4 |
| `src/backtest/metrics.py` — `sharpe_ratio, sortino_ratio, max_drawdown, calmar_ratio, hit_rate, equity_curve, ...` | metriche di portafoglio | WP3, WP4 |
| `src/backtest/benchmark.py` — `buy_and_hold_equity`, `dca_equity` | benchmark passivi | WP3 |
| `src/models/baseline.py` — `momentum_forecast`, `random_walk_forecast`, `directional_accuracy`, `strategy_returns` | baseline single-asset (il ranking cross-sectional è nuovo: WP3) | WP3 |
| `src/models/multifactor.py` — `fit_predict_walk_forward(...)`, `WalkForwardResult` | pattern fit/predict per-fold da imitare | WP3 |

### Esecuzione (paper)
| Componente | Cosa offre | Usato da |
|---|---|---|
| `src/execution/orders.py` — `Order`, `Side`, `OrderType`, `OrderStatus` (+`to_record/from_record`) | ordini serializzabili | WP4 |
| `src/execution/paper_broker.py` — `PaperBroker(...).submit/process_bar/qty_for_cash_fraction`, `Bar`, `default_cost_model()` | fill t+1 con costi | WP4 |
| `src/execution/portfolio.py` — `Portfolio.apply_buy/apply_sell/equity/to_record` | stato posizioni | WP4 |
| `src/execution/scenarios.py` — `ScenarioStore.create/load/save/append_orders/orders/reset/fork` (persistenza `data/paper/`, ADR-029) | scenari versionati in git, append-only | WP4 |
| `src/execution/live_shadow.py` — `run_daily(...)` + workflow `paper-shadow.yml` | **modello da imitare** per il runner settimanale ETF | WP4 |

### Dashboard
`public/index.html` (tab statici) + `public/app.js` (vanilla JS, un renderer per
payload, `fetchJSON`, formatter `NF/NF0/NF1/NF2/EUR0`, `el()` helper) +
`public/styles.css` (variabili tema, light/dark automatico). Pattern da seguire:
un file JSON per vista sotto `public/data/`, renderer isolato, empty-state
esplicito ("Dati non ancora disponibili…"). Il worker Cloudflare serve `public/`
(`wrangler.toml`, SPA fallback).

---

## 4. Vincoli d'ambiente per gli agenti (leggere: fa risparmiare ore)

1. **La sandbox di sviluppo ha una egress-allowlist**; GitHub Actions no. Verificato
   in sessione: `fc.yahoo.com` (bootstrap cookie di yfinance) **bloccato** in
   sandbox → `YahooFinanceSource` può fallire localmente ma **funziona in CI**
   (i cron lo provano ogni giorno). `api.llama.fi`, `api.tokenterminal.com`,
   `api.dune.com` bloccati in sandbox. `query1.finance.yahoo.com` diretto,
   `api.coingecko.com`, `api.github.com`, `api.stlouisfed.org` raggiungibili.
2. **Conseguenza operativa**: ogni modulo di fetch nuovo si sviluppa
   **fixture-first** — test offline con payload sintetici (convenzione già usata:
   vedi `tests/test_coingecko.py`), validazione live delegata al workflow
   (`workflow_dispatch` per il primo run). Non scrivere client HTTP verso host
   mai osservati: farsi dare un payload reale dall'utente o dal workflow.
3. **Screenshot**: Chromium è in `/opt/pw-browsers/chromium`; installare
   playwright via npm nella scratchpad e passare `executablePath`. Non eseguire
   `playwright install`.
4. **Yahoo in locale**: per lavorare offline sui prezzi si può usare l'endpoint
   chart diretto (`query1.finance.yahoo.com/v8/finance/chart/<TICKER>`) con
   User-Agent browser, cache su parquet in scratchpad. Non committare dataset
   grossi (>10MB) nel repo (`CLAUDE.md`).
5. **Verifica firme prima dell'uso**: il costo di un `grep -n "def "` è nulla; il
   costo di un attributo inventato è una PR rossa (caso reale: `.reason` su
   `FreshnessResult`).

---

## 5. Work packages

Dipendenze:

```text
P0 (merge PR #52, utente)
 └─ WP0 ── WP1 (parallelo a WP2 dopo ADR-033)
      └─ WP2 ── WP3 ── WP4 ── WP5
                              └─ (WP6 gated D9) ── (WP7 gated, prerequisiti)
 WP-T, WP-N: filler paralleli, mai bloccanti
```

---

### WP0 — Riconciliazione, fotografia e ADR di direzione

**Obiettivo**: allineare i file di stato alla realtà, misurare la crescita del
repo, registrare la direzione di prodotto. Nessun codice nuovo.

**File da leggere**: `CLAUDE.md`, `STATUS.md` (integrale, una tantum: è il WP che
lo comprime), `ROADMAP.md`, `DECISIONS.md` (solo indice `grep "^## ADR"`),
`README.md`.

**Deliverable**
1. `STATUS.md` ridotto a: commit/branch corrente, stato workflow, milestone
   corrente, risultati empirici consolidati (in forma di elenco puntato, non
   cronaca), blocchi, prossime 3-5 attività, data. La cronologia delle sessioni
   viene spostata in `docs/STATUS_ARCHIVIO.md` (consenso: la creazione di questo
   file è autorizzata da questo piano, commissionato dall'utente). Target:
   `STATUS.md` sotto le 200 righe.
2. Misura della crescita git: `git rev-list --objects --all | ...` oppure
   `git count-objects -vH` + top-10 blob per dimensione cumulata; risultato in
   una tabella dentro l'ADR-033 (vedi WP1) come contesto.
3. **ADR-032 — "Direzione di prodotto: market intelligence probabilistica"**:
   registra la decisione (già presa dall'utente commissionando questo piano) di
   sviluppare il ranking ETF cross-sectional con probabilità calibrate come primo
   prodotto predittivo, con le decisioni D1-D7 e le ipotesi §2.1 in allegato.
   Stato: Accepted.
4. README: paragrafo iniziale che chiarisce che il repo non è un gioco Snake e
   una riga che punta a questo piano.
5. `ROADMAP.md`: nuova sezione "Fase 9 — Ranking ETF probabilistico" con i WP di
   questo piano come deliverable (checkbox), e rimando a `docs/PIANO_SVILUPPO.md`.

**Non fare**: riscrivere la storia git; rinominare il repo; toccare `src/`.

**Accettazione**: CI verde; `STATUS.md` < 200 righe; nessuna informazione persa
(tutto ciò che viene tolto è in `docs/STATUS_ARCHIVIO.md`); ADR-032 registrata.
**Stima**: PR piccola, solo Markdown. Mezza giornata-agente.

---

### WP1 — Contenere la crescita del repository (storage dei dati storici)

**Obiettivo**: fermare la crescita da riscrittura di blob binari **senza** storage
esterno, senza riscrittura della storia e senza toccare la raccolta dati.

**Contesto misurato**: `data/news_history/news.parquet` ≈ 26,6MB riscritto dal
cron ogni 3 ore → ogni commit salva un blob nuovo quasi-integrale. È la causa
principale del ~1,24GB. `category_history` (~0,6MB) e gli altri parquet sono
minori ma stessa dinamica.

**File da leggere**: `src/ingestion/news/persist.py`, `history.py`,
`update_history.py`, `src/ingestion/snapshot.py`, workflow `news-history.yml`,
`tests/test_news_history.py`, `tests/test_news_persist.py`.

**Deliverable**
1. **ADR-033 — "Storage storico: partizionamento mensile in-repo"**. Decisione
   proposta (default D8): partizionare gli accumulatori per mese —
   `data/news_history/news_2026-08.parquet` ecc. Il cron riscrive **solo il file
   del mese corrente** (≤ ~1/12 del blob attuale in media, e i mesi passati
   diventano blob immutabili che git non riscrive mai più). Nell'ADR:
   la tabella di crescita misurata in WP0, le alternative valutate (R2, LFS,
   release artifact, DB esterno — dall'handoff §4.1) e perché sono rinviate
   (costo/complessità non giustificati finché il partizionamento basta).
   **La scelta finale è dell'utente (D8): l'ADR va in stato Proposed e diventa
   Accepted solo dopo il suo ok.**
2. Implementazione (dopo l'ok): lettura trasparente multi-partizione
   (`read_news_history()` concatena i mesi; API invariata per i consumatori),
   scrittura sul solo mese corrente, migrazione one-shot del parquet monolitico
   in partizioni (i vecchi blob restano nella storia: nessuna riscrittura).
3. Stesso pattern, se banale, per `categories_history`; altrimenti annotare e
   fermarsi (perimetro).
4. Aggiornare `news-history.yml` per committare solo la partizione corrente.

**Test richiesti**: lettura multi-partizione ≡ lettura monolitica (fixture con 2
mesi sintetici); append idempotente sul mese corrente; mese nuovo → file nuovo;
migrazione preserva righe e schema (round-trip count + hash colonne).

**Accettazione**: CI verde; cron news verde al primo run post-merge; dimensione
del blob riscritto per run ridotta di ≥80% (misurata e riportata in PR).
**Stima**: PR media. 1 giornata-agente.

---

### WP2 — Dataset ETF point-in-time (Milestone 1 dell'handoff)

**Obiettivo**: panel giornaliero ETF × feature, causale, con target di excess
return vs SPY a 20/60 sedute, riproducibile da CLI.

**File da leggere**: §3 di questo piano; `src/assets/sectors.py`;
`src/features/conditional_outcomes.py` (docstring e `forward_return`/`momentum`);
`src/features/regime.py`; `src/ingestion/tier1/yahoo_finance.py`;
`src/ingestion/tier1/fetch_sectors.py` (pattern CLI); `tests/test_conditional_outcomes.py`
(stile test causalità).

**Deliverable**
1. **`src/assets/asset.py`**: aggiungere `SPY` (AssetClass.ETF, calendario NYSE,
   `yahoo_symbol="SPY"`, tier=3/context, nota "benchmark del ranking ETF, D2").
2. **`src/features/etf_dataset.py`** (nuovo, pyright strict). Funzioni pure:
   - `build_feature_panel(closes: pd.DataFrame, volumes: pd.DataFrame | None, benchmark: pd.Series) -> pd.DataFrame`
     → long-form `(date, symbol)` multi-index o colonne `date,symbol,<feature...>`.
   - `build_targets(closes, benchmark, horizons=(20, 60)) -> pd.DataFrame`
     → `excess_ret_20`, `outperform_20`, `excess_ret_60`, `outperform_60`
     (shiftati in avanti: valore a `t` = esito realizzato in `(t, t+h]`; NaN sul
     tail non realizzato, mai riempito).
   - `assemble(features, targets, regime: pd.Series) -> pd.DataFrame` con colonna
     `regime` (da `combine_regimes` su SPY/SPX) e metadati.
3. **Feature fase 1** (tutte causali, formule esplicite; niente altro senza ADR):
   - `ret_5`, `ret_20`, `ret_60`, `ret_126`, `ret_252`: `close[t]/close[t-k] - 1`
   - `rel_ret_20`, `rel_ret_60`, `rel_ret_126`: `ret_k(asset) − ret_k(SPY)`
   - `vol_20`, `vol_60`: std dei rendimenti daily × √252
   - `downside_vol_60`: std dei soli rendimenti negativi × √252
   - `dist_sma50`, `dist_sma200`: `close/SMA − 1`
   - `dist_52w_high`: `close/max(close, 252) − 1`
   - `drawdown`: `close/cummax(close) − 1`
   - `beta_60`, `corr_60`: rolling OLS/corr dei rendimenti vs SPY
   - `volume_z20`: z-score del volume su 20gg (se il volume c'è; altrimenti NaN)
   - cross-sectional: `rank_rel_ret_60` (percentile nel giorno, stile
     `_rank_pct` già usato negli screener)
4. **CLI `src/ingestion/tier1/build_etf_dataset.py`**: fetch Yahoo dei 20 ETF +
   SPY dal 2005-01-01 (o dal listing: ITA 2006, XLC 2018, BOTZ/CIBR ~2016, URA
   2010, ICLN 2008 — gestire storie corte con NaN, non escludere), guardia
   freshness, build, scrittura `data/processed/etf_panel.parquet` (**gitignored**)
   + `data/processed/etf_panel_meta.json` (gitignored: righe, range date, feature
   list, hash schema, versione). Stampare report copertura/missing per simbolo.
5. Documentare nel docstring del modulo le due semplificazioni note:
   (a) prezzi adjusted (auto_adjust) ⇒ rendimenti ~total-return, standard ma va
   detto; (b) universo = ETF **oggi** esistenti ⇒ survivorship residuo basso (gli
   ETF settoriali SPDR esistono dal 1998) ma dichiarato.

**Test richiesti** (`tests/test_etf_dataset.py`, sintetici, offline):
1. causalità: aggiungere barre dopo `t` non cambia nessuna feature a `t`
   (pattern del test già in `test_conditional_outcomes`);
2. target shiftato: `outperform_20[t]` calcolato con `close[t+20]`, NaN sul tail;
3. excess: asset ≡ benchmark ⇒ excess = 0, outperform = 0;
4. storie corte: ETF con 100 barre → NaN su `ret_252`, riga non droppata;
5. allineamento: date non comuni tra asset e benchmark → inner join dichiarato;
6. `rank_rel_ret_60` ∈ [0,1] e neutro a 0.5 con universo degenere;
7. regime attaccato per data, `unknown` dove manca;
8. determinismo: due build sullo stesso input → frame identici;
9. tz: indice UTC in ingresso e in uscita.

**Non fare**: niente macro FRED (D12); niente feature oltre la lista (ablation
prima di aggiungere); niente fetch nel modulo feature (solo nel CLI).

**Accettazione**: CI verde; CLI riproducibile; report copertura in PR; pyright
strict pulito sul modulo nuovo.
**Stima**: PR media-grande. 1-2 giornate-agente.

---

### WP3 — Baseline di ranking, validazione e calibrazione (Milestone 2)

**Obiettivo**: confrontare le baseline pre-registrate in walk-forward con
embargo, produrre probabilità calibrate, rispondere onestamente a H1-H3 (§2.1).

**File da leggere**: §2.1; `src/features/etf_dataset.py` (da WP2);
`src/backtest/splits.py` + `tests/test_splits.py`; `src/models/multifactor.py`
(pattern per-fold); `src/backtest/costs.py`, `metrics.py`.

**Deliverable**
1. **`src/backtest/splits.py`**: parametro `embargo: int = 0` in
   `walk_forward_splits` — il test di ogni fold inizia `embargo` osservazioni
   dopo la fine del train (per target a h giorni: `embargo = h`). I 9 test
   esistenti restano verdi; aggiungerne per l'embargo.
2. **`src/models/etf_ranker.py`** (nuovo, strict): interfaccia unica
   `RankerModel` con `fit(X, y)` / `predict_proba(X)` / `rank(X)` e tre
   implementazioni: `MomentumRanker` (rank su `rel_ret_60`, nessun fit),
   `LogisticRanker` (sklearn `LogisticRegression` L2, feature standardizzate sul
   train), `RidgeRanker` (excess return → rank). Più `RandomRanker(seed)` e
   `ClimatologyBaseline` (frequenza train di outperformance) come controlli.
3. **`src/models/calibration.py`** (nuovo, strict): wrapper isotonic
   (`sklearn.isotonic.IsotonicRegression`) **fit solo su train**, `calibrate(p)`;
   + funzioni `brier_score(p, y)`, `reliability_table(p, y, bins=10)`,
   `expected_calibration_error(p, y)`.
4. **`src/backtest/ranking_metrics.py`** (nuovo): `information_coefficient`
   (Pearson e Spearman, per data poi mediati), `top_minus_bottom(returns, ranks, q=0.2, costs=...)`,
   `hit_rate_outperform`. Riusare `metrics.py` per Sharpe/DD del TMB.
5. **Runner `src/ingestion/tier1/ranking_backtest_cli.py`**: carica il panel di
   WP2, esegue le baseline su fold walk-forward settimanali (campionamento del
   panel al lunedì; `embargo = horizon`), calibra, valuta, e scrive:
   - `docs/REPORT_RANKING.md` (autorizzato da questo piano): tabella per modello ×
     orizzonte × metà OOS; reliability table; verdetto esplicito su H1/H2/H3 e
     barra di adozione; sezione "cosa NON ha funzionato".
   - `public/data/ranking_backtest.json` (per la vista modello di WP5).
6. **ADR-034 — "Ranking ETF: esito della validazione pre-registrata"**: ipotesi
   §2.1 copiate verbatim PRIMA del run (commit separato, così il timestamp git
   prova la pre-registrazione), poi esito. Qualunque esso sia.

**Test richiesti**: embargo rispettato (nessun indice train entro h dal test);
probabilità ∈ [0,1]; calibrazione fit solo su train (test: cambiare il test set
non cambia il calibratore); IC di un ranking perfetto = 1, di uno invertito = −1;
TMB con costi < TMB senza costi; determinismo con seed; `ClimatologyBaseline`
restituisce la frequenza train.

**Non fare**: boosting/deep learning (D11); tuning iterativo sullo stesso test
(ogni variante provata va elencata nel report, anche fallita); non dichiarare
edge senza entrambe le metà OOS.

**Accettazione**: CI verde; ADR-034 con ipotesi committate prima dei risultati
(due commit distinti); report riproducibile con un comando.
**Stima**: PR grande. 2 giornate-agente.

---

### WP4 — Paper portfolio settimanale + prediction ledger (Milestone 3)

**Obiettivo**: trasformare il ranking (o il fallback momentum, secondo la barra
§2.1) in un portafoglio simulato con registro immutabile delle previsioni.

**File da leggere**: `src/execution/live_shadow.py` + `paper-shadow.yml` (è il
modello da imitare); `src/execution/scenarios.py`; esito ADR-034.

**Deliverable**
1. **`src/execution/prediction_ledger.py`** (nuovo, strict): JSONL append-only
   `data/predictions/etf_ranking.jsonl` (versionato: righe piccole, git-friendly).
   Schema riga (da handoff §15, contratto stabile — pydantic):
   ```json
   {"emitted_at": "...", "data_cutoff": "...", "model_version": "...",
    "dataset_version": "...", "asset": "SMH", "benchmark": "SPY",
    "horizon_days": 20, "probability_outperform": 0.61,
    "expected_excess_return": 0.018, "expected_volatility": 0.24,
    "regime": "bull_high_vol", "confidence": "medium",
    "top_factors": [{"name": "rel_ret_60", "direction": "positive"}],
    "outcome": null}
   ```
   API: `append(predictions)` (idempotente per `(emitted_at, asset, horizon)`),
   `backfill_outcomes(prices)` — aggiunge l'esito **solo** quando l'orizzonte è
   maturato, riga nuova o campo aggiornato una sola volta, mai riscrittura del
   passato (test dedicato).
2. **`src/execution/etf_rotation.py`** (nuovo): logica settimanale — dal ranking
   ai target weights (D6: top-5 equal weight, cap 20%, soglia D7, liquidità se
   sotto soglia) → ordini per `PaperBroker` con fill alla barra successiva.
   Scenario `ScenarioStore` dedicato: `etf_top5` (capitale simulato 10k).
3. **CLI `src/ingestion/tier1/etf_ranking_cli.py`**: fetch → panel (WP2) →
   predizione col modello adottato → append ledger → ordini scenario → payload
   `public/data/ranking_report.json` (vista Opportunità, contratto in WP5) +
   `public/data/ranking_model.json` (metriche correnti, versione, freshness).
   Fail-safe: dati stale (freshness) o calibrazione più vecchia di N settimane ⇒
   il payload esce con `status: "stale"` e il portafoglio NON viene ribilanciato.
4. **Workflow `.github/workflows/etf-ranking.yml`**: lunedì 07:00 UTC +
   `workflow_dispatch`; committa ledger, scenario e i due JSON (pattern identico
   a `sector-history.yml`).
5. Benchmark automatici nel report: SPY buy&hold ed equal-weight dell'universo
   (riusare `benchmark.py`).

**Test richiesti**: ledger append idempotente; outcome mai retroattivo (una riga
emessa non cambia dopo il backfill se non nel campo `outcome`, una volta sola);
fill sempre a timestamp > emissione; cap 20% e soglia D7 rispettati; scenario
rerun-idempotente (secondo run stesso input ⇒ zero ordini nuovi); costi applicati
una sola volta; payload validato contro il contratto (schema test).

**Accettazione**: CI verde; primo run via `workflow_dispatch` verde; ledger e
scenario visibili in git; nessuna previsione retrodatata.
**Stima**: PR grande. 2 giornate-agente.

---

### WP5 — Dashboard: vista Opportunità e vista Modello

**Obiettivo**: comunicare probabilità e incertezza. Niente "compra ora".

**File da leggere**: `public/app.js` (solo: `SOURCES`, `init`, un renderer come
esempio, gli helper), `public/index.html`, `public/styles.css` (variabili tema),
contratti JSON di WP4.

**Deliverable**
1. Tab **"Opportunità"**: tabella ordinabile (ETF, P(outperform) 20/60gg, excess
   atteso, vol attesa, regime, confidenza, freshness, top factors). Ogni riga
   espandibile: distribuzione storica in condizioni simili (da
   `conditional_outcomes`), previsioni passate con esito (dal ledger), caveat.
   Empty/stale state espliciti (`status: "stale"` ⇒ banner "dati non aggiornati,
   nessun nuovo ranking emesso").
2. Sezione **"Modello"** (nello stesso tab o in "Metodo e limiti"): periodo di
   training, ultimo retraining, metriche OOS per metà e per regime, reliability
   chart (SVG inline, pattern sparkline esistente), differenza dichiarata tra
   backtest / paper forward, verdetto ADR-034 riportato testualmente.
3. Linguaggio (vincolante, handoff §12): "probabilità stimata", "storicamente in
   condizioni simili", "confidenza bassa/media/alta", "non sufficiente per un
   segnale". Vietato: "compra", "salirà", "previsto con precisione".
4. Il disclaimer educativo esistente resta su ogni payload.

**Test/verifica**: JS sintassi (`new Function(...)`); screenshot Playwright
light/dark/mobile 390px allegati alla PR; payload mancante ⇒ empty state, mai
crash; nessun testo inglese nella UI.
**Stima**: PR media. 1 giornata-agente.

---

### WP6 — Event intelligence (GATED: non partire senza D9)

Bloccato finché l'utente non decide provider/budget LLM (D9, rif. Q19). Quando
sbloccato: tassonomia eventi (handoff §7.4, schema già definito lì), gold set
manuale ~100 eventi etichettati, estrazione strutturata con audit
(fonte+timestamp+hash+versione prompt), precision/recall misurate sul gold set,
poi ablation con/senza eventi sul modello di WP3. **ADR-035** per la decisione.
Un LLM non produce mai numeri di segnale (solo estrazione/classificazione).

### WP7 — Estensione alle azioni (GATED)

Prerequisiti (tutti, verificabili): pipeline ETF stabile da ≥8 settimane di run
settimanali; WP1 approvato e attivo; provider fondamentali point-in-time scelto
e pagato (decisione utente); universe policy con delisting approvata. Fino ad
allora: non creare cartelle, non scrivere codice speculativo (`CLAUDE.md`).

### WP-T — Debito typing (filler, parallelo, spezzabile)

Ordine (handoff §4.3): `src/execution/` → nuovi moduli (già strict per regola §0)
→ `src/ingestion/` provider usati dalla pipeline → test. Una tranche = una PR
piccola. Niente `# type: ignore` generici, niente `Any` gratuiti; cast mirati con
motivazione. Obiettivo finale: promuovere la cartella nel gate bloccante di
`ci.yml` quando arriva a zero errori.

### WP-N — Notebook lint (filler, opzionale)

`ruff check notebooks/` non bloccante in CI (step `|| true`), pulizia meccanica
dei 31 rilievi senza alterare output embedded, estrazione in `src/` delle
funzioni riusate da più notebook. Bassa priorità: farlo solo se un agente è in
attesa di review.

---

## 6. Cosa NON fare (globale — dall'handoff §17, tutto confermato)

Riscrivere da zero; deep learning; decine di provider; migliaia di azioni subito;
ottimizzare guardando ripetutamente lo stesso test set; LLM come generatore del
segnale numerico; rimuovere il paper trading esistente; riscrivere la storia git;
broker reali; dichiarare edge da un singolo backtest. In più, da questa sessione:
inventare firme non verificate; committare parquet >10MB; fetch code senza
fixture.

---

## 7. Azioni in capo all'utente (nessun agente può farle)

| # | Azione | Blocca |
|---|---|---|
| U1 | **Merge PR #52** (o dichiarare che non si merge) | tutti i WP |
| U2 | Confermare/emendare D4, D7, D8 (§2) — le altre D valgono come default | WP1, WP3, WP4 |
| U3 | Decidere D9 (LLM per eventi: provider e budget mensile) | WP6 |
| U4 | (dal lavoro precedente) `holdings_units` reali in `config/dca_plan.yaml` | nulla, ma migliora il tab DCA |
| U5 | (dal lavoro precedente) allowlist `api.llama.fi` nell'ambiente | ricavi di protocollo nel tab DCA |
| U6 | Eventuale rename repo (D10) — non prerequisito | nulla |

---

## 8. Checklist di consegna per ogni PR (copiarla nella descrizione)

- [ ] Perimetro = il WP dichiarato, nient'altro
- [ ] `uv run ruff check src tests` pulito
- [ ] `uv run pyright src/backtest src/features src/models <nuovi moduli>` = 0 errori
- [ ] `uv run pytest -q` tutto verde (numero test riportato)
- [ ] Nuovi moduli pyright-clean e con test offline
- [ ] Nessun fetch live nei test; fixture sintetiche
- [ ] STATUS.md aggiornato (sezione sessione), ROADMAP.md marcata, ADR registrata se prevista
- [ ] Se dashboard: screenshot light/dark/mobile in PR
- [ ] Se workflow: primo run `workflow_dispatch` verde linkato
- [ ] Esiti negativi documentati, non nascosti
