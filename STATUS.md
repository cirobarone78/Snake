# STATUS.md

> Stato corrente del progetto. **Aggiornare a ogni sessione.**
> Questo è il primo file che chi (umano o agente) riprende il lavoro deve leggere.

---

## Ultimo aggiornamento
2026-05-29

## Fase corrente
**Fase 1 — Esplorazione dati** ✅ *completata (2026-05-29)*
→ pronti per **Fase 2 — Baseline tecnica & backtesting rigoroso**

ROADMAP aggiornata: deliverable Fase 1 tutti spuntati, hook empirici
da Fase 1 (volatility clustering, regime instability, BTC vs CPI YoY
−0.40) usati come vincoli per il design della Fase 2.

## Cosa è stato fatto

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

## Ultimo aggiornamento (sessione 3)
2026-05-29

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
- Niente di attivo a fine sessione

## Prossimo step (Fase 1, continua)

1. **Aggiungere sorgenti Tier 1 mancanti rimanenti** (in ordine di valore):
   - Etherscan + Blockchain.com (on-chain base) — Etherscan richiede API key
   - Granularità intra-day via Binance già esposta ma non ancora usata
   - Dominance time series (richiede Q24)
   - Estendere `fetch_fred.py` con altre serie macro su demand
     (housing, sentiment, ecc.) — base ormai c'è
2. **Capitolo educational L1.08**: custodia (cold/hot wallet vs
   exchange) — L1.07 volatilità/drawdown completato in sessione 3
3. **(Fase 2 preview)** Regime clustering / regime-switching sulle
   correlazioni rolling crypto-macro — direttamente ispirato dall'EDA
   appena fatta. Le std rolling 0.12-0.17 dei rolling crypto vs macro
   sono il segnale concreto che i regimi esistono e vale la pena
   modellarli

## Note per la prossima sessione

### Contesto generale
- Leggere PRIMA `CLAUDE.md` e questo file. Tutte le decisioni
  architetturali e di scope sono fissate in ADR-001 ÷ ADR-021
  (`DECISIONS.md`)
- Non rimettere in discussione lo scope senza motivo concreto
- Convenzioni cartelle e principio asset-class-agnostic (ADR-014): mai
  hardcodare "crypto" — usare l'Asset model
- Il codice della pipeline funziona, ha **48/48 test che passano**, e ha
  dati reali da 4 provider in `data/raw/{yahoo,binance,coingecko,fred}/`
  (gitignored), + serie POL canonica in `data/processed/POL_1d.parquet`
- I 4 provider esistenti sono il **reference pattern** per nuove fonti:
  vedere `src/ingestion/tier1/fred.py` per il template più recente
  (no OHLCV, metodi specializzati, retry su 429, API key obbligatoria
  via env)
- **Open question rilevanti**: Q24 (storage append per snapshot), Q23
  (volume cross-venue), Q18 (granularità educational)
- **Fase 2 hook empirico**: le std rolling 0.12-0.17 sulle correlazioni
  crypto-macro nel notebook 02 dicono che i regimi esistono. Quando
  apriremo Fase 2, partire da regime-switching o clustering su quelle
  rolling correlations
- **Nuovo dato disponibile per Fase 2**: yield curve slope FRED
  (DGS10-DGS2) come potenziale feature regime — già inverted nel
  25.9% dei giorni nel sample, segnale macro forte

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
- L1 ora **7/10 capitoli pubblicati**. Prossimo: L1.08 su custodia
  (cold/hot wallet vs custodia su exchange)
- I tier 2, 3, 4 NON vanno toccati in Fase 1 (ADR-017)
- Il modulo `src/ai/` e `src/execution/` sono solo placeholder; non
  implementare nulla finché Fase 3 / Fase 6 rispettivamente
