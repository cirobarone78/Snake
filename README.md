# Multifactor Market Analysis

Sistema sperimentale di **analisi multifattoriale dei mercati finanziari** con
focus sulle criptovalute. Integra dati di mercato, on-chain, macro, cicli e
sentiment estratto da notizie (finanza, tecnologia, geopolitica, politica)
per identificare segnali probabilistici sull'andamento di asset selezionati.

> **Stato**: Fase 1 in corso — esplorazione dati, sorgenti Tier 1.

## Documentazione del progetto

Prima di lavorare su questo progetto, leggere in quest'ordine:

1. [`CLAUDE.md`](./CLAUDE.md) — istruzioni operative per ogni sessione
2. [`STATUS.md`](./STATUS.md) — dove siamo ora
3. [`VISION.md`](./VISION.md) — obiettivo e principi
4. [`ROADMAP.md`](./ROADMAP.md) — fasi e deliverable
5. [`OPEN_QUESTIONS.md`](./OPEN_QUESTIONS.md) — decisioni ancora aperte
6. [`DECISIONS.md`](./DECISIONS.md) — decisioni già prese (ADR)
7. [`docs/data_sources_tier1.md`](./docs/data_sources_tier1.md) — inventario fonti dati
8. [`education/`](./education/) — modulo didattico multi-livello

## Quickstart

Richiede [`uv`](https://docs.astral.sh/uv/) installato.

```bash
# Installazione dipendenze (Python 3.12 incluso, gestito da uv)
uv sync

# Test e lint
uv run pytest -v
uv run ruff check src/ tests/

# Fetch dati Tier 1 (richiede network access, vedi sotto)
uv run python -m src.ingestion.tier1.fetch_tier1

# Esplorazione (Jupyter)
uv run jupyter notebook notebooks/01_exploration_btc_eth.ipynb
```

### Network access

L'ingestion ha bisogno di accesso outbound HTTPS verso le sorgenti elencate
in [`docs/data_sources_tier1.md`](./docs/data_sources_tier1.md). In ambienti
con allowlist (es. Claude Code on the web), configurare la policy per
includere almeno:

- `query1.finance.yahoo.com`, `query2.finance.yahoo.com`
- `api.binance.com`
- `api.exchange.coinbase.com`
- `api.coingecko.com`
- `api.etherscan.io`
- `api.blockchain.info`, `mempool.space`
- `api.glassnode.com`
- `api.stlouisfed.org` (FRED)
- `cryptopanic.com`

## Struttura

```
src/                       # codice del sistema (asset-class-agnostic, ADR-014)
  assets/                  # modello Asset, Tier 1 e context
  ingestion/               # data sources, organizzate per tier (ADR-017)
    tier1/                 # core: yahoo, binance, coingecko, etherscan, FRED, ...
  ai/                      # NLP (ADR-016): nlp_local (Layer 1), llm_api (Layer 2)
  execution/               # paper / live broker (ADR-010+)
notebooks/                 # esplorazione, EDA
data/raw/                  # dati grezzi (gitignored)
data/processed/            # dataset puliti (gitignored)
tests/                     # pytest
config/                    # configurazione (es. sources.yaml in iter successive)
education/                 # modulo didattico (ADR-015)
  L1_principiante/         # Investor 101
  L2_intermedio/           # Smart Investor
  L3_avanzato/             # Quantitative Investor
  L4_esperto/              # Wolf of Wall Street / Professional
docs/                      # documentazione tecnica (inventario fonti, ...)
```

## Natura del progetto

Ricerca quantitativa, **non** trading bot. Il rigore metodologico viene prima
dei risultati. Vedere `VISION.md` per i criteri di successo.
