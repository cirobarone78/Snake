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
  - **POL: 1181 righe, 2020-08-07 → 2023-10-31 — anomalia**
    (vedi `OPEN_QUESTIONS.md` Q21: ticker POL-USD su Yahoo è troncato
    post-rebrand MATIC→POL del 2024)
  - DXY, SPX, NDX, GOLD: ~2111-2113 righe, 2018-01-02 → 2026-05-27
    (mercato chiuso nei weekend, normale)
- **Quality check superato**: 0 NaN, 0 gap "anomali" per tutti gli asset
- **Nota su network policy**: i 403 `host_not_allowed` riportati nella
  sessione precedente sono spariti — l'ambiente attuale permette outbound
  verso Yahoo. `fc.yahoo.com` (cookie/crumb endpoint usato da yfinance in
  alcuni casi) è ancora `host_not_allowed` ma non è necessario per il
  chart endpoint pubblico.

## Cosa è in corso
- Niente di attivo a fine sessione

## Prossimo step (Fase 1, continua)

1. **Risolvere quirk POL** (vedi `OPEN_QUESTIONS.md` Q21): decidere se
   passare a `MATIC-USD`, concatenare i due ticker, sostituire l'asset, o
   switchare provider per POL
2. **Eseguire notebook EDA** (`notebooks/01_exploration_btc_eth.ipynb`)
   su BTC + ETH; documentare findings (skew, kurtosis, volatility clustering)
3. **Aggiungere sorgenti Tier 1 mancanti** (in ordine di valore):
   - Binance public API (granularità intra-day)
   - CoinGecko (top 20 dinamica + dominance + market cap)
   - FRED (tassi, CPI, M2) — richiede API key gratuita
   - Etherscan + Blockchain.com (on-chain base) — Etherscan richiede API key
4. **Capitolo educational L1.02**: tipi di ordine (collegato al fetch reale)
5. **Test su YahooFinanceSource** (mock di yfinance, no network)

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
