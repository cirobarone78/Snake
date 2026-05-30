# CLAUDE.md

> Istruzioni operative per ogni sessione di Claude Code su questo progetto.
> **Leggere SEMPRE prima di iniziare qualsiasi attività.**

## Cos'è questo progetto

Sistema sperimentale di **analisi multifattoriale dei mercati finanziari** con focus
sulle criptovalute. Obiettivo: integrare dati di mercato, on-chain, macro, cicli e
sentiment da notizie (finanza, tecnologia, geopolitica, politica) per cercare
segnali predittivi sull'andamento di asset selezionati.

**Natura del progetto**: ricerca quantitativa, non "trading bot da arricchirsi".
Il rigore metodologico viene prima dei risultati.

## File da leggere a inizio sessione

In quest'ordine:

1. **`STATUS.md`** — dove siamo ora, cosa è in corso, cosa è bloccato
2. **`ROADMAP.md`** — fase corrente e prossimi obiettivi
3. **`OPEN_QUESTIONS.md`** — decisioni ancora aperte (non assumere risposte)
4. **`DECISIONS.md`** — decisioni già prese, non rimetterle in discussione senza motivo
5. **`VISION.md`** — solo se serve riallineare sull'obiettivo di alto livello

## Convenzioni operative

### Lingua
- **Chat con l'utente**: italiano
- **Codice, identificatori, log, commit message**: inglese
- **File di documentazione (`.md`)**: italiano
- **Commenti nel codice**: solo se aggiungono il "perché" (vedi sotto)

### A fine sessione (importantissimo per la continuità)
- Aggiornare **`STATUS.md`** con: cosa fatto, cosa lasciato in corso, cosa serve sapere alla prossima sessione
- Se è stata presa una decisione architetturale o di scope, registrarla in **`DECISIONS.md`** con format ADR
- Se è emersa una nuova domanda aperta, aggiungerla in **`OPEN_QUESTIONS.md`**
- Se uno step della roadmap è completato, marcarlo in **`ROADMAP.md`**

### Atteggiamento metodologico (non negoziabile)
- **Mai** trarre conclusioni da un singolo backtest senza out-of-sample testing
- **Sempre** documentare look-ahead bias check, survivorship bias check
- **Mai** promettere previsioni: parliamo sempre di segnali probabilistici, mai di certezze
- **Documentare anche cosa NON funziona** — gli esperimenti falliti vanno tracciati
- Le ipotesi vanno scritte **prima** di vedere i risultati, non dopo

### Vincoli operativi
- **Nessuna esecuzione di trade reali** in nessun ambiente, mai, senza richiesta esplicita E documentazione del consenso in `DECISIONS.md`
- API key e credenziali: **mai** in commit; usare `.env` + `.gitignore`
- Dati storici scaricati: tenerli fuori dalla repo se grossi (>10MB), usare `.gitignore`

## Stack & ambiente

**Stack tecnologico** (definito in ADR-009):
- **Python 3.12+** come linguaggio
- **`uv`** come package & env manager
- **Jupyter** notebook per esplorazione, script `.py` modulari per pipeline
- **ruff** (lint+format), **pyright** (type check: basic di default, strict
  per moduli core)
- **pytest** quando ci sarà codice testabile
- Data: **pandas** + **polars** (per performance), **DuckDB** se serve query SQL
- ML: **scikit-learn**, **statsmodels**, **XGBoost**, **LightGBM**;
  **PyTorch** se servirà deep learning
- NLP: **Hugging Face transformers**, **sentence-transformers**, **spaCy**,
  baseline **FinBERT** per sentiment finanziario
- Viz: **matplotlib** + **seaborn** (statica), **plotly** (interattiva)
- Storage iniziale: file **parquet** in `data/` (gitignored)

**Struttura cartelle** (convenzione):
```
src/                       # moduli Python riusabili (asset-class-agnostic, ADR-014)
notebooks/                 # esplorazione, EDA, prototipi
data/raw/                  # dati grezzi scaricati (gitignored)
data/processed/            # dataset puliti pronti per modelli (gitignored)
tests/                     # test pytest
education/                 # modulo didattico multi-livello (ADR-015)
  L1_principiante/         # Investor 101
  L2_intermedio/           # Smart Investor
  L3_avanzato/             # Quantitative Investor
  L4_esperto/              # Wolf / Professional
```

**Principio architetturale chiave** (ADR-014): il codice è
**asset-class-agnostic**. Non hardcodare assunzioni crypto-only (es. "il
mercato è sempre aperto", "non ci sono dividendi"). Asset, broker, fee model,
calendari sono configurazione. L'implementazione effettiva è solo crypto
fino a Fase 6 inclusa, ma l'astrazione c'è già.

**Asset universe** (ADR-005):
- **Tier 1** (priorità massima, deep analysis): BTC, ETH, SOL, LINK, POL
- **Tier 2** (universe dinamica, analisi base): top 20 crypto by market cap
- **Contesto** (non target): BTC dominance, DXY, S&P 500, NASDAQ, oro

**Timeframe predittivi** (ADR-006):
- **Breve**: 1–7 giorni, dati daily
- **Medio**: 2–8 settimane, dati daily/weekly
- **Lungo**: 3–12 mesi, dati weekly/monthly + macro

**Output del sistema** (ADR-007): direzione, rendimento atteso, probabilità,
volatilità attesa, confidence, top factors — per ogni asset × timeframe.

**Stato attuale**: Fase 1 completata (2026-05-29). Pronti per Fase 2
(baseline tecnica & backtesting rigoroso). Per il dettaglio aggiornato
leggere sempre `STATUS.md`.

## Quando in dubbio

- Su scope o obiettivo → rileggi `VISION.md` e chiedi all'utente
- Su una decisione tecnica → consulta `DECISIONS.md`; se assente, **proponi** prima di implementare
- Su priorità → segui `ROADMAP.md` ordine fasi

## Cosa NON fare

- Non creare file `.md` di documentazione aggiuntivi senza chiedere
- Non installare dipendenze pesanti senza che lo stack sia confermato
- Non scaricare dataset grossi senza prima discutere storage e licenze
- Non creare codice "speculativo" per fasi future della roadmap
- Non aggiungere abstraction layer o framework di test prima che ci sia codice da testare
