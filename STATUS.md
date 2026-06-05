# STATUS.md

> Stato corrente del progetto. **Aggiornare a ogni sessione.**
> Questo è il primo file che chi (umano o agente) riprende il lavoro deve leggere.

---

## Ultimo aggiornamento
2026-06-05

## Fase corrente
**Screener di rotazione + attribuzione eventi + report auto-aggiornati 🟢 attivo
— in fase di ACCUMULO DATI**, ora su **due universi: crypto ed equity (ETF
settoriali)**. Riorientamento deciso dall'utente: non predire il singolo asset,
ma individuare "cosa si muove ORA" + rischi + **catalizzatori** degli eventi,
con probabilità storiche. Fasi 0-5 ✅ in `main` (nucleo di ricerca: nessun edge
predittivo direzionale daily; unico indizio = macro/inflazione mensile, non
validabile col campione).

**Sessione 14 (2026-06-05)** — 3 PR mergiate in `main` + 1 in review:
- **#22 freshness check** (`src/ingestion/freshness.py`): intercetta i feed
  *congelati* (lezione POL/MATIC, ADR-026), guard nei cron di raccolta
- **#23 attribuzione eventi → equity ETF**: `attribution_cli` ora gira anche
  sugli ETF settoriali (rif. mercato S&P 500, soglia 1% vs 3% crypto); il motore
  è simmetrico → cattura sia crolli sia **balzi positivi**
- **#24 fonte news azionaria** (in review, CI verde): Google News per-settore
  nella stessa pipeline (ADR-027); il cron news ora accumula crypto + equity
