# ROADMAP.md

> Fasi in ordine. Ogni fase ha obiettivi, deliverable e criteri di "fatto".
> Stato di completamento aggiornato qui. Date indicative omesse: si procede a
> milestone, non a calendario.

---

## Fase 0 — Framing & setup ✅ *completata (2026-05-28)*

**Obiettivo**: definire scope, principi e infrastruttura documentale prima di
scrivere una singola riga di codice.

### Deliverable
- [x] Repository inizializzata e pulita
- [x] `CLAUDE.md`, `VISION.md`, `ROADMAP.md`, `STATUS.md`, `DECISIONS.md`,
      `OPEN_QUESTIONS.md` creati
- [x] Risolte le decisioni critiche (ADR-004 ÷ ADR-009 in `DECISIONS.md`):
  - [x] Scope: ricerca ora, live trading futuro condizionale (ADR-004)
  - [x] Asset universe: Tier 1 (BTC/ETH/SOL/LINK/POL) + Tier 2 top 20 (ADR-005)
  - [x] Timeframe: multi (breve/medio/lungo) (ADR-006)
  - [x] Output: direzione + rendimento + probabilità (+ vol/conf/factors) (ADR-007)
  - [x] Budget: gratuiti prima, premium dopo conferma (ADR-008)
  - [x] Stack: Python 3.12 + uv + Jupyter + ruff + pandas/polars + sklearn/HF (ADR-009)
- [ ] Definizione finale di metriche di successo concrete → spostata a Fase 2
      (servono dati per calibrare soglie realistiche)

---

## Fase 1 — Esplorazione dati

**Obiettivo**: capire quali dati sono accessibili (gratis o low-cost), in che
forma, con quale qualità.

### Deliverable
- [ ] Inventario di sorgenti dati con: API, frequenza, storico disponibile,
      licenza, costo, rate limit
- [ ] Setup ambiente Python (o stack scelto) con virtualenv/poetry/uv
- [ ] Script di ingestion **basico** per 1-2 asset (es. BTC, ETH) — solo OHLCV
- [ ] Notebook di esplorazione: statistica descrittiva, distribuzioni di
      rendimenti, autocorrelazioni, stagionalità, ciclo halving
- [ ] Strategia di storage definita (file CSV/parquet locali → poi
      eventualmente DB time-series)

### Criterio di completamento
Sappiamo esattamente quali sorgenti dati useremo, in che formato, con quali
limiti.

---

## Fase 2 — Baseline tecnica & backtesting rigoroso

**Obiettivo**: costruire l'infrastruttura di valutazione **prima** dei modelli
complessi. Senza questa, qualsiasi risultato successivo è inattendibile.

### Deliverable
- [ ] Indicatori tecnici classici implementati (MA, MACD, RSI, BB, ATR, OBV)
- [ ] Framework di **backtesting walk-forward** con:
  - Niente look-ahead bias (test esplicito)
  - Costi di transazione inclusi (fee + slippage stimato)
  - Survivorship bias mitigato (se possibile)
  - Out-of-sample mandatory
- [ ] Modello **baseline**: random walk + momentum semplice + ARIMA
- [ ] Suite di metriche: Sharpe, Sortino, max drawdown, hit rate, profit factor,
      Calmar, time underwater
- [ ] Confronto baseline vs buy-and-hold

### Criterio di completamento
Possiamo confrontare qualsiasi nuovo modello con baseline solide e affidabili.

---

## Fase 3 — Sentiment & notizie

**Obiettivo**: introdurre la dimensione "informativa" non-numerica.

### Deliverable
- [ ] Pipeline ingestion notizie da almeno 2 fonti (es. CryptoPanic, RSS feed
      Reuters/Bloomberg/altro)
- [ ] NLP pipeline: sentiment scoring, entity recognition, topic classification
- [ ] Feature derivate: sentiment medio rolling, volume notizie, divergenza
      sentiment vs prezzo, picchi di volume informativo
- [ ] Test di correlazione (con lead/lag) tra feature di sentiment e
      rendimenti / volatilità futuri
- [ ] Pipeline estendibile a Twitter/X, Reddit (se accesso disponibile)

### Criterio di completamento
Abbiamo dataset news-derived allineato temporalmente con dati di mercato, e
abbiamo testato statisticamente se il sentiment ha potere predittivo.

---

## Fase 4 — Modelli multifattoriali

**Obiettivo**: combinare tecnico + sentiment + macro in modelli ML.

### Deliverable
- [ ] Macro features: tassi, DXY, M2, yield treasury
- [ ] On-chain features (se accessibili): hash rate, active addresses, exchange flows
- [ ] Feature engineering pipeline pulita e riproducibile
- [ ] Modelli ML in ordine di complessità: logistic regression → gradient
      boosting (XGBoost/LightGBM) → eventuali deep learning (LSTM/Transformer)
- [ ] Cross-validation temporale rigorosa
- [ ] Feature importance analysis
- [ ] Confronto out-of-sample vs baseline Fase 2

### Criterio di completamento
Sappiamo dire (con metriche, non con sensazioni) se l'integrazione
multifattoriale aggiunge valore predittivo rispetto al tecnico puro.

