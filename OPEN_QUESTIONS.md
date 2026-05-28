# OPEN_QUESTIONS.md

> Domande aperte, ipotesi da validare, decisioni rinviate.
> Quando una domanda viene risolta: spostala in `DECISIONS.md` come ADR e
> rimuovila da qui (o marca con `[RISOLTA → ADR-NNN]`).

---

## ✅ Decisioni risolte

| # | Domanda | Risolta da |
|---|---|---|
| Q1 | Scope finale: trading reale o solo ricerca? | [ADR-004](./DECISIONS.md) |
| Q2 | Asset universe iniziale | [ADR-005](./DECISIONS.md) |
| Q3 | Timeframe predittivo | [ADR-006](./DECISIONS.md) |
| Q4 | Tipo di output del modello | [ADR-007](./DECISIONS.md) |
| Q5 | Budget per dati premium | [ADR-008](./DECISIONS.md) |
| Q6 | Stack tecnologico | [ADR-009](./DECISIONS.md) |
| Q13 | Capitale virtuale del paper trading | [ADR-011](./DECISIONS.md) |
| Q14 | Exchange di riferimento per fee | [ADR-012](./DECISIONS.md) |
| Q15 | Modello di slippage | [ADR-013](./DECISIONS.md) |
| Q21 (parz.) | Mapping ticker POL su Yahoo | [ADR-019](./DECISIONS.md) |
| Q21bis | Gap recente POL post-2025-03 | [ADR-020](./DECISIONS.md) (via Binance.us) |
| Q22 | Composizione serie multi-source | [ADR-021](./DECISIONS.md) (concat + flag source) |

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

### Q16 — Universe equity per la futura Fase 8
Quando estenderemo a equity tradizionale, su quale universe partiamo?

Opzioni:
- **A**: **S&P 500** (USA, large cap) — più dati, più ricerca, alta liquidità
- **B**: **NASDAQ 100** (USA, tech-pesante) — overlap con interessi tech crypto
- **C**: **FTSE MIB** (Italia) — coerente con la residenza dell'utente,
  fiscalmente più accessibile in pratica
- **D**: **Combinazione**: indici USA + alcuni titoli italiani liquidi
- **E**: Solo **ETF** (S&P 500, MSCI World, settori specifici) come baseline
  più semplice prima di passare a singoli titoli

*Direzione iniziale (non vincolante)*: probabile **E** + alcuni nomi USA
liquidi. **C** è interessante per uso pratico ma ha meno copertura di news.

*Decisione rinviata a inizio Fase 8.*

---

### Q17 — Broker di riferimento per il paper trading equity
Per modellare fee/spread su equity, quale broker simuliamo?

Opzioni:
- **A**: **Interactive Brokers** (IBKR) — standard de facto per retail
  internazionale, fee competitive, modello tariffario complesso ma noto
- **B**: **Degiro** — popolare in Italia, fee semplici, ma copertura asset
  più limitata
- **C**: **Fineco / Directa** — italiani, comodi per residenti, fee più alte
- **D**: Multipli (come per crypto, modelliamo IBKR + uno italiano)

*Direzione iniziale*: probabile **D** (IBKR come benchmark + uno italiano
per realismo pratico per l'utente).

*Decisione rinviata a inizio Fase 8.*

---

### Q19 — Budget LLM API: calibrazione del cap
ADR-016 fissa un cap iniziale di **15 EUR/mese** per le chiamate LLM API
(Layer 2). È un valore prudenziale, da calibrare in Fase 3 quando avremo:

- Numero realistico di news/giorno che richiedono Layer 2 (cioè quelle che
  Layer 1 non gestisce con confidence sufficiente)
- Costo medio per chiamata su modelli effettivamente usati (Claude Sonnet vs
  Haiku vs altri)
- Hit rate del cache (più alto è il cache, più basso il costo effettivo)

*Direzione*: rivedere il cap a inizio Fase 3, alzare/abbassare in base a
dati reali. Decisione formale rinviata.

---

### Q20 — Provider LLM API: solo Anthropic o multi-provider
ADR-016 propone Anthropic Claude come default. Vale la pena considerare:

- **A**: Solo Claude (semplice, coerente, una sola chiave API, costo
  prevedibile)
- **B**: Claude + OpenAI come fallback (in caso di downtime / cap raggiunto)
- **C**: Layer di astrazione su LiteLLM o simili → swappabile tra provider
  in modo trasparente

*Direzione*: **A** per partire, **C** se serviranno test comparativi tra
modelli. Decisione rinviata a inizio Fase 3.

---

### Q23 — Volume aggregato tra venue diverse
[ADR-021](./DECISIONS.md) compone OHLCV multi-source con later-source-wins,
ma il volume viene preso "come arriva" dalla source vincente. Yahoo
aggrega cross-exchange (volume "globale" stimato), Binance.us riporta
solo il volume sul proprio venue. **Non sono confrontabili in livello
assoluto.**

Per la Fase 1 (descriptive stats, distribuzioni) il problema è marginale
— il volume è una serie ausiliaria. Diventa rilevante quando:
- Costruiamo feature di **liquidità relativa** (volume / market cap, o
  rolling volume z-score) che assumono una scala stabile
- Cerchiamo segnali da **volume spikes** (un picco di volume Binance.us
  può essere un evento, ma il livello "0" pre-listing rende il
  cambiamento artificiale)

*Direzione*: ignorare per ora. Quando attaccheremo feature volume-based
in Fase 2, decidere se (a) normalizzare per provider con z-score
within-source, (b) usare solo CoinGecko/CMC come fonte volume aggregata
e dedicata, (c) costruire feature solo su return, non su volume assoluto.

---

### Q18 — Granularità del modulo didattico
Quanto in profondità entriamo per ciascun livello (ADR-015)?

- **A**: Sintetico — un solo file markdown per capitolo, ~1-2 pagine,
  rimando a letture esterne
- **B**: Esteso — più file per capitolo, esempi pratici sui dati del progetto,
  esercizi
- **C**: Ibrido — sintetico per L1/L2, esteso per L3/L4 dove l'utente vuole
  davvero imparare a fare

*Raccomandazione*: **C**. L1/L2 sono "alfabetizzazione", L3/L4 sono il vero
valore aggiunto del progetto.

*Decisione rinviata a quando si scriverà il primo capitolo (Fase 1).*

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
