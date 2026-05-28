# STATUS.md

> Stato corrente del progetto. **Aggiornare a ogni sessione.**
> Questo è il primo file che chi (umano o agente) riprende il lavoro deve leggere.

---

## Ultimo aggiornamento
2026-05-28

## Fase corrente
**Fase 1 — Esplorazione dati** ⏳ *in corso (fetch reale completato, EDA da fare)*

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

## Cosa è in corso
- Niente di attivo a fine sessione

## Prossimo step (Fase 1, continua)

1. **Aggiungere sorgenti Tier 1 mancanti** (in ordine di valore):
   - Binance public API (granularità intra-day)
   - CoinGecko (top 20 dinamica + dominance + market cap)
   - FRED (tassi, CPI, M2) — richiede API key gratuita
   - Etherscan + Blockchain.com (on-chain base) — Etherscan richiede API key
   - Binance chiude anche il gap residuo POL (Q21bis)
2. **Capitolo educational L1.02**: tipi di ordine (collegato al fetch reale)
3. **Test su YahooFinanceSource** (mock di yfinance, no network)
4. **(Fase 2 preview)** Regime clustering / regime-switching sulle
   correlazioni rolling crypto-macro — direttamente ispirato dall'EDA
   appena fatta

## Note per la prossima sessione

- Leggere PRIMA `CLAUDE.md` e questo file. Tutte le decisioni architetturali
  e di scope sono fissate in ADR-001 ÷ ADR-018 (`DECISIONS.md`)
- Non rimettere in discussione lo scope senza motivo concreto
- Convenzioni cartelle e principio asset-class-agnostic (ADR-014): mai
  hardcodare "crypto" — usare l'Asset model
- Il codice della pipeline funziona, ha test che passano, e ora ha anche
  dati reali in `data/raw/yahoo/` (gitignored). Il prossimo step naturale
  è il notebook EDA, una volta risolto il dilemma POL
- I tier 2, 3, 4 NON vanno toccati in Fase 1 (ADR-017)
- Il modulo `src/ai/` e `src/execution/` sono solo placeholder; non
  implementare nulla finché Fase 3 / Fase 6 rispettivamente
