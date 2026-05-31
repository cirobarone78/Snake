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
| Q24 | Storage append per snapshot | [ADR-022](./DECISIONS.md) (latest + history) |
| Q9 | Modello di sentiment per news | [ADR-023](./DECISIONS.md) (Layer 1 lessico/VADER) |
| Q12 | Allineamento temporale news↔prezzo | [ADR-024](./DECISIONS.md) (publication-time + lag) |
| Q10 | Frequenza di ingestion notizie | [ADR-025](./DECISIONS.md) (batch giornaliero + history versionata) |

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

### Q9 — Modello di sentiment per news — ✅ RISOLTA → [ADR-023](./DECISIONS.md)
Scelto **Layer 1 = lessico (VADER)** come baseline (deterministico, nessuna
dipendenza pesante). Salita a FinBERT (Layer 2) subordinata a evidenza empirica.

---

### Q10 — Frequenza di ingestion notizie — ✅ RISOLTA → [ADR-025](./DECISIONS.md)
**Batch giornaliero** (cron GitHub Actions 06:30 UTC) che alimenta la news
history versionata. Coerente col timeframe breve daily (ADR-006) e col lag di
allineamento (ADR-024).

---

### Q11 — Definizione operativa di "sideways"
ADR-007 definisce indicativamente: ±2% per breve, ±10% per lungo. Vanno
calibrate empiricamente sulla volatilità storica di ciascun asset
(BTC vs SOL hanno scala diversa).

*Decisione rinviata a Fase 4*. Le statistiche descrittive di Fase 1 ci
sono già, ma la soglia operativa "sideways" serve solo quando un modello
produrrà davvero l'output a 3 stati di ADR-007. I baseline di Fase 2
(random walk / momentum) usano un segnale binario long/flat e non
richiedono la calibrazione: rinviata al primo modello che implementa il
contract ADR-007 completo.

---

### Q12 — Allineamento temporale tra fonti — ✅ RISOLTA → [ADR-024](./DECISIONS.md)
Per le news: **publication-time UTC**, aggregazione a giorno UTC, **lag di
sicurezza 1 giorno** prima del join coi return (anti-look-ahead). UTC midnight
resta il "fine giornata" del timeframe daily. L'allineamento di macro a *release
date* (CPI/M2) resta un punto distinto del backlog Fase 2.1/4.

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

### Q25 — Perché LINK resiste al filtro di regime/momentum?
Emersa in Fase 2.1 (notebook 05). Il momentum trend-following protegge nei
bear 4 asset Tier 1 su 5 (BTC/ETH/SOL/POL), riducendo il drawdown. **LINK è
l'unico su cui danneggia** (Δsharpe bear −0.94 vs buy-and-hold). L'ipotesi
"è whipsaw da volatilità" è **falsa**: SOL e POL sono più volatili di LINK
ma vengono protetti (corr vol↔Δsharpe = −0.09). Quindi è qualcosa di
**specifico di LINK**.

Candidati da indagare:
- Microstruttura del trend LINK 2019-2025 (range prolungati che generano
  falsi segnali di trend?)
- Eventi idiosincratici (es. staking launch, tokenomics) che rompono la
  persistenza
- È robusto al cambio di finestra del filtro di regime (SMA200 → altre)?

*Non bloccante.* Candidata a indagine dedicata in Fase 2.1 residua o Fase 5
(regimi). Importante non trattare LINK come gli altri finché non è capito.

---

## 🟢 Domande di ricerca (diario delle ipotesi testate — VISION)

Ipotesi testate empiricamente nel corso del progetto. **Esiti onesti registrati**
(✅ risposta data / 🔄 aperta).

- ✅ **Il sentiment news ha potere lead sui prezzi?** — **No** col campione
  attuale (nb 06): `corr(sentiment, ret) ~0` a tutti i lag; il +0.32 di n=23 era
  artefatto small-sample (svanito a n=143). In gran parte già scontato/lagging.
- ✅ **I cicli di halving sono ancora predittivi nel 2026+?** — **No edge**
  (nb 09): `halving_phase` non sposta l'accuracy → largamente "priced in".
- ✅ **Esistono regimi distinguibili sistematicamente?** — **Sì, descrittivamente**
  (nb 09): bull/bear × high/low vol partizionano nettamente rischio/rendimento
  (bull_high_vol Sharpe 2.97 vs bear_high_vol −1.20). Ma *conoscerli* non dà edge
  direzionale (sono già impliciti nel tecnico).
- ✅ **L'integrazione multifattoriale aggiunge valore vs tecnico puro?** — **No
  a frequenza daily** (nb 07/08): tecnico, +macro, +regime tutti ≈ coin-flip OOS.
- 🔄 **La macro conta alla sua frequenza naturale (mensile)?** — **Indizio di sì
  ma non validabile** (nb 10): `corr(cpi_yoy[t], ret[t+1]) = −0.26` (segno atteso,
  persistente), ma n~45 OOS troppo piccolo. **Il segnale più promettente trovato.**
  Validazione richiede cross-asset (equity/oro, decenni di storia mensile).
- 🔄 Le notizie tech vs macro: impatto relativo — non ancora isolato (serve più
  storia news + classificazione topic).
- 🔄 Lag tipici notizia→reazione — non misurabile col campione news attuale.
- 🔄 Correlazioni cross-asset stabili o regime-dependent? — **regime-dependent**
  (Fase 1: rolling std 0.12-0.17); non riapprofondito.
- 🔄 Dinamiche predittive diverse per asset Tier 1? — solo BTC testato a fondo;
  cross-asset rinviato.
- 🔄 Coerenza segnali breve/medio/lungo — solo breve (daily) e lungo (mensile)
  toccati; il segnale mensile macro non ha analogo daily (frequenze diverse).

*Sintesi*: dopo aver testato tecnico, macro, news, regimi e cicli, **nessun edge
predittivo direzionale robusto** emerge a frequenza daily. L'unico indizio reale
è la macro (inflazione) a frequenza **mensile**, ma il campione crypto (~100 mesi)
è troppo corto per validarlo. Coerente con VISION #1: "meglio nessun segnale che
un segnale falso convincente".