---

## Fase 5 — Cicli, regimi & contestualizzazione

**Obiettivo**: il mercato non è omogeneo nel tempo. Identificare regimi e
adattare l'analisi.

### Deliverable
- [ ] Detection di market regime (bull/bear/sideways/high-vol/low-vol) con
      hidden Markov models o clustering
- [ ] Analisi cicli specifici crypto: halving, anniversari, cicli on-chain
- [ ] Modelli condizionati al regime
- [ ] Test: i modelli funzionano meglio quando "sanno" il regime?

### Criterio di completamento
Capiamo se e quanto la contestualizzazione per regime migliora le predizioni.

---

## Fase 6 — Paper trading engine

**Obiettivo**: permettere all'utente di "investire" con un budget virtuale sui
segnali generati dal sistema, simulando con realismo guadagni e perdite. È il
**gate di validazione finale** prima di qualsiasi considerazione di live
trading. Vedi ADR-010 per i principi non negoziabili.

### Deliverable
- [ ] Modulo `src/execution/` con interfaccia `Broker` astratta
- [ ] Implementazione `PaperBroker`:
  - [ ] No look-ahead (ordine al tempo `t` ⇒ fill alla candela `t+1`)
  - [ ] Modello fee tarato su Binance spot (default 0.1% maker/taker)
  - [ ] Modello slippage lineare basato su spread e size
  - [ ] Latenza simulata (almeno una candela del timeframe corrente)
- [ ] Portfolio manager: posizioni, P&L realizzato e non-realizzato, equity curve
- [ ] Persistenza completa (storico ordini, fill, snapshot portfolio) in
      parquet/SQLite — risultati riproducibili e auditabili
- [ ] Tipi di ordine: Market, Limit (Stop e TP in seconda iterazione)
- [ ] Position sizing configurabile (percentuale fissa come baseline)
- [ ] Long-only inizialmente (no leverage, no short)
- [ ] Metriche calcolate sull'equity curve, **identiche** a quelle del backtest
      di Fase 2 (Sharpe, Sortino, max drawdown, profit factor, ecc.)
- [ ] Modalità di esecuzione:
  - [ ] **Replay**: rieseguire segnali su dati storici (= backtest realistico)
  - [ ] **Live-shadow**: ingerire dati real-time/quasi-real-time, generare
        segnali e simulare esecuzione in continuo. Coerente col timeframe scelto
- [ ] Configurazione iniziale (parametri esposti):
  - Capitale virtuale di partenza
  - Exchange di riferimento (per fee model)
  - Allocazione/sizing policy
  - Whitelist asset operabili

### Criterio di completamento
- Il paper trading gira in modalità live-shadow per **almeno 3 mesi**
  consecutivi senza interventi manuali
- L'equity curve generata viene confrontata con buy-and-hold sui Tier 1 e
  con un benchmark naïve (es. DCA fisso)
- Le metriche sono **honestly reportable**: drawdown massimo, periodi di
  underwater, hit rate, Sharpe out-of-sample
- Documentazione completa dei limiti del simulato vs reale (psicologia,
  esecuzione di ordini grossi, ecc.)

---

## Fase 7 — Output, dashboard, sintesi

**Obiettivo**: rendere il sistema **utile** e consultabile, non solo un insieme
di notebook. È la fase di "consumo" del sistema da parte dell'utente.

### Deliverable
- [ ] Forma di output finale (decisione in `OPEN_QUESTIONS.md` Q8):
      dashboard web? report periodico? alerting Telegram?
- [ ] Visualizzazione segnali multi-orizzonte per asset (breve/medio/lungo
      a colpo d'occhio)
- [ ] Visualizzazione dello stato del paper portfolio: equity curve, posizioni,
      P&L, metriche
- [ ] Confronto continuo paper portfolio vs benchmark (DCA, buy-and-hold)
- [ ] Diario degli insights e delle ipotesi non confermate
- [ ] Documentazione finale del progetto

### Criterio di completamento
Dato lo stato corrente dei mercati e delle notizie, il sistema produce un
output sintetico, comprensibile e onesto sulla confidenza dei segnali, e
l'utente può consultare lo stato del paper portfolio in qualsiasi momento.

---

## Note sulla roadmap

- **Le fasi sono lineari ma rivisitabili**: scoperte in Fase 3 possono richiedere
  di tornare in Fase 1 (nuove sorgenti dati). Va bene, basta tracciarlo in
  `STATUS.md`.
- **Ogni fase può "fallire"**: scoprire che non c'è segnale è un risultato valido.
- **Le fasi 5, 6 e 7 sono condizionate**: ha senso affrontarle solo se le fasi
  precedenti producono baseline funzionanti. In particolare, **Fase 6 (paper
  trading) ha senso solo se Fase 4 produce modelli che battono benchmark
  out-of-sample**. Altrimenti staremmo simulando trade su segnali rumorosi.
- **Eventuale Fase 8 — Live trading**: non in roadmap attuale. Richiede nuova
  ADR esplicita, ≥3 mesi di paper trading positivo, risk management
  formalizzato. Vedi ADR-004.
