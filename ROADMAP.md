# ROADMAP.md

> Fasi in ordine. Ogni fase ha obiettivi, deliverable e criteri di "fatto".
> Stato di completamento aggiornato qui. Date indicative omesse: si procede a
> milestone, non a calendario.

---

## Fase 0 — Framing & setup *(in corso)*

**Obiettivo**: definire scope, principi e infrastruttura documentale prima di
scrivere una singola riga di codice.

### Deliverable
- [x] Repository inizializzata e pulita
- [x] `CLAUDE.md`, `VISION.md`, `ROADMAP.md`, `STATUS.md`, `DECISIONS.md`,
      `OPEN_QUESTIONS.md` creati
- [ ] Risolte le decisioni critiche aperte in `OPEN_QUESTIONS.md`:
  - [ ] Scope: trading reale vs solo segnali/ricerca
  - [ ] Asset universe iniziale
  - [ ] Timeframe predittivo
  - [ ] Tipo di output del modello
  - [ ] Budget per dati premium (sì/no)
  - [ ] Stack tecnico
- [ ] Definite metriche di successo concrete

### Criterio di completamento
Quando l'avvio di Fase 1 è possibile senza dover tornare a discutere lo scope.

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

## Fase 6 — Output, dashboard, sintesi

**Obiettivo**: rendere il sistema **utile** e consultabile, non solo un insieme
di notebook.

### Deliverable
- [ ] Decidere la forma di output (vedi `OPEN_QUESTIONS.md`):
      dashboard web? report periodico? alerting?
- [ ] Implementazione
- [ ] Documentazione finale: insights, limitazioni, ipotesi non confermate
- [ ] (Opzionale) Paper trading per validazione finale prima di qualsiasi
      considerazione di uso reale

### Criterio di completamento
Dato lo stato corrente dei mercati e delle notizie, il sistema produce un output
sintetico, comprensibile e onesto sulla confidenza dei segnali.

---

## Note sulla roadmap

- **Le fasi sono lineari ma rivisitabili**: scoperte in Fase 3 possono richiedere
  di tornare in Fase 1 (nuove sorgenti dati). Va bene, basta tracciarlo in
  `STATUS.md`.
- **Ogni fase può "fallire"**: scoprire che non c'è segnale è un risultato valido.
- **Le fasi 5 e 6 sono condizionate**: ha senso affrontarle solo se le fasi
  precedenti producono baseline funzionanti.
