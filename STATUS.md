# STATUS.md

> Stato corrente del progetto. **Aggiornare a ogni sessione.**
> Questo è il primo file che chi (umano o agente) riprende il lavoro deve leggere.

---

## Ultimo aggiornamento
2026-05-28

## Fase corrente
**Fase 1 — Esplorazione dati** ⏳ *in corso (parte fondazionale completata, fetch reale bloccato da network policy)*

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

## Cosa è in corso
- Niente di attivo a fine sessione

## Blocker
- 🛑 **Network policy dell'ambiente blocca outbound HTTPS** verso le fonti
  dati. Verificato: `query2.finance.yahoo.com`, `api.binance.com`,
  `api.coingecko.com` rispondono tutti `403 Host not in allowlist`.
  Lo script di ingestion è funzionante (struttura, parsing, persistenza
  validati) ma non può scaricare dati reali finché l'allowlist non viene
  aggiornata.

  **Cosa serve fare** (richiede intervento utente nella config ambiente
  Claude Code on the web):
  - Aprire la policy per i domini elencati in `docs/data_sources_tier1.md`
    sezione "Prerequisiti operativi"
  - Rilanciare `uv run python -m src.ingestion.tier1.fetch_tier1`
  - Quindi eseguire il notebook EDA

## Prossimo step (Fase 1, continua)

1. **Sbloccare network** (utente lato config ambiente)
2. **Verificare fetch reale**: rilanciare `fetch_tier1`, controllare row counts
   e qualità dati (gap, NaN, copertura storica per ciascun asset)
3. **Eseguire notebook EDA** su BTC + ETH; documentare findings (skew,
   kurtosis, volatility clustering)
4. **Aggiungere sorgenti Tier 1 mancanti** (in ordine di valore):
   - Binance public API (granularità intra-day)
   - CoinGecko (top 20 dinamica + dominance + market cap)
   - FRED (tassi, CPI, M2) — richiede API key gratuita
   - Etherscan + Blockchain.com (on-chain base) — Etherscan richiede API key
5. **Capitolo educational L1.02**: tipi di ordine (collegato al fetch reale)
6. **Test su YahooFinanceSource** (mock di yfinance, no network)

## Note per la prossima sessione

- Leggere PRIMA `CLAUDE.md` e questo file. Tutte le decisioni architetturali
  e di scope sono fissate in ADR-001 ÷ ADR-018 (`DECISIONS.md`)
- Non rimettere in discussione lo scope senza motivo concreto
- Convenzioni cartelle e principio asset-class-agnostic (ADR-014): mai
  hardcodare "crypto" — usare l'Asset model
- Il codice della pipeline funziona, ha test che passano. Il prossimo step
  *dipende dal network*, quindi conviene chiedere all'utente conferma che
  l'allowlist sia stata aggiornata prima di rilanciare il fetch
- I tier 2, 3, 4 NON vanno toccati in Fase 1 (ADR-017)
- Il modulo `src/ai/` e `src/execution/` sono solo placeholder; non
  implementare nulla finché Fase 3 / Fase 6 rispettivamente
