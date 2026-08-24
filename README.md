# Multifactor Market Analysis

> ⚠️ **Questa repository non contiene un gioco Snake.** Il nome è un residuo del
> progetto che occupava la repo prima del 2026-05-28 (vedi ADR-001) e non ha
> alcun legame con il contenuto attuale. Rinominarla è possibile ma non è una
> priorità (ADR-032, D10).

Sistema sperimentale di **analisi multifattoriale dei mercati finanziari**, nato
sulle criptovalute e oggi esteso agli ETF settoriali azionari. Integra dati di
mercato, on-chain, macro, cicli e sentiment estratto da notizie (finanza,
tecnologia, geopolitica, politica) per cercare segnali **probabilistici**
sull'andamento di asset selezionati.

È **ricerca quantitativa, non un trading bot**: il rigore metodologico viene
prima dei risultati, e gli esperimenti falliti sono documentati quanto quelli
riusciti — con la stessa evidenza.

> **Stato (2026-08-24)**: Fasi 0–8 chiuse o in accumulo dati; nessun edge
> predittivo direzionale daily trovato finora (il dettaglio misurato è in
> [`STATUS.md`](./STATUS.md)). È in corso la **Fase 9 — ranking ETF
> probabilistico** (ADR-032): probabilità calibrate di sovraperformance vs SPY a
> 20/60 sedute. Il piano operativo, in work package autonomi con ipotesi e barra
> di adozione scritte **prima** dei risultati, è in
> [`docs/PIANO_SVILUPPO.md`](./docs/PIANO_SVILUPPO.md).

## Documentazione del progetto

Prima di lavorare su questo progetto, leggere in quest'ordine:

1. [`CLAUDE.md`](./CLAUDE.md) — istruzioni operative per ogni sessione
2. [`STATUS.md`](./STATUS.md) — dove siamo ora (la cronaca delle sessioni
   passate sta in [`docs/STATUS_ARCHIVIO.md`](./docs/STATUS_ARCHIVIO.md))
3. [`VISION.md`](./VISION.md) — obiettivo e principi
4. [`ROADMAP.md`](./ROADMAP.md) — fasi e deliverable
5. [`OPEN_QUESTIONS.md`](./OPEN_QUESTIONS.md) — decisioni ancora aperte
6. [`DECISIONS.md`](./DECISIONS.md) — decisioni già prese (ADR)
7. [`docs/PIANO_SVILUPPO.md`](./docs/PIANO_SVILUPPO.md) — piano operativo della
   Fase 9 in work package (uno per PR)
8. [`docs/data_sources_tier1.md`](./docs/data_sources_tier1.md) — inventario fonti dati
9. [`education/`](./education/) — modulo didattico multi-livello

## Quickstart

Richiede [`uv`](https://docs.astral.sh/uv/) installato.

```bash
# Installazione dipendenze (Python 3.12 incluso, gestito da uv)
uv sync

# Test e lint (483/483 al 2026-08-24)
uv run pytest -q
uv run ruff check src tests

# Fetch dati Tier 1 (richiede network access, vedi sotto)
# Yahoo: crypto + indici + commodity (default)
uv run python -m src.ingestion.tier1.fetch_tier1
# Binance.us: cross-validation crypto (geo-blocked api.binance.com, ADR-020)
uv run python -m src.ingestion.tier1.fetch_tier1 --source binance
# CoinGecko: market chart + global dominance + top-20 (no API key needed)
uv run python -m src.ingestion.tier1.fetch_coingecko
# FRED: macro USA (tassi, CPI, M2, unemployment). Richiede FRED_API_KEY in .env
uv run python -m src.ingestion.tier1.fetch_fred
# Etherscan: ETH supply, gas, ERC-20 supply. Richiede ETHERSCAN_API_KEY in .env
uv run python -m src.ingestion.tier1.fetch_etherscan

# Piano di accumulo: quale asset della quota satellite + candidate a lungo
# termine. Legge config/dca_plan.yaml, scrive REPORT_DCA.md + il JSON del tab
uv run python -m src.ingestion.tier1.dca_cli
# Rifà da zero il backtest che valida (e ridimensiona) quella scelta
uv run python -m src.ingestion.tier1.dca_cli --validate

# Esplorazione (Jupyter): tre notebook EDA disponibili
uv run jupyter notebook notebooks/
```

### API key gratuite (per FRED e Etherscan)

- **FRED**: https://fredaccount.stlouisfed.org/apikeys
- **Etherscan**: https://etherscan.io/myapikey

Aggiungi in `.env` (gitignored) come:
```
FRED_API_KEY=...
ETHERSCAN_API_KEY=...
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
- `api.llama.fi` (DefiLlama: fees, revenue e TVL dei protocolli — **non ancora
  sbloccato**, vedi ADR-031: senza, la scheda fondamentale dei progetti misura
  solo *se* un meccanismo di cattura del valore esiste, non quanto valga)

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
config/                    # configurazione (dca_plan.yaml: il piano di accumulo)
education/                 # modulo didattico (ADR-015)
  L1_principiante/         # Investor 101
  L2_intermedio/           # Smart Investor
  L3_avanzato/             # Quantitative Investor
  L4_esperto/              # Wolf of Wall Street / Professional
docs/                      # documentazione tecnica (piano di sviluppo,
                           #   archivio di STATUS, inventario fonti, ...)
```

## Natura del progetto

Ricerca quantitativa, **non** trading bot. Il rigore metodologico viene prima
dei risultati. Vedere `VISION.md` per i criteri di successo.
