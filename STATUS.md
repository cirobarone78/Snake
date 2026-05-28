# STATUS.md

> Stato corrente del progetto. **Aggiornare a ogni sessione.**
> Questo è il primo file che chi (umano o agente) riprende il lavoro deve leggere.

---

## Ultimo aggiornamento
2026-05-28

## Fase corrente
**Fase 0 — Framing & setup** ✅ *completata.*
**Fase 1 — Esplorazione dati** ⏭️ *pronti per iniziare.*

## Cosa è stato fatto

### 2026-05-28
- Repository svuotata dal precedente progetto (gioco Snake)
- Creati i 6 file di documentazione di base: `CLAUDE.md`, `VISION.md`,
  `ROADMAP.md`, `STATUS.md`, `DECISIONS.md`, `OPEN_QUESTIONS.md`
- **Decisioni critiche di Fase 0 chiuse** (ADR-001 … ADR-009 in `DECISIONS.md`):
  - Riutilizzo della repo "Snake" per il nuovo progetto (ADR-001)
  - Natura del progetto: ricerca, non trading bot (ADR-002)
  - Convenzioni linguistiche (ADR-003)
  - Scope: ricerca ora, live trading come obiettivo condizionale futuro (ADR-004)
  - Asset universe: Tier 1 (BTC, ETH, SOL, LINK, POL) + Tier 2 (top 20 dinamica) (ADR-005)
  - Multi-timeframe predittivo: breve (1–7gg), medio (2–8sett), lungo (3–12mesi) (ADR-006)
  - Output multi-dimensionale: direzione + rendimento + probabilità (+ vol, conf, factors) (ADR-007)
  - Budget dati: gratuiti prima, premium dopo (ADR-008)
  - Stack: Python 3.12+, uv, Jupyter, ruff, pyright, pandas/polars, scikit-learn, HuggingFace, PyTorch (ADR-009)
- **Paper trading promosso a fase dedicata** (ADR-010):
  - Nuova Fase 6 della roadmap (era "Output, dashboard" — diventata Fase 7)
  - Principi non negoziabili: no look-ahead, costi reali (fee+slippage+latency),
    stesso codebase paper/live, stato persistente, metriche coerenti col backtest
  - Aggiunte Q13–Q15 in `OPEN_QUESTIONS.md` (capitale virtuale, exchange di
    riferimento, modello slippage)
- **Paper trading parametrizzato** (ADR-011, ADR-012, ADR-013):
  - Multi-scenario con reset e fork (default: 1k / 10k / 100k EUR) (ADR-011)
  - Due broker modellati: Binance (default) e Kraken (utente reale) (ADR-012)
  - Slippage spread-proportional con floor 2 bps, market impact attivabile
    per ordini grossi (ADR-013)
- **Architettura asset-class-agnostic** (ADR-014):
  - Tutti i moduli (data, features, models, backtest, broker) sono
    `asset_class`-aware fin dalla Fase 1
  - Implementazione effettiva: solo crypto fino a Fase 6 inclusa
  - Espansione equity = Fase 8 dedicata, ma niente riscrittura
  - Aggiunte Q16, Q17 (universe equity, broker equity) in `OPEN_QUESTIONS.md`
- **Modulo didattico multi-livello** (ADR-015):
  - Stream parallelo, cresce in `education/` insieme alle fasi tecniche
  - 4 livelli: L1 principiante, L2 intermedio, L3 avanzato, L4 esperto/"wolf"
  - Capitoli scritti quando l'argomento è "fresco" perché lo stiamo
    implementando nel codice
  - Aggiunta Q18 (granularità) in `OPEN_QUESTIONS.md`

## Cosa è in corso
- Niente di attivo. Fine della sessione di framing.

## Prossimo step (Fase 1)
Inventario delle sorgenti dati + bootstrap educational. In ordine:

1. **Setup ambiente Python**: `uv init`, `pyproject.toml`, `uv.lock`,
   `.gitignore` con `data/`, `.env`, `__pycache__/`, `.venv/`, `*.ipynb_checkpoints`
2. **Struttura cartelle**: `src/`, `notebooks/`, `data/raw/`, `data/processed/`,
   `tests/`, `education/L1_principiante/`, `education/L2_intermedio/`,
   `education/L3_avanzato/`, `education/L4_esperto/`
3. **`education/README.md`** come indice navigabile dei livelli (ADR-015)
4. **Inventario sorgenti dati** per gli asset Tier 1 (BTC, ETH, SOL, LINK, POL):
   - Market data: CoinGecko, Binance public API, Coinbase, Yahoo Finance
     (per equity correlati). Documentare: storico disponibile, rate limit,
     campi forniti, licenza
   - On-chain (per BTC, ETH come prima istanza): Etherscan, Blockchain.com,
     Glassnode free tier, mempool.space
   - News: RSS feeds (Cointelegraph, CoinDesk, Reuters), CryptoPanic free tier
   - Macro: FRED (Federal Reserve), ECB SDW, Yahoo Finance (DXY, indici)
5. **Script di ingestion minimale** per OHLCV daily di 1-2 asset (BTC + ETH)
   → salvataggio in `data/raw/` come parquet. Codice asset-class-agnostic
   (ADR-014): tutti i parametri di asset class come configurazione, niente
   hardcoded "crypto"
6. **Notebook di esplorazione**: statistiche descrittive, distribuzioni
   rendimenti, autocorrelazione, stagionalità, identificazione finestre di
   halving Bitcoin
7. **Primo capitolo educational L1**: "Cos'è un asset, una borsa, un broker" —
   scritto in parallelo all'ingestion, perché tocca gli stessi concetti

## Blocker
Nessuno.

## Note per la prossima sessione
- Le ADR-004 ÷ ADR-009 sono **già prese** — non rimetterle in discussione
  salvo motivo concreto
- Prima di scrivere codice di ingestion: **leggere ADR-005** per ricordare
  i due tier di asset, e ADR-008 per limiti su API premium
- Convenzioni cartelle (da ADR-009): `src/`, `notebooks/`, `data/raw/`,
  `data/processed/`, `tests/`
- I dati in `data/` e i `.env` non vanno in commit: predisporre `.gitignore`
  come primo task
- Verificare se `uv` è disponibile nell'ambiente, in caso installarlo come
  prima cosa
