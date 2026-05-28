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

## Cosa è in corso
- Niente di attivo. Fine della sessione di framing.

## Prossimo step (Fase 1)
Inventario delle sorgenti dati. In ordine:

1. **Setup ambiente Python**: `uv init`, `pyproject.toml`, `uv.lock`,
   `.gitignore` con `data/`, `.env`, `__pycache__/`, `.venv/`, `*.ipynb_checkpoints`
2. **Inventario sorgenti dati** per gli asset Tier 1 (BTC, ETH, SOL, LINK, POL):
   - Market data: CoinGecko, Binance public API, Coinbase, Yahoo Finance
     (per equity correlati). Documentare: storico disponibile, rate limit,
     campi forniti, licenza
   - On-chain (per BTC, ETH come prima istanza): Etherscan, Blockchain.com,
     Glassnode free tier, mempool.space
   - News: RSS feeds (Cointelegraph, CoinDesk, Reuters), CryptoPanic free tier
   - Macro: FRED (Federal Reserve), ECB SDW, Yahoo Finance (DXY, indici)
3. **Script di ingestion minimale** per OHLCV daily di 1-2 asset (BTC + ETH)
   → salvataggio in `data/raw/` come parquet
4. **Notebook di esplorazione**: statistiche descrittive, distribuzioni
   rendimenti, autocorrelazione, stagionalità, identificazione finestre di
   halving Bitcoin

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
