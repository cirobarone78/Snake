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
| D7 (piano §2) | Soglia di confidenza del paper portfolio | [ADR-036](./DECISIONS.md) (disattivata: senza probabilità calibrata non è applicabile) |

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

### Q26 — La quota satellite resta a 3 asset, o ne assorbe uno dalla shortlist?
Emersa con ADR-030. Lo screen candidate produce nomi che superano i filtri
meccanici (dimensione, liquidità, età dimostrabile), ma **allargare la quota
satellite non è una decisione tecnica**: significa spalmare 10€/mese su 4 o 5
asset invece di 3, quindi accumulare più lentamente su ciascuno.

Il trade-off, in chiaro:
- **Restare a 3**: posizioni che crescono a una velocità apprezzabile; la
  diversificazione la fa già il core BTC/ETH (90% del versamento)
- **Allargare**: meno dipendenza dal destino di un singolo progetto, ma con
  10€/mese divisi in 5 si accumulano cifre che le commissioni erodono

Nota di onestà: **il sistema non ha modo di rispondere**. Non c'è alcun
risultato in questo progetto che dica quale delle due sia migliore, e le
candidate non sono ordinate per qualità ma per dimensione, età e liquidità.

*Decisione dell'utente, non del sistema.* Se la risposta è "allargare", va
aggiornato `config/dca_plan.yaml` (`sleeve.target_weights`) e registrata la
scelta qui o in DECISIONS.md.

---

### Q27 — Quanto vale davvero un meccanismo di cattura del valore?
Emersa con ADR-031. La scheda fondamentale sa dire **se** un token cattura il
valore prodotto dal protocollo (burn, staking, riacquisti, work token), ma non
**quanto**: un burn enorme e uno simbolico prendono lo stesso punteggio. È il
motivo per cui NEAR ed Ethereum compaiono a pari merito, il che è chiaramente
sbagliato.

Il dato che risolverebbe la questione — ricavi di protocollo, TVL, rapporto
prezzo/commissioni — esiste ed è gratuito (DefiLlama), ma `api.llama.fi` è
**bloccato dalla policy di rete** di questo ambiente.

Due domande distinte, e vanno separate:
1. **Operativa**: sbloccare l'host? Decisione dell'utente sull'ambiente.
2. **Metodologica, e più interessante**: una volta avuti i ricavi, un rapporto
   prezzo/commissioni basso indica davvero qualcosa? Nelle azioni il P/E basso
   ha una letteratura enorme e contrastata; nei protocolli crypto la storia è
   lunga pochi anni e piena di sopravvissuti. **Il rischio concreto è
   confezionare un P/E crypto e trattarlo come se fosse validato.** Se lo si
   introduce, va introdotto come descrizione, con la stessa onestà con cui la
   regola sulla quota satellite è stata dichiarata priva di edge.

*Non bloccante.* La scheda funziona anche senza; semplicemente non gradua.

---

### Q28 — Quando e come si ri-apre la validazione del ranking?
Emersa con WP4. Il paper portfolio gira ogni lunedì su una regola **misurata come
non predittiva** (ADR-034) e accumula un ledger di previsioni con esito. Prima o
poi quel ledger sarà abbastanza lungo da dire qualcosa — ma *quanto* è abbastanza,
e cosa si misura, va deciso **prima** di guardarlo, altrimenti si ripete
esattamente l'errore che ADR-034 documenta.

Tre cose da fissare in anticipo, in una pre-registrazione come quella di §2.1:

1. **Quante settimane** di forward prima di rimisurare (a 20 sedute, previsioni
   emesse settimanalmente e sovrapposte: il campione indipendente cresce molto più
   lentamente di quanto suggerisca il conteggio delle righe).
2. **Quale ipotesi**, con **magnitudine** — la lezione esplicita di ADR-034: `IC > 0`
   è quasi gratis da superare, e infatti il momentum ci è passato pur essendo
   sotto il ranker casuale.
3. **Cosa succede se passa**: riattivare D7 con la sua soglia originale è già
   previsto da ADR-036, ma serve una ADR che dichiari il modello adottato.

Nota di cautela già scritta nel payload: se il portafoglio dovesse battere SPY
nelle prime settimane, **la prima ipotesi da falsificare è la fortuna**.

*Non bloccante*: nulla dipende da questa risposta finché il ledger è corto. Ma va
risolta prima di guardare i numeri, non dopo.

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
