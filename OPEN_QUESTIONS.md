# OPEN_QUESTIONS.md

> Domande aperte, ipotesi da validare, decisioni rinviate.
> Quando una domanda viene risolta: spostala in `DECISIONS.md` come ADR e
> rimuovila da qui (o marca con `[RISOLTA → ADR-NNN]`).

---

## ✅ Decisioni critiche di Fase 0 — RISOLTE

| # | Domanda | Risolta da |
|---|---|---|
| Q1 | Scope finale: trading reale o solo ricerca? | [ADR-004](./DECISIONS.md#adr-004--scope-ricerca-ora-live-trading-come-obiettivo-condizionale-futuro) |
| Q2 | Asset universe iniziale | [ADR-005](./DECISIONS.md#adr-005--asset-universe-iniziale) |
| Q3 | Timeframe predittivo | [ADR-006](./DECISIONS.md#adr-006--multi-timeframe-predittivo) |
| Q4 | Tipo di output del modello | [ADR-007](./DECISIONS.md#adr-007--output-del-modello-multi-dimensionale) |
| Q5 | Budget per dati premium | [ADR-008](./DECISIONS.md#adr-008--budget-dati-gratuiti-prima-premium-dopo-conferma-di-necessit) |
| Q6 | Stack tecnologico | [ADR-009](./DECISIONS.md#adr-009--stack-tecnologico) |

**Fase 0 sbloccata**: possiamo iniziare Fase 1.

---

## 🟡 Decisioni importanti ma non bloccanti

### Q7 — Storage dei dati
Come persistiamo i dati raccolti?

Opzioni:
- **A**: File parquet/CSV locali in `/data` (gitignored) — *direzione iniziale
  per ADR-009*
- **B**: SQLite per dati strutturati piccoli
- **C**: DB time-series locale (DuckDB, TimescaleDB, InfluxDB)
- **D**: Cloud object storage (S3-compatible)

*Probabile evoluzione*: **A** → **DuckDB** (parquet-native, zero-config) se
i dataset crescono. Decisione formale rinviata a Fase 1.

---

### Q8 — Forma finale dell'output
Quando arriviamo a Fase 6, in che forma il sistema espone i risultati?

Opzioni:
- **A**: Dashboard web (Streamlit/Gradio/Dash) — interattiva
- **B**: Report markdown/HTML generato periodicamente
- **C**: Alerting (Telegram/email) su segnali significativi
- **D**: API + client a scelta
- **E**: Combinazione

*Non urgente*: la forma di output dipende anche da cosa il sistema riuscirà
effettivamente a produrre. Rinviata a fine Fase 4.

---

### Q9 — Modello di sentiment per news
Quando estraiamo sentiment da news, quale tecnologia?

- **A**: FinBERT / sentence-transformers (open-source, gratis, accuratezza media)
- **B**: LLM commerciale (Anthropic/OpenAI API) per casi complessi (costo per chiamata)
- **C**: Ibrido: open-source per il bulk, LLM per casi ad alta importanza

*Direzione*: partire con **A**, valutare **C** in Fase 3 se l'accuratezza
non basta.

---

### Q10 — Frequenza di ingestion notizie
Real-time vs batch giornaliero?

*Decisione rinviata a Fase 3*. Probabile: batch giornaliero per il primo
modello (allineato con timeframe "breve" che è a granularità giornaliera).

---

### Q11 — Definizione operativa di "sideways"
ADR-007 definisce indicativamente: ±2% per breve, ±10% per lungo. Vanno
calibrate empiricamente sulla volatilità storica di ciascun asset
(BTC vs SOL hanno scala diversa).

*Decisione rinviata a Fase 2*, quando avremo dati e statistiche descrittive.

---

### Q12 — Allineamento temporale tra fonti
Notizie, market data, on-chain, macro hanno frequenze e fusi orari diversi:

- Chiusura giornaliera: in che fuso orario? UTC è standard ma le borse USA
  chiudono alle 21:00 UTC, mentre crypto è 24/7
- News: il timestamp è ora di pubblicazione o ora dell'evento?
- Macro (es. CPI): pubblicato a date fisse, ma vale dal momento `t`

*Decisione*: usare **UTC midnight** come "fine giornata" per il timeframe
giornaliero. Da formalizzare in ADR appena tocchiamo il primo allineamento
multi-source (Fase 3).

---

### Q13 — Capitale virtuale iniziale del paper trading
Quanti euro virtuali assegniamo al paper portfolio (ADR-010)?

Opzioni:
- **A**: Allineato al portafoglio reale dell'utente — ~1 200 EUR/anno DCA,
  quindi capitale virtuale ~1 200 EUR aggiornato annualmente, o stock fittizio
  iniziale 5 000 EUR
- **B**: 10 000 EUR fissi all'inizio del paper trading
- **C**: Più scenari paralleli (es. 1k / 10k / 100k) per vedere come scala
  con la size — utile per analisi di slippage

*Raccomandazione*: **B** come default, valutare **C** se vediamo che lo
slippage modeling impatta i risultati.

*Decisione rinviata a inizio Fase 6.*

---

### Q14 — Exchange di riferimento per fee e spread
Le fee e gli spread differiscono tra exchange. Quale modelliamo?

Opzioni:
- **A**: Binance spot (fee 0.1% maker/taker base, alta liquidità) — *default proposto in ADR-010*
- **B**: Coinbase Advanced Trade (fee più alte ma più "retail-friendly")
- **C**: Kraken
- **D**: Modelliamo più exchange e mostriamo P&L per ciascuno (più realistico
  ma overhead)

*Raccomandazione*: partire da **A**. Quando arriveremo al live (se), questa
decisione condiziona anche il broker reale.

*Decisione rinviata a inizio Fase 6.*

---

### Q15 — Modello di slippage e market impact
Quanto realismo serve nella simulazione dell'impatto?

Opzioni:
- **A**: Slippage costante (es. sempre 5 bps) — semplice ma poco realistico
- **B**: Slippage proporzionale al bid-ask spread storico — realistico per
  ordini piccoli su asset liquidi (i nostri Tier 1)
- **C**: Modello di impatto sub-lineare basato su volume (square-root law) —
  serio ma richiede dati di order book
- **D**: Slippage random calibrato sulla volatilità — onesto sull'incertezza

*Raccomandazione*: **B** in Fase 6, considerare **C** o **D** se i risultati
mostrano sensitività al modello.

*Decisione rinviata a inizio Fase 6.*

---

## 🟢 Domande di ricerca (non decisioni operative)

Ipotesi da testare empiricamente nel corso del progetto.

- Il sentiment delle news ha potere predittivo *lead* sui prezzi, o è solo
  *concomitante/lagging*?
- Le notizie tech (es. annunci adoption, exploit, regulation) hanno impatto
  più forte di quelle macro?
- I cicli di halving Bitcoin sono ancora predittivi nel 2026+ o sono "priced
  in" dal mercato?
- Esistono regimi di mercato distinguibili sistematicamente?
- L'integrazione multifattoriale aggiunge davvero valore o il tecnico puro
  è sufficiente?
- Quali sono i lag temporali tipici tra una notizia e la reazione di prezzo?
- Le correlazioni cross-asset (BTC vs S&P, vs gold, vs DXY) sono stabili
  o regime-dependent?
- Gli asset Tier 1 dell'utente (BTC, ETH, SOL, LINK, POL) hanno dinamiche
  predittive diverse? Quali feature funzionano su quale asset?
- I segnali sono coerenti tra breve/medio/lungo termine o frequentemente
  divergenti?

*Queste vanno trasformate in esperimenti specifici durante le fasi corrispondenti.*