- POL sistemato a monte (#21, ADR-026): `MATIC-USD` congelato → `POL28321-USD`

**Cosa è in piedi e FUNZIONA da solo:**
- `src/ingestion/tier1/coingecko.py::fetch_categories` — ~700 categorie CoinGecko
  (= mappa settoriale crypto), filtro min market cap
- `src/features/screener.py` — `screen_categories` (score rank-based robusto agli
  outlier: mossa 24h + turnover) + `screen_movers` (gainers/risк)
- `src/features/screener_report.py` — `format_report` (testo) + `format_report_md`
  (markdown); `screener_cli.py` per consultazione manuale
- **`REPORT.md`** in radice repo — **auto-aggiornato dal cron**, consultabile su
  GitHub senza lanciare nulla
- **2 cron giornalieri ATTIVI e funzionanti** (verificato 2026-06-01): commit del
  bot `data: update news/category history [skip ci]`. ⚠️ GitHub schedula con
  **ritardo variabile** (es. workflow 07:00 → eseguito 12:36 UTC): è normale,
  fidarsi del timestamp nel report

**⏸️ IN ATTESA (decisione utente: "aspettiamo di accumulare un po'")**: il layer
**probabilistico** ("data una categoria in stato 'hot', storicamente cosa è
successo dopo?") NON va costruito ora — solo 2 snapshot categorie (31/05, 01/06).
Servono settimane di history per evitare lo small-sample bias (vedi finding news
+0.32 → svanito). Il cron accumula da solo; riprendere quando ci sono ~4-8
settimane di snapshot.

**Q9/Q12/Q10 → ADR-023/024/025** chiuse.

**🔬 Finding Fase 5**: regimi vol (`classify_vol_regime`) + 4-stati
(`combine_regimes`) + halving clock (`cycles.py`), tutti causali. Test
conditioning (nb 09): accuracy OOS **0.498 → 0.510** (delta +0.0115, nel rumore)
→ **nessun edge** dal sapere il regime. MA la **decomposizione** è netta: il
rendimento BTC è fortemente regime-dipendente (bull_high_vol Sharpe **2.97** vs
bear_high_vol **−1.20**); la media full-sample (0.64) mescola mondi opposti.
Lezione: ogni metrica va letta **per regime**, mai in media.

**🔬 Finding Fase 4 (criterio di completamento)**: con `FRED_API_KEY` ora
disponibile, testato **tecnico vs tecnico+macro** su BTC (logistic walk-forward
OOS, stesso indice comune n=2249): accuracy **0.5007 → 0.5060** (delta +0.005,

**🔬 Finding Fase 4 (criterio di completamento)**: con `FRED_API_KEY` ora
disponibile, testato **tecnico vs tecnico+macro** su BTC (logistic walk-forward
OOS, stesso indice comune n=2249): accuracy **0.5007 → 0.5060** (delta +0.005,
dentro il rumore). **La macro NON aggiunge valore predittivo direzionale a
frequenza daily** — coerente con la EDA Fase 1 (segnale CPI vive a frequenza
mensile, ~0 daily). Niente leakage (un bug avrebbe gonfiato il delta). Risultato
**negativo, misurato e onesto**. Notebook 08. Direzioni vive: target mensile,
news (quando il cron avrà accumulato), modelli non lineari **solo se** un fattore
mostra segnale.

**🔬 Finding Fase 3 (onestà metodologica)**: il `corr(news_count, |return|)
= +0.32` visto su n=23 **è svanito a n=143** (market-wide, ~−0.07 a lag 1) →
**artefatto di piccolo campione, NON un segnale**. Idem sentiment→return
(rumore). Con i dati attuali **nessun potere predittivo lead** del Layer 1. La
Fase 3 resta aperta "in attesa di dati" (cron ADR-025 accumula storia, nb 06
riproducibile). Riprenderla quando la history avrà mesi densi.

Fase 2 chiusa con tutti i deliverable core: **harness di valutazione**
(engine custom, ADR-009) + **cost model** + **indicatori tecnici** +
**modelli baseline** + **notebook backtest OOS end-to-end** +
**classificazione di regime**. Fase 2.1 (robustezza baseline) confermata su
4/5 asset. Gli hook empirici da Fase 1 (volatility clustering, regime
instability, BTC vs CPI YoY −0.40) restano i vincoli di design.

## 🔭 Ripresa prossima sessione (leggere per primo)

### ✅ SBLOCCO RETE CONFERMATO (2026-05-30, ambiente nuovo)
Gli host news + HuggingFace sono **raggiungibili** in questo ambiente
(allowlist aggiornata attiva). Verifica eseguita su CoinDesk, Cointelegraph,
Google News, huggingface.co e il modello `ProsusAI/finbert` → tutti HTTP 200.
Caveat: i feed publisher nativi (CoinDesk, Decrypt, …) sono **anti-bot
instabili** da IP datacenter — lo stesso endpoint alterna RSS valido / 403 /
muro JS a seconda della richiesta. Non si aggirano (ADR-018); il fetch tollera
il fallimento e Google News (aggregatore) garantisce la copertura.

### Dove siamo
- **`main`** = `c3f52d2` (Fasi 0/1/2/2.1 mergiate). CI verde.
- **Fase 3, ingestion cablata e girata su dati veri** (branch
  `claude/phase-3-sentiment-news`, PR #6 draft):
  - `src/ingestion/news/feeds.py`: registry fonti — newswire generali
    (Cointelegraph, CoinDesk) + Google News per asset Tier 1 (≥2 fonti, ROADMAP).
    **Nota anti-bot**: i feed dei publisher nativi sono instabili da IP
    datacenter (200/403/JS-wall a rotazione); non si aggirano (ADR-018), il
    fetch tollera il fallimento parziale e Google News fa da backbone affidabile
  - `src/ingestion/news/persist.py`: `append_news` (history append-only,
    dedup su `item_id`, sort per `published`) — pura I/O su pandas
  - `src/ingestion/news/fetch_news.py`: entrypoint
    (`uv run python -m src.ingestion.news.fetch_news`); per-source parquet in
    `data/raw/news/` (gitignored), partial-failure tollerata
  - **Fetch reale OK**: 7 fonti, **560 item** persistiti
    (cointelegraph 30, decrypt 30, googlenews_{btc,eth,sol,link,pol} 100 cad.),
    timestamp maggio 2026, index UTC, dedup cross-fetch verificata (run 2: +0)
  - **187/187 pytest verde** (+10: 5 feeds + 5 persist), ruff + format puliti,
    pyright pulito su `src/ingestion/news`

### Sentiment Layer 1 (lessico/VADER) — fatto
- `src/ai/lexicon/sentiment.py` (+ `__init__`): `score_text` (VADER compound
  [-1,1]), `score_news_frame` (scoring sul titolo), `daily_sentiment`
  (aggregazione a giorno UTC: `mean_sentiment` + `news_count`),
  `lag_daily_features` / `align_sentiment_returns` (lag 1g anti-look-ahead,
  ADR-024). Dipendenza leggera `vaderSentiment` (no torch)
- **8 nuovi test offline** (`test_sentiment.py`): sign/bounds, empty,
  aggregazione, lag, anti-look-ahead nel join
- **Validato su dati veri**: 560 news scorate (range sensati, mean ~0,
  min −0.84 / max +0.79). Lead/lag BTC (n=23 giorni, indicativo): corr
  sentiment(D)↔return(D+1) **−0.10** (rumore, atteso); corr
  news_count(D)↔|return(D+1)| **+0.32** (il *volume* di notizie anticipa
  debolmente la volatilità — da verificare su storia più lunga)

### News history versionata (ADR-025) — fatto
- **Scelta utente**: accumulare storia news (i feed danno ~settimane). Storage =
  **commit nel repo** con eccezione mirata ad ADR-009 → **ADR-025**; chiude Q10
- `src/ingestion/news/history.py` (`to_compact` + `update_history`) +
  `src/ingestion/news/update_history.py` (entrypoint schedulabile)
- `.github/workflows/news-history.yml`: cron giornaliero 06:30 UTC, commit del
  parquet con `[skip ci]`; `.gitignore` carve-out `!data/news_history/*.parquet`
- **Seed reale committato**: `data/news_history/news.parquet`, **543 item**
  compatti (~260KB), schema `item_id,source,title,url,sentiment` (no summary)
- **4 nuovi test** (`test_news_history.py`); **199/199 pytest verde**

### Feature news-derived + notebook lead/lag — fatto (branch corrente)
- `src/features/news_features.py`: `rolling_mean_sentiment`, `sentiment_change`,
  `news_volume_zscore` (causale, baseline shiftata, no leakage), `build_news_features`,
  `lead_lag_table` (corr feature[t] vs target[t+k] **con n** per ogni lag). 8 test
- `notebooks/06_news_sentiment_leadlag.ipynb` (eseguito, output embedded): H1-H3
  scritte prima, analisi su BTC + market-wide news (n=143). **Esito: nessun
  segnale lead** (vedi finding chiave sopra). Riproducibile (news committate)
- **207/207 pytest verde**, ruff + format + pyright core puliti

### Prossimi step Fase 3
1. **Lasciar girare il cron** per accumulare mesi di storia, poi **rieseguire
   nb 06** (è già pronto e riproducibile) per ricontrollare i lead/lag su n grande
2. Quando la storia per-asset sarà densa: estendere nb 06 a tutti i Tier 1
   (ora BTC è l'unico con abbastanza prezzi+news allineati)
3. **Solo se** emergesse un segnale robusto: valutare FinBERT (Layer 2, ADR-016)
   — decisione separata, dipendenze pesanti. Finora l'evidenza NON lo giustifica

**Stream educational**: L1 chiuso (10/10). I prossimi capitoli (L2) sugli
indicatori/regimi/risk si possono scrivere ora che il codice esiste.

**Come far girare tutto**: `uv sync`, poi `uv run pytest -q`. Per i
notebook serve prima `uv run python -m src.ingestion.tier1.fetch_tier1`
(dati gitignored). Notebook eseguiti con
`cd notebooks && PYTHONPATH=.. uv run jupyter nbconvert --execute --inplace <nb>`.

## Cosa è stato fatto

### 2026-05-31 — Sessione 13: Fase 5 — cicli, regimi & contestualizzazione
- **`src/features/regime.py` esteso**: `classify_vol_regime` (vol alta/bassa via
  soglia relativa causale, baseline shiftata anti-leakage), `combine_regimes`
  (4-stati bull/bear × high/low vol), `summarize_by_regime` reso generico per
  qualsiasi label set. Scelta: soglie trasparenti, **non HMM** (niente dipendenze
  pesanti/scatole nere — coerente con la decisione di Fase 2)
- **`src/features/cycles.py` (nuovo)**: halving clock causale — `days_since/to
  halving`, `halving_phase` ciclica. Date halving come costanti (calendariali)
- **Notebook 09** (`09_regimes_cycles.ipynb`, eseguito): H1-H3 prima.
  - **Conditioning**: tecnico vs tecnico+regime, accuracy OOS 0.498 → 0.510
    (delta +0.0115, nel rumore, n=2430) → nessun edge dal sapere il regime
  - **Decomposizione** BTC per 4-stati: bull_high_vol Sharpe **+2.97**,
    bull_low_vol +1.55, bear_low_vol −0.81, bear_high_vol **−1.20** → il
    rendimento è fortemente regime-dipendente, la media (0.64) è un artefatto
- **16 nuovi test** (`test_regime_vol.py` 7 + `test_cycles.py` 6 + esistenti),
  **241/241 pytest verde**, ruff + pyright core puliti
- Branch `claude/phase-5-regimes`

### 2026-05-30 — Sessione 12: Fase 4 — valutazione macro (criterio completamento)
- **`FRED_API_KEY` fornita** dall'utente → `.env` (gitignored), fetch 7 serie FRED OK
- **Notebook 08** (`08_macro_value.ipynb`, eseguito): tecnico vs tecnico+macro,
  stessa logistic walk-forward, confronto su indice OOS comune (n=2249).
  **0.5007 → 0.5060** (delta +0.005, rumore). **La macro non aggiunge edge
  direzionale a daily** — atteso (EDA Fase 1: macro è segnale mensile, ~0 daily).
  Nessun leakage. Risposta al criterio di completamento Fase 4: *no, l'integrazione
  tecnico+macro non aggiunge valore predittivo a frequenza daily su BTC*
- **Fix `multifactor.py`**: guardia su index duplicati + target costruito sullo
  stesso `test_index` posizionale della predizione (allineamento robusto)
- **247/247 pytest verde**, ruff + pyright core puliti
- **Cron news**: workflow schedulato su `main`, non ancora eseguito (nessun
  commit-dati finora; partirà al prossimo trigger 06:30 UTC)

### 2026-05-30 — Sessione 11: Fase 4 — design matrix + primo modello multifattoriale
- **PR #8 mergiata in `main`** (`3e13c0d`): macro pipeline point-in-time-safe
- **`scikit-learn` aggiunto** (era in ADR-009, non in pyproject — dip. leggera, no torch)
- **`src/features/dataset.py`**: `technical_features` (SMA gap, MACD hist, RSI,
  ATR%, ret), `directional_target`, `assemble_design_matrix` (join tecnico+macro+
  news, **lag 1 su tutte le feature** → la riga t è lo stato di t-1, predice
  direzione di t; rifiuta lag 0 che leakerebbe). 6 test
- **`src/models/multifactor.py`**: `fit_predict_walk_forward` (logistic regression,
  **scaler fit-on-train-only**, walk-forward expanding via `walk_forward_splits`,
  OOS stitchate), `WalkForwardResult`, `positions_from_predictions`. 6 test
  (segnale apprendibile → >0.9 OOS; rumore → ~0.5; troppo corto → vuoto)
- **`notebooks/07_multifactor_model.ipynb`** (eseguito): H1-H3 prima, BTC reale.
  **Accuracy OOS 0.497** (coin-flip), strategia net Sharpe 0.37 vs B&H 0.98 →
  nessun edge col solo tecnico. Barra onesta, niente look-ahead nascosto
- **229/229 pytest verde**, ruff + pyright core puliti
- Branch `claude/phase-4-model`

### 2026-05-30 — Sessione 10: consolidamento Fase 3 + apertura Fase 4 (macro)
- **PR #7 mergiata in `main`** (squash `34c1af7`): feature news-derived,
  notebook lead/lag, capitolo educational L2.06 (bias cognitivi). Fase 3
  consolidata; resta aperta "in attesa di dati" (cron accumula storia)
- **Fase 4 avviata** (branch `claude/phase-4-multifactor`). Primo deliverable:
  `src/features/macro_features.py` — pipeline macro **point-in-time-safe** da FRED:
  - `apply_publication_lag`: shifta ogni serie alla sua **release date** reale
    (CPI/M2/UNRATE lag ~35-45g; daily rates lag 0) → chiude il debito look-ahead
    su release-date segnalato nel nb 03 (ROADMAP riga 204)
  - `to_daily` (step function, no back-fill), `align_macro_to_index` (ffill,
    NaN prima della prima release → mai indovinato), `yoy_change` (l'orizzonte
    YoY dove vive il segnale CPI per la EDA Fase 1)
  - `build_macro_features`: fed_funds, rate_2y/10y, **yield_curve_slope**,
    broad_dollar, **cpi_yoy**, m2_yoy, unemployment — tutte causali; degrada
    con grazia se una serie manca su disco
- **10 nuovi test** (`test_macro_features.py`): lag, no-back-fill, no-look-ahead
  nell'align, YoY, end-to-end su FRED dir temporanea. **217/217 pytest verde**,
  ruff + pyright core puliti
- **Nota**: il fetch reale FRED richiede `FRED_API_KEY` (.env gitignored, non
  persiste tra container) → il notebook su dati veri è subordinato al key, come
  gli altri notebook data-dipendenti. Il modulo è testato offline su sintetici

### 2026-05-30 — Sessione 9: Fase 3 — feature news-derived + notebook lead/lag
- **PR #6 mergiata in `main`** (squash `542fff6`): ingestion + Layer 1 + history
- **Nuovo modulo** `src/features/news_features.py` (causale, pyright-clean):
  `rolling_mean_sentiment`, `sentiment_change`, `news_volume_zscore` (z-score con
  baseline shiftata → no leakage same-day), `build_news_features`, `lead_lag_table`
  (corr feature[t] vs target[t+k] **+ n** per ogni lag, mai un lag cherry-picked)
- **8 test offline** (`test_news_features.py`): causalità, no-look-ahead, z-score
  finito su varianza zero, recupero di un lead noto, report di n
- **Notebook 06** (`06_news_sentiment_leadlag.ipynb`, eseguito): H1-H3 prima dei
  numeri, BTC + market-wide news (n=143), allineamento ADR-024 esplicito
- **Finding chiave**: il `+0.32` (news_count→|return|) di n=23 **svanisce a
  n=143** → artefatto, non segnale. Nessun potere predittivo lead del Layer 1
  con i dati attuali. Documentato apertamente (CLAUDE.md: tracciare cosa non funziona)
- **207/207 pytest verde**, ruff + format + pyright core puliti. Branch
  `claude/phase-3-news-features`

### 2026-05-30 — Sessione 8: Fase 3 — connettori reali, sentiment Layer 1, news history
- **Sblocco rete** (ambiente nuovo): news + huggingface.co + FinBERT tutti 200
- **Ingestion cablata** (`feeds.py`/`persist.py`/`fetch_news.py`): Cointelegraph
  + CoinDesk + Google News per asset; 560 item reali persistiti (gitignored).
  Publisher nativi anti-bot instabili da IP datacenter → Google News backbone
- **Q9 → ADR-023** (sentiment Layer 1 = VADER, no torch) + `src/ai/lexicon/`
  (`score_text`, `score_news_frame`, `daily_sentiment`)
- **Q12 → ADR-024** (publication-time + lag 1g) + `lag_daily_features`,
  `align_sentiment_returns` (test anti-look-ahead)
- **Q10 → ADR-025** (batch giornaliero + news history versionata): `history.py`,
  `update_history.py`, workflow `news-history.yml`, carve-out gitignore.
  Seed `data/news_history/news.parquet` committato (543 item, ~260KB)
- **199/199 pytest verde**, ruff + format + pyright (news/ai + core) puliti
- **Validazione onesta**: lead/lag BTC n≈23 (indicativo) → sentiment(D)↔
  return(D+1) −0.10; news_count(D)↔|return(D+1)| +0.32. Serve più storia

### 2026-05-28 — Sessione 1: framing & decisioni
- Repository svuotata dal precedente progetto (gioco Snake)
- Creati i 6 file di documentazione: `CLAUDE.md`, `VISION.md`, `ROADMAP.md`,
  `STATUS.md`, `DECISIONS.md`, `OPEN_QUESTIONS.md`
- Chiuse le decisioni di Fase 0 e le successive (ADR-001 ÷ ADR-018, tutte
  in `DECISIONS.md`)
- Aggiunto modulo didattico come stream parallelo (ADR-015)
- Definito ruolo dell'AI (ADR-016) e tassonomia fonti dati (ADR-017)
- Chiarita distinzione "impossibile vs scelta etico-legale" (ADR-018)

### 2026-05-28 — Sessione 1 (cont.): apertura Fase 1
- **Setup ambiente**: `uv init` con Python 3.12.11 installato automaticamente,
  dipendenze sincronizzate (pandas, polars, pyarrow, yfinance, pydantic,
  jupyter, ruff, pyright, pytest, matplotlib, seaborn)
- **`pyproject.toml`** configurato con ruff (line-length 100, ruleset E/W/F/I/B/UP/SIM/RUF)
  e pyright basic mode (ADR-009)
- **`.gitignore`** completa (data/, .env, venv, cache HF/uv, ipynb checkpoints)
- **Struttura cartelle** creata: `src/{assets,ingestion/tier1,ai/{nlp_local,llm_api},execution}`,
  `notebooks/`, `data/{raw,processed}/`, `tests/`, `config/`,
  `education/L{1,2,3,4}_*/`, `docs/`
- **Modello asset asset-class-agnostic** (`src/assets/asset.py`, ADR-014):
  `Asset` pydantic model con `AssetClass`, `TradingCalendar`, simboli
  multi-source (yahoo, binance, coingecko). Tier 1 (BTC/ETH/SOL/LINK/POL)
  e context assets (DXY, SPX, NDX, GOLD) come costanti
- **Interfaccia astratta `DataSource` / `OHLCVDataSource`** (`src/ingestion/base.py`)
- **Prima implementazione concreta**: `YahooFinanceSource`
  (`src/ingestion/tier1/yahoo_finance.py`) + `save_ohlcv_parquet` helper
- **Entrypoint batch** per ingestion Tier 1 (`src/ingestion/tier1/fetch_tier1.py`)
- **Inventario fonti Tier 1** completo in `docs/data_sources_tier1.md`
- **Modulo didattico bootstrappato**:
  - `education/README.md` (indice)
  - `education/L{1,2,3,4}_*/README.md` (capitoli pianificati per livello)
  - **Primo capitolo L1 pubblicato**: `01_asset_borsa_broker.md`
- **Notebook EDA scaffold**: `notebooks/01_exploration_btc_eth.ipynb`
  (statistiche descrittive, distribuzione log-return, ACF, volatility clustering)
- **Test sanity** (`tests/test_assets.py`): 5 test passano
- **Lint pulito**: ruff su src/ e tests/ tutto verde
- **README di progetto** aggiornato con quickstart e network policy needed

### 2026-05-28 — Sessione 2: fetch reale Yahoo Finance OK
- Verifica connettività: `curl -sI https://query2.finance.yahoo.com/`
  ritorna 429 (anti-bot edge contro UA scarno di curl); l'endpoint dati
  `query1.finance.yahoo.com/v8/finance/chart/<SYM>` ritorna **200** con UA
  browser. `yfinance` (via `curl-cffi`) passa senza problemi.
- **`uv run python -m src.ingestion.tier1.fetch_tier1` completato**:
  9/9 asset scaricati in `data/raw/yahoo/{crypto,index,commodity}/`
  - BTC, ETH, LINK: 3069 righe, 2018-01-01 → 2026-05-27 (full)
  - SOL: 2239 righe, 2020-04-10 → 2026-05-27 (dal lancio Solana)
  - **POL: 1181 righe iniziali sul ticker `POL-USD`, troncate a 2023-10-31**
    → risolto con [ADR-019](./DECISIONS.md): switch a `MATIC-USD` come
    simbolo Yahoo, ora 2158 righe (2019-04-28 → 2025-03-24, 0 gap).
    Gap recente 2025-03-24 → oggi resta aperto come Q21bis (si chiude
    quando aggiungeremo Binance/CoinGecko)
  - DXY, SPX, NDX, GOLD: ~2111-2113 righe, 2018-01-02 → 2026-05-27
    (mercato chiuso nei weekend, normale)
- **Quality check superato**: 0 NaN, 0 gap "anomali" per tutti gli asset
- **Nota su network policy**: i 403 `host_not_allowed` riportati nella
  sessione precedente sono spariti — l'ambiente attuale permette outbound
  verso Yahoo. `fc.yahoo.com` (cookie/crumb endpoint usato da yfinance in
  alcuni casi) è ancora `host_not_allowed` ma non è necessario per il
  chart endpoint pubblico.

### 2026-05-28 — Sessione 2 (cont.): EDA BTC + ETH
- Eseguito `notebooks/01_exploration_btc_eth.ipynb` con
  `PYTHONPATH=. uv run jupyter nbconvert --execute` (3068 rendimenti
  log-daily per asset, 2018-01-02 → 2026-05-27)
- **Findings descrittivi** (fatti stilizzati della finanza tutti
  confermati):

  | | BTC | ETH |
  |---|---|---|
  | Mean log-return | 0.055%/d (~14% ann.) | 0.031%/d |
  | Annualized vol | 64.8% | 85.1% |
  | Skewness | -0.95 | -0.84 (entrambi left-skewed) |
  | Kurtosis (excess) | 14.7 | 10.95 (Normal = 0 → fat tails) |
  | Worst day | -46.5% | -55.1% |
  | Best day | +17.2% | +23.1% |

- **ACF — efficienza weak-form + volatility clustering**:
  - `ACF(r)` lag 1: BTC -0.05, ETH -0.05 → rendimenti ~ unforecastable da
    soli lag
  - `ACF(|r|)` lag 1: BTC 0.16, ETH 0.16 → forte volatility clustering,
    persistente a lag 5 (~0.12-0.13)
  - Apre la strada a famiglia GARCH come baseline volatilità nelle fasi
    successive
- ETH è ~30% più volatile di BTC su base annualizzata (consistente con
  ipotesi: "asset a maggiore beta ha più vol")
- Nessuna sorpresa metodologica nei dati: distribuzione si comporta come
  ci si aspetta da serie crypto, segnale che il fetch è pulito

### 2026-05-28 — Sessione 2 (cont.): EDA estesa a tutti i Tier 1 crypto
- Notebook refattorizzato per essere cross-asset (BTC/ETH/SOL/LINK/POL)
- **Vol annualizzata cresce monotonicamente**: BTC 65% < ETH 85% <
  LINK 115% ≈ SOL 119% < POL 136% → ordering di "rischiosità" coerente
  con dimensione/maturità del progetto
- **Skewness**: BTC/ETH marcatamente left-skewed (-0.95/-0.84), mentre
  SOL/LINK/POL praticamente simmetriche o leggermente positive. Ipotesi
  da testare: la skewness negativa di BTC/ETH potrebbe essere legata
  alla loro maggiore "istituzionalizzazione" (selling pressure asimmetrica
  dei grandi holder?)
- **Kurtosis** (excess): tutti 7-16 → fat tails universali; POL ha la
  kurtosis più alta (15.8) ma è anche la serie più rumorosa post-2025
- **ACF(|r|) lag 1**: BTC/ETH 0.16, LINK 0.21, SOL 0.27, POL 0.26 →
  **volatility clustering più forte nelle altcoin**. La predicibilità
  della varianza scala con la dimensione/volatilità: utile per modellare
  l'incertezza asset per asset
- **Cross-asset correlations** (1809 giorni comuni 2020-04 → 2025-03):
  - BTC ↔ ETH: 0.81 (blue-chip co-movement)
  - ETH ↔ altcoin: 0.61-0.75 (ETH funziona da "hub" per le altcoin,
    più correlata di BTC con il resto)
  - LINK ↔ ETH: 0.75 (LINK è ETH-ecosystem heavy)
  - SOL ↔ BTC: 0.53 (la meno correlata; coerente con narrativa
    "Ethereum competitor")
  - Nessuna coppia sotto 0.5 → diversificazione **moderata** in Tier 1,
    non zero ma neanche scarsa
- Aggiunta rolling 90-day correlation vs BTC per studiare la stabilità
  delle correlazioni (visibile nel notebook)
- **Bugfix incontrato**: il parquet salvato ha `timestamp` come index
  (non come colonna) quando letto via pandas. Aggiornata `load_ohlcv`
  nel notebook (vedi `notebooks/01_exploration_btc_eth.ipynb`)

### 2026-05-28 — Sessione 2 (cont.): EDA crypto vs macro context
- Nuovo notebook `notebooks/02_crypto_vs_macro.ipynb`
- Universo allargato: 5 crypto Tier 1 + 4 context asset (SPX, NDX, DXY,
  GOLD). Allineamento sui **trading day comuni** (inner join sui log-return);
  974 righe utili da 2020-04-14 a 2025-03-21
- **Correlazioni daily medie**:
  - Crypto ↔ SPX / NDX: **~0.39** (positive, regime "risk-on" comune
    tra crypto e tech-equity USA)
  - Crypto ↔ DXY: **~-0.21** (dollaro forte = crypto debole, link
    moderato ma consistente)
  - Crypto ↔ GOLD: **~0.08** (sostanzialmente zero a frequenza daily →
    la narrativa "BTC = oro digitale" non regge come correlazione
    contemporanea; eventualmente da testare a frequenze maggiori o in
    sotto-periodi specifici)
  - SPX ↔ NDX: 0.93 (info ridondante; un solo proxy equity USA può
    bastare per features di livello macro)
  - DXY ↔ GOLD: -0.42 (classica inverse, conferma sanità dati)
- **Rolling 90d correlation**: std tra 0.10 e 0.17 su tutte le coppie
  crypto-macro → **correlazioni regime-dependent**, non costanti. BTC vs
  SPX media 0.38 ma oscilla tra ~0 e ~0.65. Quantificato in cell 7 del
  notebook
- Implicazione per la roadmap: lo "stato del mercato" (regime risk-on
  vs risk-off) va trattato come variabile esplicita nel modello, non
  marginalizzato. Ipotesi per Fase 2: clustering / regime-switching
  sulle correlazioni rolling
- **Caveat metodologico documentato**: l'inner-join sui trading day USA
  somma il "weekend gap" del crypto al return del lunedì. Per analisi
  future a granularità più fine, costruire return crypto allineati alla
  cadenza dei mercati tradizionali

### 2026-05-28 — Sessione 2 (cont.): Binance come secondo provider (ADR-020)
- **Geo-block scoperto**: `api.binance.com` risponde HTTP 451 dall'IP del
  sandbox (ToS Binance, non network policy). Per ADR-018 non aggirabile.
- **Scelta**: `BinanceSource` con base URL configurabile, default
  `api.binance.us`. Tutti i Tier 1 pair disponibili anche su .us.
- **Nuovo file** `src/ingestion/tier1/binance.py`:
  - Endpoint pubblico klines, no API key, no SDK
  - Paginazione esplicita (limit 1000/call, loop fino a end)
  - 451 → `PermissionError` con riferimento a ADR-020
  - Schema OHLCV identico a quello di YahooFinanceSource (`open, high,
    low, close, volume`, DatetimeIndex UTC)
- **Refactor `fetch_tier1.py`**: ora accetta `--source {yahoo,binance,all}`
  via CLI; `fetch_all()` parametrizzata sulla source (era hardcoded Yahoo).
  Asset context (DXY/SPX/NDX/GOLD) saltati automaticamente su Binance
  perché non hanno `binance_symbol` (corretto: Binance non lista indici)
- **Test unitari** (`tests/test_binance.py`, 8 nuovi test, no network):
  parsing klines, paginazione (mock 2 batch), 451→PermissionError,
  ValueError su simbolo mancante, gestione empty response. **13/13
  pytest verde**, ruff pulito
- **Fetch reale via Binance.us**, 5/5 crypto Tier 1 scaricati:

  | asset | Yahoo | Binance.us | overlap |
  |---|---|---|---|
  | BTC | 2018-01 → 2026-05 (3069) | 2019-09 → 2026-05 (2440) | 2439 |
  | ETH | 2018-01 → 2026-05 (3069) | 2019-09 → 2026-05 (2440) | 2439 |
  | SOL | 2020-04 → 2026-05 (2239) | 2020-09 → 2026-05 (2079) | 2079 |
  | LINK | 2018-01 → 2026-05 (3069) | 2022-01 → 2026-05 (1596) | 1596 |
  | **POL** | 2019-04 → 2025-03 (2158) | **2025-01 → 2026-05 (498)** | **68** |

- **Cross-validation BTC**: differenza % media 0.14%, mediana 0.07%,
  log-return correlation Yahoo↔Binance.us = **0.996**. I dati daily
  Yahoo erano già di qualità eccellente, Binance.us conferma
- **Cross-validation POL**: rapporto POL/MATIC sui 68 giorni di overlap
  = 0.998 ± 0.007, log-return correlation 0.977 → i due ticker sono
  operativamente lo stesso asset (rebrand 1:1 confermato dai dati)
- **Q21bis chiusa via ADR-020**. Nuova Q22 aperta: come comporre
  Yahoo+Binance in una "serie POL canonical" (decisione tecnica
  rinviata al primo modulo che ne ha davvero bisogno, probabile
  direzione: concatenazione con flag di provenance)

### 2026-05-28 — Sessione 2 (cont.): composer multi-source (ADR-021)
- **Nuovo modulo** `src/ingestion/composer.py` con `compose_ohlcv()`:
  funzione pura, prende lista di `(DataFrame, source_name)` in ordine
  di priorità crescente, ritorna serie unica + colonna `source` di
  provenance per riga
- **Policy di overlap**: later-listed source wins
  (`drop_duplicates(keep="last")` sull'index). Naturale, swappa l'ordine
  per ribaltare la priorità
- **7 nuovi test unitari** (`tests/test_composer.py`): no-overlap,
  overlap binario, overlap a 3 source, empty input, missing columns,
  no source dei dati buoni. **Totale 20/20 pytest verde**
- **Prima applicazione**: serie POL composta in
  `data/processed/POL_1d.parquet`
  - **2588 righe** complessive, 2019-04-28 → 2026-05-28 (full coverage!)
  - Source breakdown: 2090 yahoo + 498 binance (dedup di 68 giorni
    overlap)
  - Math check: 2158 + 498 − 68 = 2588 ✓
  - Binance vince come previsto nel cutover (gennaio 2025 in poi)
- **Q22 chiusa** (ADR-021). Nuova Q23 aperta: come trattare il volume
  multi-source (Yahoo cross-exchange vs Binance single-venue, scale
  diverse). Non bloccante per Fase 1; da decidere quando faremo feature
  volume-based in Fase 2
- Architettura risultante: pipeline a 3 layer pulita
  - **raw**: `data/raw/{provider}/{class}/{SYMBOL}_{interval}.parquet`
    (gitignored, una entry per provider)
  - **processed**: `data/processed/{SYMBOL}_{interval}.parquet`
    (gitignored, una sola serie per asset, con `source` column)
  - **code**: ingestion sources implementano `OHLCVDataSource`, il
    composer è puro pandas, downstream non sa dei provider

### 2026-05-28 — Sessione 2 (cont.): CoinGecko come terzo provider
- **Nuovo file** `src/ingestion/tier1/coingecko.py` con `CoinGeckoSource`
  - **Non** implementa `OHLCVDataSource`: CoinGecko ritorna single-price
    points, non OHLC. Forzare l'astrazione sarebbe lossy. Eredita solo
    da `DataSource` (interfaccia minimale: `name`) ed espone metodi
    specializzati
  - Metodi: `fetch_market_chart()`, `fetch_global()`, `fetch_top_n()`
  - **Retry con exponential backoff** su 429 (free tier free strict,
    quota IP-shared sul sandbox). Default: 5 retry, base 30s →
    60/120/240/480s. Configurabile.
  - Supporto opzionale Demo API key via env `COINGECKO_API_KEY`
- **Nuovo script** `src/ingestion/tier1/fetch_coingecko.py`: 5 asset +
  global + top-20 con pacing 10s, ~50s totali
- **9 nuovi test** (`tests/test_coingecko.py`): parser market_chart con
  floor-to-date, dominance extraction, top-N ranking, retry recovery,
  retry exhaustion, Demo key header. **29/29 pytest verde, lint pulito**
- **Fetch reale via free tier (no API key)** completato:
  - **BTC/ETH/SOL/LINK/POL** market chart: 365 righe ciascuno
    (2025-05-29 → 2026-05-28; free tier limit)
  - **Global snapshot**: BTC dominance 57.7%, ETH 9.4%, USDT 7.5%,
    BNB 3.4%, XRP 3.2%; total market cap **$2.52T**; 17,401 cripto
    attive globalmente
  - **Top 20** by market cap: i nostri Tier 1 sono tutti dentro tranne
    **POL (caduto fuori top 20)** — interessante perché in ADR-005 POL
    era selezionato come Tier 1 dall'utente per ragioni indipendenti
    dal rank di market cap; il dato conferma che POL ha perso peso
    relativo nel 2025
  - Cross-check BTC CG vs Yahoo (ultimi 30 giorni): mediana |diff%|
    1.06% — coerente con il fatto che l'ultimo punto CG è "ora"
    (orario fetch) mentre Yahoo è close UTC midnight
- **Q24 aperta**: lo script attuale sovrascrive
  `global_latest.parquet` ad ogni run. Per analisi temporale di
  dominance servirà append. Decisione rinviata a quando avremo bisogno
  di dominance storica (presumibilmente Fase 2+)

### 2026-05-28 — Sessione 2 (cont.): EDA crypto-vs-macro + test Yahoo
- **Eseguito `notebooks/02_crypto_vs_macro.ipynb`** sui 9 asset
  (5 crypto + 4 macro), 974 trading day comuni (2020-04 → 2025-03):

  Correlazioni statiche notevoli:
  | | BTC | ETH | DXY | SPX | NDX | GOLD |
  |---|---|---|---|---|---|---|
  | BTC vs … | 1.00 | 0.83 | **-0.21** | **0.39** | 0.39 | 0.08 |
  | ETH vs … | 0.83 | 1.00 | -0.22 | 0.39 | 0.38 | 0.10 |
  | SPX ↔ NDX | | | | 0.93 | | |
  | GOLD ↔ DXY | | | -0.42 | | | |

  Conclusioni:
  - **Crypto è risk-on**: positivo con tech equity, negativo con
    dollaro. Non è "digital gold" (correlazione GOLD vicina a zero)
  - **SPX/NDX co-muovono** (0.93): qualsiasi feature derivata da uno
    è quasi-ridondante con l'altro
  - **GOLD-DXY -0.42** conferma il dollaro come fattore principale
    per oro, mentre lo è meno per crypto
- **Rolling-90d statistics** (correlazione crypto vs macro):
  std 0.12-0.17 → relazioni instabili, regime-dependent. Apre la
  strada a regime-switching models in Fase 2
- **7 nuovi test** per `YahooFinanceSource` (mock di yfinance, no
  network): missing yahoo_symbol → ValueError, invalid interval →
  ValueError, column rename + tz UTC normalization, tz conversion
  (NY → UTC), NaN close drop, empty response → empty frame, kwargs
  forwarding (auto_adjust + actions baked-in)
- **Coverage simmetrica sui 3 provider**: Yahoo 7 + Binance 8 +
  CoinGecko 9 + Composer 7 + Assets 5 = **36/36 pytest verde**,
  ruff pulito

### 2026-05-28 — Sessione 2 (chiusura): educational L1.02
- Pubblicato `education/L1_principiante/02_tipi_di_ordine.md`:
  market / limit / stop / stop-limit / time-in-force, con esempi su
  BTC e collegamento esplicito a ADR-013 (modello slippage) e ai dati
  Binance che stiamo scaricando
- L1 ora ha 2/10 capitoli pubblicati. Prossimo: L1.03 sulla lettura
  dei grafici (candele, volume)

### 2026-05-29 — Sessione 3: FRED come quarto provider Tier 1
- **API key FRED** ottenuta gratis da
  https://fredaccount.stlouisfed.org/apikeys, salvata in `.env`
  (gitignored, verificato)
- **Nuovo file** `src/ingestion/tier1/fred.py` con `FredSource`:
  - Eredita solo da `DataSource` (FRED ritorna single-value series,
    non OHLCV; stesso pattern di CoinGecko)
  - Metodi: `fetch_series(series_id, observation_start, observation_end)`,
    `fetch_series_info(series_id)`
  - Validazione: senza `FRED_API_KEY` in env (o param esplicito)
    rifiuta l'init con `ValueError`
  - Gestione 400 con messaggio FRED (es. bad key) e 429 con retry
    + backoff esponenziale (3 retry, base 5s)
  - Conversione del sentinel `"."` → `NaN` (FRED indica così le
    osservazioni mancanti)
- **Nuovo script** `src/ingestion/tier1/fetch_fred.py`: 7 serie macro,
  storage `data/raw/fred/{frequency}/{SERIES_ID}.parquet` (path-based
  provenance per cadenza)
- **12 nuovi test** (`tests/test_fred.py`, no network): init senza key
  → ValueError, env vs explicit precedence, parser values + missing
  sentinel + sort, fetch_series params, fetch_series_info metadata,
  400 surfacing FRED error_message, 429 retry recovery + exhaustion.
  **48/48 pytest verde, lint pulito**
- **Fetch reale FRED** completato (~10 secondi totali):

  | series | rows | freq | range | NaN | nota |
  |---|---|---|---|---|---|
  | DFF | 3070 | D | 2018-01-01 → 2026-05-28 | 0 | Fed funds rate |
  | DGS2 | 2194 | D | 2018-01-01 → 2026-05-28 | 93 | 2Y Treasury |
  | DGS10 | 2194 | D | 2018-01-01 → 2026-05-28 | 93 | 10Y Treasury |
  | DTWEXBGS | 2190 | D | 2018-01-01 → 2026-05-22 | 96 | Broad Dollar |
  | CPIAUCSL | 100 | M | 2018-01-01 → 2026-04-01 | 1 | CPI all items |
  | M2SL | 100 | M | 2018-01-01 → 2026-04-01 | 0 | M2 money supply |
  | UNRATE | 100 | M | 2018-01-01 → 2026-04-01 | 1 | Unemployment |

  I NaN nelle daily series sono festività USA (93-96 in 8 anni = quadra)
- **Insight già pronto: yield curve slope** (DGS10 − DGS2):
  - Mean 2018-2026: **+0.25%**
  - **Inverted nel 25.9% dei giorni** (segnale recessione classico)
  - Slope corrente: ~0.46% (positivo, normal)
- **Validazione cross-source DXY**:
  - Yahoo DXY (paniere 6 major) ↔ FRED DTWEXBGS (paniere 26 partner)
    su 2085 giorni comuni
  - Level correlation **0.90**, log-return correlation **0.76**
  - Alta ma non perfetta — sono effettivamente metriche diverse
    (geographic mix), entrambe valide. Buon cross-check di
    "dollaro strength"
- Pipeline data ingestion **essenzialmente completa** per Fase 1:
  4 provider (Yahoo + Binance.us + CoinGecko + FRED) coprono crypto
  prices/volumes + global crypto market + US macro fundamentals.
  Manca solo on-chain (Etherscan / Blockchain.com) come stretch goal

## Cosa è in corso

### 2026-05-30 — Sessione 4: harness di valutazione Fase 2
- **Nuovo package** `src/backtest/` (engine custom, ADR-009 — scelto
  custom per controllo totale su no-look-ahead e futuro cost model):
  - `metrics.py`: metriche su serie di rendimenti semplici periodici —
    equity curve, total/annualized return, annualized vol, Sharpe,
    Sortino (downside deviation), drawdown series + max drawdown +
    durata, Calmar, hit rate, profit factor, time underwater, e
    `summarize()` che le impacchetta in un `PerformanceSummary`.
    Annualizzazione parametrica via `periods_per_year`
    (asset-class-agnostic, ADR-014: 365 crypto / 252 equity), default
    crypto-first ma overridable
  - `splits.py`: walk-forward splitter rolling/expanding, posizionale
    (index-agnostic). Invariante no-look-ahead (`test_start >=
    train_end`) forzata alla costruzione di `Split`. `split_frame()`
    helper iloc-based
  - `benchmark.py`: buy-and-hold (equity + returns) e DCA (contributo
    fisso a cadenza fissa, nessun look-ahead) — DCA è il benchmark che
    conterà davvero in Fase 6 (vedi L1.06). Equity curve confrontabili
    con quelle delle strategie via le stesse metriche
- **35 nuovi test** (`test_metrics.py`, `test_splits.py`,
  `test_benchmark.py`) su curve note + edge case (vol zero, serie vuota,
  no-downside → Sortino NaN, wipe-out, cadenze DCA, invariante
  anti-look-ahead). **102/102 pytest verde**, ruff pulito, pyright
  pulito su `src/backtest`
- Sviluppo su branch dedicato `claude/phase-2-baseline-backtest` (da
  `main`); la doc review resta isolata in PR #3

### 2026-05-30 — Sessione 4 (cont.): cost model (ADR-013)
- **Nuovo modulo** `src/backtest/costs.py`:
  - `FeeModel` maker/taker su notional; costanti `BINANCE_SPOT`
    (0.10%/0.10%) e `KRAKEN_SPOT` (0.16%/0.26%) per ADR-012 (da
    ri-verificare prima di un eventuale go-live)
  - `SlippageModel` (ADR-013): rate = max(half_spread, base_cost_bps) ×
    size_adj, con size_adj = 1 + impact_coeff·notional/ADV. Floor di
    default 2 bps, market impact off di default (trascurabile fino a
    ~100k EUR su Tier 1)
  - `TransactionCostModel` = fee + slippage (il round-trip cost di L1.04)
  - `estimate_half_spread_bps()`: proxy crudo di spread dal range OHLC
    (non abbiamo bid/ask, Q23) — lower-quantile del range rolling come
    stima conservativa del floor; da rivedere se arriveranno spread reali
- **15 nuovi test** (`tests/test_costs.py`): fee maker/taker + sign,
  floor vs spread, market impact, validazioni, proxy di spread. **117/117
  pytest verde**, ruff pulito, pyright pulito su `src/backtest`

### 2026-05-30 — Sessione 4 (cont.): indicatori tecnici
- **Nuovo package** `src/features/` con `indicators.py`: SMA, EMA, MACD
  (line/signal/hist), RSI (Wilder, gestione casi limite all-gain/all-loss
  → 100/0 e flat → 50), Bollinger Bands (mid/upper/lower, std ddof=0),
  ATR (Wilder, true range), OBV (volume firmato dalla direzione del close)
  - Tutte funzioni pure su Series/OHLCV, **causali per costruzione**:
    ogni valore a `t` usa solo dati ≤ `t` (rolling/ewm backward); le
    posizioni iniziali a finestra non piena sono NaN (mai back-fill)
  - Asset-class-agnostic (ADR-014): finestre in osservazioni, nessuna
    assunzione di calendario o scala crypto
- **17 nuovi test** (`tests/test_indicators.py`): valori noti SMA/EMA,
  identità MACD hist = macd−signal, RSI bounded [0,100] + casi limite,
  struttura Bollinger + collasso a std zero, ATR su range costante, OBV
  signing, validazioni colonne/parametri, e **test esplicito di
  non-look-ahead** (appendere una barra futura non cambia i valori
  passati). **134/134 pytest verde**, ruff pulito, pyright pulito su
  `src/features`
- Material di base per il futuro capitolo educational L2 sugli indicatori
  (ADR-015), da scrivere quando li useremo nei modelli baseline

### 2026-05-30 — Sessione 4 (cont.): modelli baseline (opzione A, no statsmodels)
- **Nuovo package** `src/models/` con `baseline.py`:
  - `random_walk_forecast` (martingala: forecast = 0 ovunque, il null
    "do nothing") e `momentum_forecast` (media mobile trailing dei
    rendimenti, `shift(1)` per garantire causalità: f[t] usa solo r<t)
  - `returns_from_prices`, `signal_from_forecast` (segno → posizione in
    {-1,0,+1}, **long-only di default** per spot ADR-012, NaN→flat),
    `strategy_returns` (gross = pos×ret; con cost model addebita
    turnover |Δpos|×cost_rate, entry da flat al t0)
  - Metriche di forecast: `directional_accuracy` (esclude periodi flat/NaN
    → random walk dà NaN per costruzione, corretto) e `mean_absolute_error`
  - **Scelta**: ARIMA rimandato per non aggiungere `statsmodels` ora
    (è in ADR-009 ma non in `pyproject.toml`); random walk + momentum non
    richiedono nuove dipendenze
- **16 nuovi test** (`tests/test_baseline.py`): returns, RW all-zero,
  momentum trailing-mean + causalità, signal sign/long-only/short/NaN,
  strategy returns gross e con turnover (cost model zero vs non-zero),
  RW non tradea mai, directional accuracy (perfetta/metà/NaN su RW), MAE.
  **150/150 pytest verde**, ruff pulito, pyright pulito su `src/models`
### 2026-05-30 — Sessione 4 (cont.): notebook backtest OOS end-to-end
- **`notebooks/04_baseline_backtest.ipynb`** (eseguito, output embedded):
  chiude il criterio di completamento Fase 2. Pipeline reale su BTC/ETH/LINK
  (Yahoo daily 2018-2026, scaricati con `fetch_tier1.py`):
  indicatori/forecast → walk-forward expanding (train=365/test=90, metriche
  solo sui test windows) → costi (Binance taker 0.10% + slippage 2 bps) →
  confronto vs buy-and-hold + DCA. **Ipotesi H1-H3 scritte prima dei
  risultati** (metodologia CLAUDE.md)
- **Risultati reali OOS** (~2700 oss/asset):
  - Directional accuracy momentum: BTC 0.515, ETH 0.503, LINK 0.488 →
    edge marginale e **non robusto** (negativo su LINK)
  - Random walk batte sempre momentum su MAE (forecaster puntuale): i
    daily return sono rumore (H1 confermata)
  - Momentum *net* batte buy-and-hold in Sharpe/drawdown su BTC (1.29 vs
    0.96) ed ETH (1.16 vs 0.85) ma **non** su LINK (0.82 vs 0.96). Il
    valore è **difensivo** (stare flat nei crash → MDD -0.50 vs -0.77 su
    BTC), non direzionale. 2 su 3 → **non è un segnale** (CLAUDE.md)
  - Costi erodono ~25-30% del return lordo, hit_rate netto < 0.50 (H3
    confermata)
- **Bias documentati nel notebook**: look-ahead evitato; survivorship
  (BTC/ETH/LINK sono i vincitori → numeri ottimistici); DCA non
  comparabile time-weighted (serve IRR money-weighted); metriche full-OOS
  nascondono instabilità di regime
- **Dati**: `data/raw/yahoo/` ripopolato (gitignored, fuori repo). Il
  notebook resta tracciato con output embedded come 01/02/03
- 150/150 pytest ancora verde, ruff pulito (notebooks esclusi da lint)
- **Prossimi step**: ARIMA (+`statsmodels`), decomposizione regime-aware
  delle metriche, IRR per confronto DCA corretto, sensibilità al lookback

### 2026-05-30 — Sessione 4 (cont.): revisione di programma + CI
- **Revisione di allineamento** (richiesta dall'utente: "ogni tanto rivedi
  se il programma procede come dovrebbe"). Riletti VISION/OPEN_QUESTIONS/
  ROADMAP/DECISIONS vs stato reale di codice/test/PR. Esito: allineamento
  buono coi criteri di successo VISION (#2 framework backtesting, #3
  baseline OOS, #4 documentare cosa non funziona — tutti onorati), scope
  disciplinato, codice sano (150 test, ratio test/src ~0.6). Debiti
  rilevati e affrontati:
  - **CI assente** → aggiunta `.github/workflows/ci.yml` (uv + ruff su
    src/tests + pytest, pyright bloccante sui moduli core puliti
    backtest/features/models e informativo sul resto: ~147 finding
    pre-esistenti di pandas-stubs in ingestion, tracciati come debito)
  - **PR draft sovrapposte** → #3 (doc review) mergiata in `main`, #4
    (Fase 2) rebasata su `main` aggiornato (history pulita)
  - **Q11 "sideways"** mal etichettata Fase 2 → ri-tag a Fase 4 (serve solo
    quando un modello produrrà l'output a 3 stati ADR-007; i baseline usano
    segnale binario)
  - **CLAUDE.md "Stato attuale"** → aggiornato a "Fase 2 in corso"
  - Falso allarme verificato: il blocco `ADR-NNN` in fondo a DECISIONS.md è
    un template dentro commento HTML, intenzionale — non toccato
- **Nota CI**: pyright resta verde solo su `src/{backtest,features,models}`;
  ripulire ingestion dal rumore pandas-stubs è un task futuro a parte
- **CI verde al primo run** (run 26679640442): ruff + pytest + pyright core

### 2026-05-30 — Sessione 7: avvio Fase 3 (bloccata da allowlist)
- **Fasi 2 e 2.1 mergiate in `main`** (PR #4 e #5 squash-merged, CI verde).
  `main` = `c3f52d2`
- **Avviata Fase 3** (sentiment & notizie). Primo deliverable (ingestion
  news) costruito come **scaffold testato offline**:
  - `src/ingestion/news/`: `NewsItem` (shape canonica tz-aware + dedup id),
    `NewsSource` ABC, `parse_rss` (RSS 2.0/Atom via stdlib `xml.etree`, zero
    nuove dipendenze), `RSSNewsSource` (fetch HTTP + backoff 429)
  - **11 test** (`tests/test_news.py`) su fixture RSS/Atom inline: parsing,
    dedup, skip malformati, invariante tz-aware, source con sessione fake.
    **177/177 pytest verde**, ruff pulito, pyright pulito (`rss.py` strict)
  - Q12 (allineamento temporale) deciso nello scaffold: si usa il
    **publication-time** del feed (unico timestamp affidabile) → da
    formalizzare in ADR
  - PR #6 (draft, CI verde), branch `claude/phase-3-sentiment-news`
- **BLOCCO scoperto**: network policy ad allowlist blocca news + HuggingFace.
  L'utente ha aggiornato l'allowlist ma **non ha effetto sulla sessione
  corrente** (proxy fissato all'avvio container) → serve ambiente nuovo
- **Decisione utente**: pausa Fase 3, riprendere a pipeline completa in nuova
  sessione con rete attiva (invece di accumulare codice non eseguito). Vedi
  blocco "Ripresa prossima sessione" in testa per i dettagli operativi

### 2026-05-30 — Sessione 6: robustezza baseline (Fase 2.1)
- **Scelta**: prima di aprire Fase 3, consolidare la robustezza dei baseline
  (CLAUDE.md: "diffida dei backtest brillanti"). Due bandiere rosse del
  notebook 04 chiuse
- **Nuovo modulo testato** `src/backtest/walkforward.py`: promossa la logica
  OOS inline del notebook 04 a codice riutilizzabile (`oos_strategy_returns`,
  `oos_index_start`). **6 test** (`tests/test_walkforward.py`): selezione
  solo test-windows, no overlap, RW flat, costi mordono, expanding==rolling
  per le finestre OOS. Importato direttamente (non in `__init__`) per
  evitare cicli con `models`
- **Notebook 05** (`05_baseline_robustness.ipynb`, eseguito) su **tutti e 5**
  i Tier 1. Ipotesi H5/H6 scritte prima dei numeri:
  - **H5 (robustezza lookback) confermata 4/5**: Sharpe-vs-lookback è una
    collina (non picco). `beats_bh`: POL 7/8, ETH 5/8, SOL 5/8, BTC 4/8,
    **LINK 2/8** (fragile). Il risultato del notebook 04 non era artefatto
  - **H6 (danno = whipsaw da volatilità) SMENTITA**: corr vol↔Δsharpe(bear)
    = **−0.09**. Il momentum protegge 4/5 *inclusi i due più volatili*
    (SOL vol 1.20, POL vol 1.41). LINK (vol 1.16) è l'unico che danneggia
    (Δsharpe −0.94) → **outlier specifico di LINK, non pattern di vol**
- **Esito netto**: l'edge difensivo è **più robusto del previsto**
  (cross-asset + cross-lookback), e LINK è un caso studio isolato da
  indagare (aggiunto a OPEN_QUESTIONS come Q25)
- **160 → 166/166 pytest verde** (+6 walkforward), ruff pulito, pyright
  core pulito
- Branch dedicato `claude/phase-2.1-baseline-robustness` (da `main`
  post-merge Fase 2)

### 2026-05-30 — Sessione 5: consolidamento Fase 2
- **Scelta utente**: consolidare invece di aprire nuovi filoni. Fase 2
  marcata **completata** in ROADMAP/STATUS; i 6 residui spostati in una
  nuova sezione **Fase 2.1** (backlog di qualità non bloccante)
- **PR #4 promossa da draft a ready-for-review** (CI verde su `ee61842`,
  160/160 test). Il criterio di completamento Fase 2 è dichiarato raggiunto
- Nessuna modifica al codice: solo allineamento documentale + stato PR

### 2026-05-30 — Sessione 4 (cont.): analisi regime-aware
- **Scelta** (utente: "scegli tu il percorso migliore"): regime-aware invece
  di ARIMA. Motivo: il notebook 04 aveva prodotto un risultato che
  *richiedeva* approfondimento (il momentum vince solo difensivamente), ed
  è una domanda di ricerca aperta (OPEN_QUESTIONS: "regimi distinguibili?").
  ARIMA avrebbe aggiunto `statsmodels` per un baseline che le evidenze danno
  per perdente; il debito pyright è manutenzione pura. Regime-aware sblocca
  conoscenza
- **Nuovo modulo** `src/features/regime.py`:
  - `classify_regime` causale: bull se `close[t] >= SMA(window)[t]`, else
    bear; warm-up = unknown (escluso, non indovinato). Default window 200
  - `summarize_by_regime`: decompone uno stream di rendimenti per regime
    (full/bull/bear) riusando `summarize`; allineamento causale
  - `regime_fractions`: quota di tempo per regime
  - **Proxy trasparente, non regime-switching model** (HMM resta Fase 5)
- **10 nuovi test** (`tests/test_regime.py`): warm-up unknown, rising→bull,
  falling→bear, **causalità** (barra futura non cambia label passate),
  separazione bull/bear, esclusione unknown, fractions. **160/160 verde**,
  ruff pulito, pyright pulito su `src/features`
- **Notebook 04 esteso** (sezione 5b + H4 scritta prima dei numeri,
  rieseguito): decomposizione per regime di buy_hold vs momentum_net
- **Risultato chiave (H4 confermata su BTC/ETH, smentita su LINK)**:
  - Bear BTC: momentum maxDD -0.64 vs B&H -0.92, Sharpe -0.44 vs -0.81 →
    **protezione reale**. Idem ETH (-0.64 vs -0.95; -0.19 vs -0.62)
  - Bull: momentum *sotto* B&H su tutti e tre (entra tardi, paga whipsaw)
  - **LINK bear: momentum Sharpe -2.04 vs B&H -1.10** → il filtro di trend
    viene fatto a pezzi dal whipsaw → spiega perché LINK perde nel
    full-sample. La robustezza cross-asset va dimostrata, non assunta
  - **Conseguenza**: il benchmark da battere è **regime-dependent**, non
    uno scalare. Motiva la direzione regime-aware/per-asset di Fase 3+

## Prossimo step

1. **Apertura Fase 2** — Baseline tecnica & backtesting rigoroso (vedi
   ROADMAP). Hook empirici dalla Fase 1 documentati in "Note per la
   prossima sessione" qui sotto
2. **Stretch goal Fase 1** ancora aperti (non bloccanti per Fase 2):
   - Blockchain.com (BTC on-chain base) — non richiede API key
   - Granularità intra-day via Binance già esposta ma non ancora usata
   - Schedulare l'esecuzione di `fetch_coingecko` / `fetch_etherscan`
     (cron locale o GitHub Actions) per popolare history nel tempo —
     pattern ora pronto via ADR-022
   - Estendere `fetch_fred.py` con altre serie macro su demand
     (housing, sentiment, ecc.) — base ormai c'è
3. **Educational stream**: livello L1 chiuso (10/10). I prossimi
   capitoli appartengono a L2 (Smart Investor) e si scriveranno
   parallelamente alla Fase 2 (bias cognitivi, cicli/regimi, risk
   management) o Fase 3 (sentiment, FOMO)
4. **(Fase 2 preview)** Regime clustering / regime-switching sulle
   correlazioni rolling crypto-macro — direttamente ispirato dall'EDA
   appena fatta. Le std rolling 0.12-0.17 dei rolling crypto vs macro
   sono il segnale concreto che i regimi esistono e vale la pena
   modellarli

### 2026-05-29 — Sessione 3 (cont.): EDA crypto vs FRED macro
- **Nuovo notebook** `notebooks/03_crypto_vs_fred_macro.ipynb`
  (eseguito), focus su tassi USA + curve slope + CPI/M2/UNRATE che
  Yahoo non dà. Stessa filosofia del 02 ma su variabili macro
  fundamentals invece di equity indices
- **Panel daily** (1232 giorni comuni 2020-04 → 2025-03):
  - BTC vs ΔDTWEXBGS = **-0.18** (conferma headwind dollaro già visto
    con DXY nel 02; due paniere indipendenti, stesso segnale)
  - BTC vs Δrate (DFF, 2Y, 10Y): tutti ~0 → variazioni di tasso
    *intraday* non muovono crypto; il segnale vive a frequenze più basse
  - BTC vs Δslope curve = +0.054 (curva più ripida → BTC marginalmente
    positivo, segnale debole)
  - **Yield curve invertita nel 43.8% dei giorni del sample**
    (vs 25.9% sull'intero 2018-2026, perché il window comune copre
    l'episodio 2022-2024 in pieno)
- **Panel monthly** (59 mesi, aggregando BTC EoM vs FRED monthly):
  - **BTC vs CPI YoY = -0.40** ⚠️ **forte negativa**. Smonta la
    narrativa "BTC = inflation hedge" almeno per il sample disponibile:
    inflazione su → Fed hike → BTC giù. Stesso pattern visto nei dati
    daily ma con segnale molto più forte alla frequenza giusta
  - BTC vs M2 YoY = +0.18 (debole positiva, coerente con "money
    printer go brrr")
  - BTC vs Δunemployment = -0.04 (zero)
  - M2 YoY vs Δunemployment = -0.60 (relazione macroeconomica classica)
- **Insight metodologico**: la differenza tra correlazione daily ~0 e
  monthly -0.40 è la conferma empirica che le **variabili macro
  agiscono su orizzonti più lunghi**. Per i modelli predittivi serve
  separare features ad alta vs bassa frequenza
- **Look-ahead bias da risolvere in Fase 2**: CPI/M2/UNRATE sono
  dated alla *reference month* ma pubblicate ~1-2 mesi dopo. Per
  signal generation serio servirà allineamento a release date (FRED
  ha l'API `vintagedates` per questo). Per la EDA descrittiva attuale,
  date di FRED OK
- ~~**Known issue minore** in `03_crypto_vs_fred_macro.ipynb` cell 8: il
  reporting "inversion spans >= 10 consecutive days" usa
  `idxmin/idxmax` su una boolean Series — restituisce posizioni
  sbagliate. Il count totale (540/1233 = 43.8%) è corretto, solo la
  tabella per-span no. Polish per la prossima volta che si tocca il
  notebook~~ **Risolto in sessione 3**: refactor con run-length
  encoding via groupby su DataFrame `{date, run}`. Output corretto:
  1 sola span >=10 giorni, di **536 giorni dal 2022-07-06 al 2024-08-26**
  — la più lunga inversione della curva 2Y-10Y della storia moderna USA.
  Numeri consistenti col total count (4 giorni isolati in span da 1-9
  giorni)

### 2026-05-29 — Sessione 3 (cont.): educational L1.03
- Pubblicato `education/L1_principiante/03_lettura_grafico.md`:
  candele OHLC, timeframe, scala log vs lineare, volume con caveat
  cross-venue (collegamento esplicito a Q23), onestà su pattern di
  analisi tecnica e hindsight bias, collegamento ai notebook EDA
  esistenti come "alternativa quantitativa al guardare il grafico ad
  occhio"

### 2026-05-29 — Sessione 3 (cont.): educational L1.04
- Pubblicato `education/L1_principiante/04_fee_spread_slippage.md`:
  i tre costi (fee dichiarata, spread invisibile, slippage
  size-dependent) con esempi numerici concreti su BTC e su altcoin
  illiquide; concetto di **round-trip cost** come metrica vera; trucco
  "fee 0%" del PFOF spiegato; collegamento esplicito a ADR-012/ADR-013
  (modello di slippage del paper trader) e ai limiti dei dati raw
  che abbiamo (no bid/ask nei parquet → spread va stimato)

### 2026-05-29 — Sessione 3 (cont.): educational L1.05
- Pubblicato `education/L1_principiante/05_portafoglio_diversificazione.md`:
  distinzione rischio sistematico vs idiosincratico, **uso esplicito
  dei numeri di correlazione dei nostri notebook** (BTC↔ETH 0.81,
  BTC↔SPX 0.39, BTC↔GOLD 0.08, BTC↔DXY -0.21) per mostrare quale
  diversificazione funziona davvero; equal weight vs market cap vs
  convinzione vs risk-parity; ribilanciare come strategia contrarian;
  errori classici; cash come asset con opzionalità

### 2026-05-29 — Sessione 3 (cont.): educational L1.06
- Pubblicato `education/L1_principiante/06_dca_dollar_cost_averaging.md`:
  DCA vs lump sum, **risultato Vanguard onesto** (lump sum batte DCA
  ~66% delle volte su 10 anni), perché il DCA è raccomandato comunque
  per ragioni psicologiche e per chi ha solo flusso da stipendio,
  variante value averaging, specificità crypto, collegamento esplicito
  al fatto che **DCA sarà il benchmark più rilevante in Fase 6** —
  battere buy-and-hold non basta, va battuto anche il DCA mensile

### 2026-05-29 — Sessione 3 (cont.): educational L1.07
- Pubblicato `education/L1_principiante/07_volatilita_drawdown.md`:
  vol come "energia cinetica" simmetrica vs drawdown come "dolore
  reale", tabella con vol annualizzata dei nostri Tier 1 (BTC 65%,
  ETH 85%, LINK 115%, SOL 119%, POL 136% dai notebook EDA), max DD
  storici BTC (−84% nel 2018, −77% nel 2022), recovery time + time
  underwater, distinzione vol ≠ drawdown con esempio UST-Terra come
  caso "bassa vol → alto DD latente nel tail", introduzione concettuale
  Sharpe/Sortino/Calmar, volatility clustering come ponte verso GARCH
  in Fase 2, collegamento esplicito ad ADR-007 (vol è dimensione di
  output del sistema)

### 2026-05-29 — Sessione 3 (cont.): Etherscan come quinto provider Tier 1
- **API key Etherscan** ottenuta gratis da
  https://etherscan.io/myapikey, salvata in `.env` (gitignored)
- **Nuovo file** `src/ingestion/tier1/etherscan.py` con `EtherscanSource`:
  - Etherscan v2 multi-chain endpoint (chainid parametrizzato; default
    Ethereum mainnet, supporto Polygon 137 disponibile)
  - Eredita solo da `DataSource` (snapshot stato corrente, non OHLCV);
    metodi: `fetch_eth_supply`, `fetch_eth_supply_components`,
    `fetch_gas_oracle`, `fetch_eth_price`, `fetch_token_supply`
  - **Envelope handling**: Etherscan ritorna HTTP 200 anche su errori
    logici (status="0", message="NOTOK", result=reason). Il source
    detecta e ri-lancia come `RuntimeError`
  - **Wei stored as string**: i valori in wei (10^26+ per ETH supply,
    10^27 per token supply) sfondano int64 → memorizzati come stringa
    decimale per esattezza, accanto al float "human" (ETH/LINK/POL
    interi) per analisi
  - Retry+backoff esponenziale per 429 (3 retry, base 5s)
  - Tier 1 ERC-20 contract addresses (LINK, POL post-rebrand) come
    costanti del modulo; rimandare al modello Asset solo se servirà a
    più moduli
- **Nuovo script** `src/ingestion/tier1/fetch_etherscan.py`: 6 snapshot
  in ~5 secondi
- **12 nuovi test** (`tests/test_etherscan.py`, no network): envelope
  parsing OK + envelope error mapping, wei string preservation,
  retry recovery + exhaustion, params propagation. **60/60 pytest
  verde, lint pulito**
- **Fetch reale completato** (~5 secondi):
  - **ETH supply 122,373,866** ETH (snapshot 2026-05-29)
  - Components: 2.94M ETH in staking, **4.63M ETH bruciati cumulativi
    post-EIP-1559**, 14.02M withdrawn post-Shapella → ETH è
    deflationary on net per chi guarda burn vs issuance
  - **Gas oracle 0.19 gwei** (safe/propose/fast tutti vicini) — il
    gas mainnet 2026 è crollato per migrazione massiva su L2
    (Optimism/Arbitrum/Base). Signal storico rilevante
  - LINK supply 1B (hard cap confermato)
  - POL supply 10.65B (compatibile con il rebrand MATIC→POL del 2024)
- **Cross-check ETH price su 3 fonti** (snapshot odierno):
  - Etherscan aggregated: $2,006.63
  - Yahoo last close: $2,022.20 (−0.77% vs Etherscan)
  - Binance.us last close: $1,985.71 (+1.05% vs Etherscan)
  - Tutto entro ±1%, consistente con il fatto che le tre fonti hanno
    snapshot intraday/EOD diversi ma allineati al momento
- **Q24 estesa**: ora ci sono **cinque** snapshot da Etherscan
  che vengono sovrascritti ogni run (oltre ai 2 di CoinGecko già
  noti). La pipeline append-to-history per dominance / gas / supply
  storica diventa ancora più desiderabile prima di Fase 2

### 2026-05-29 — Sessione 3 (cont.): chiusura Q24 con ADR-022
- **Nuovo modulo** `src/ingestion/snapshot.py` con `write_snapshot()`:
  funzione pura, due modi
  - **Single-row** (DataFrame con DatetimeIndex `snapshot_at`): dedup
    sull'index, idempotente nello stesso minuto
  - **Multi-row** (top-N indexed by `rank`, ecc.): aggiunge colonna
    `snapshot_at`, dedup su `(snapshot_at, *primary_key)`
- **Scrittura ordinata**: history first, latest after (un latest stale
  è recuperabile dalla history; il contrario no)
- **7 nuovi test** (`tests/test_snapshot.py`, no network): primo run
  crea entrambi i file, history accumula timestamp distinti, idempotente
  nello stesso minuto, multi-row con primary_key dedup, empty frame
  skip, history sopravvive a cancellazione accidentale del latest.
  **67/67 pytest verde, lint pulito**
- **Integrazione** in `fetch_coingecko.py` (global + top-20) e
  `fetch_etherscan.py` (5 snapshot single-row + 2 multi-row per
  token supply). Fetch reali eseguiti:
  - `global_history.parquet`: 1 riga (BTC dom 57.59%, ETH 9.49%,
    USDT 7.42% — snapshot delle 22:13 UTC)
  - `top_20_history.parquet`: 20 righe (rank 1-20 con `snapshot_at`)
  - Etherscan 6 history files popolati
- **Etherscan pacing fix**: il rate-limit dichiarato 5/sec è in realtà
  3/sec osservato → `DEFAULT_SLEEP_BETWEEN_CALLS` da 0.25s a 0.4s.
  Errore arrivava come envelope `status=0 + result="rate limit"`,
  diverso da HTTP 429
- **Q24 chiusa** (ADR-022). Pattern riutilizzabile per qualunque
  futuro provider snapshot-based (Blockchain.com BTC on-chain,
  FRED ALFRED vintages, ecc.)

### 2026-05-29 — Sessione 3 (chiusura): completamento L1 (capitoli 08-10)
- **L1.08 Custodia**: not your keys not your coins, custodial vs hot
  vs cold wallet, casi storici (Mt.Gox/FTX/Celsius), seed phrase su
  carta o acciaio mai cloud, multisig per importi grandi, 3 profili
  pratici (500 EUR / 5-30k EUR / 50k+), collegamento al sistema (no
  trading reale, API key sempre read-only)
- **L1.09 Fiscalità essenziale**: disclaimer triplo (non consulenza,
  evasione è reato), framework italiano (26% imposta sostitutiva +
  quadro RW + IVAFE 0.2%), eventi tassabili (incluso swap
  crypto→crypto), staking/airdrop/mining/hard fork, FIFO/LIFO/costo
  medio, tool pratici (Koinly/CTC), DAC8 chiude la "crypto invisibile",
  errori frequenti, collegamento al fatto che il sistema produce
  rendimenti **lordi**
- **L1.10 Cosa NON è il trading**: il capitolo "anti-fuffa" finale —
  statistiche regolamentari (70-97% retail perde), promesse rosse
  decodificate (rendimenti garantiti, "segreto nascosto", alta winrate
  → tail catastrofica, backtest senza walk-forward = marketing),
  modelli di business dei guru (affiliate/segnali/pump-and-dump),
  survivorship bias, cosa funziona davvero (ETF + DCA + tempo), red
  flags vs green flags, esplicito invito ad applicare lo **stesso
  scetticismo al nostro progetto**

- **L1 ora 10/10 capitoli pubblicati** — livello chiuso. Indice L1
  aggiornato a "L1 completo (2026-05-29)" con pointer a L2 come
  prossimo livello (scrivibile durante Fase 2-3)

## Note per la prossima sessione

### Stato a fine sessione 3 (2026-05-29)
- **Fase 1 chiusa** nella ROADMAP (criterio di completamento soddisfatto)
- **5 data provider** integrati e funzionanti (Yahoo, Binance.us,
  CoinGecko, FRED, Etherscan); **3 notebook EDA** eseguiti con
  findings documentati; **snapshot history pattern** attivo (ADR-022);
  **POL canonical multi-source** (ADR-019/020/021); **L1 educational
  chiuso** (10/10); **67/67 pytest verde**, lint pulito
- **Branch**: PR #2 (`claude/yahoo-finance-connection-2Qy92`) mergiata
  in `main` — chiude formalmente Fase 1 nel repo. Il lavoro di doc
  review prosegue su `claude/review-project-docs-YlHSL`
- **ADR registrati**: ADR-001 ÷ ADR-022 in `DECISIONS.md`
- **`.env`** ha `FRED_API_KEY` e `ETHERSCAN_API_KEY` (gitignored).
  Entrambe sono nel transcript di sessione 3 — rigenerabili dai
  rispettivi portali se l'utente vuole ruotarle

### Prima cosa da chiedere all'utente al riavvio
Decisione di igiene del repo:
1. **Mergiare PR #2 in main** (chiude formalmente Fase 1 nel repo)
   e iniziare Fase 2 su **nuovo branch** con nome decente
   (es. `claude/phase-2-baseline-backtest`) — *raccomandato*
2. **Continuare sullo stesso branch** (più semplice, ma la PR diventa
   sempre più ingestibile da rivedere)
3. **Altro** (es. Blockchain.com per BTC on-chain prima di Fase 2,
   o schedulare i fetch snapshot per popolare history nel tempo)

### Se la scelta è "Fase 2" (più probabile)
Hook empirici concreti da Fase 1 che vincolano il design:
- **Volatility clustering** ACF(|r|) lag 1 = 0.16-0.27 → GARCH(1,1)
  come baseline naturale per varianza condizionata
- **Rolling correlation std 0.12-0.17** → regime detection
  (HMM o clustering su rolling correlation vectors) probabilmente
  da spostare avanti da Fase 5 a Fase 2
- **BTC vs CPI YoY mensile = −0.40** → almeno una macro feature deve
  essere nella shortlist baseline, non solo prezzo
- **Yield curve slope FRED** già pronta come potenziale regime feature
  (inverted 25.9% dei giorni 2018-2026, 536 giorni consecutivi
  2022-07-06 → 2024-08-26)
- **L1.04 fee/spread/slippage** è il prerequisito mentale per ADR-013
  (modello di slippage del paper trader); ADR-007 fa di "vol attesa"
  una dimensione di output del sistema

### Promemoria operativi
- Leggere PRIMA `CLAUDE.md` e questo file. Tutte le decisioni
  architetturali in ADR-001 ÷ ADR-022 (`DECISIONS.md`). Non rimettere
  in discussione lo scope senza motivo concreto
- Convenzioni cartelle e principio asset-class-agnostic (ADR-014):
  mai hardcodare "crypto" — usare l'Asset model
- Open question rimaste: **Q23** (volume cross-venue, non bloccante
  per Fase 2 a meno di feature volume-based), **Q18** (granularità
  educational, non bloccante)
- I 5 provider esistenti sono il **reference pattern** per nuove
  fonti. Per snapshot single-state (es. blockchain stats), template
  più recente: `src/ingestion/tier1/etherscan.py` + `fetch_etherscan.py`
  con `write_snapshot()`. Per time series con API key, template:
  `src/ingestion/tier1/fred.py`. Per cross-validated multi-source,
  pattern composer: `src/ingestion/composer.py`
- I tier 2, 3, 4 di asset NON vanno toccati in Fase 1 (ADR-017)
- `src/ai/` e `src/execution/` sono solo placeholder: non
  implementare nulla finché Fase 3 / Fase 6 rispettivamente
- Se servisse popolare la history Etherscan/CoinGecko nel tempo (per
  avere serie storiche di gas / dominance prima di Fase 2), basta
  schedulare i fetch (cron locale, GitHub Actions, ecc.). Pattern
  pronto via ADR-022
