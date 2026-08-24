# DECISIONS.md

> Log delle decisioni prese, in stile **ADR (Architecture Decision Record)** semplificato.
> Una volta scritta una decisione qui, non rimetterla in discussione senza un motivo
> concreto (nuovi dati, vincoli cambiati). Le decisioni si **superano**, non si cancellano.

## Format

```
## ADR-NNN — Titolo breve
**Data**: YYYY-MM-DD
**Stato**: Accepted | Superseded by ADR-XXX | Deprecated
**Contesto**: perché si è dovuto decidere
**Decisione**: cosa è stato deciso
**Conseguenze**: cosa implica, cosa preclude, cosa abilita
```

---

## ADR-001 — Riutilizzo della repository "Snake"

**Data**: 2026-05-28
**Stato**: Accepted

**Contesto**: La repository conteneva un piccolo gioco Snake in HTML/JS che
l'utente non vuole più mantenere. Voleva una repo pulita per un nuovo progetto
sperimentale di analisi finanziaria.

**Decisione**: Rimosso completamente il contenuto pregresso (`index.html`).
README azzerato a placeholder. La repo conserva il nome "Snake" — può essere
rinominata in futuro, ma per ora non è una priorità.

**Conseguenze**:
- Il nome "Snake" non è più semanticamente legato al contenuto: ricordarsene
- La storia git mantiene traccia del progetto precedente
- Nessun impatto su sviluppo futuro

---

## ADR-002 — Natura del progetto: ricerca, non trading bot

**Data**: 2026-05-28
**Stato**: Accepted

**Contesto**: Il progetto può essere interpretato in due modi: (a) come trading
bot operativo, (b) come progetto di ricerca quantitativa che produce analisi e
segnali. Le due strade hanno requisiti, rischi e priorità molto diverse.

**Decisione**: Il progetto è inquadrato come **ricerca quantitativa
multifattoriale**. Nessuna esecuzione automatica di trade. Output del sistema
sono segnali probabilistici e analisi, non ordini di compravendita.

**Conseguenze**:
- Eliminato (per ora) il bisogno di integrazioni con exchange per ordini
- Eliminato (per ora) il bisogno di gestione di chiavi API con permessi di trading
- Focus su rigore metodologico, riproducibilità, honest reporting
- Apre la porta a un'eventuale fase futura "paper trading", ma solo dopo che la
  ricerca abbia prodotto risultati out-of-sample credibili
- Qualsiasi futura introduzione di esecuzione reale richiede una nuova ADR
  esplicita e consenso documentato

---

## ADR-003 — Convenzioni linguistiche

**Data**: 2026-05-28
**Stato**: Accepted

**Contesto**: L'utente comunica in italiano. Standard di sviluppo (codice,
librerie, ecosistema) sono in inglese. Serve una regola chiara per evitare
inconsistenze.

**Decisione**:
- Comunicazione chat: **italiano**
- File di documentazione `.md`: **italiano**
- Codice, identificatori, log, commit message: **inglese**
- Commenti nel codice: inglese, solo quando aggiungono il "perché" non ovvio

**Conseguenze**:
- Più facile per l'utente leggere documentazione e roadmap
- Il codice resta portabile e leggibile da chiunque
- Nessun mix di lingue all'interno dello stesso artefatto

---

## ADR-004 — Scope: ricerca ora, live trading come obiettivo condizionale futuro

**Data**: 2026-05-28
**Stato**: Accepted
**Risolve**: OPEN_QUESTIONS Q1

**Contesto**: L'utente ha portafoglio reale crypto (~100€/mese DCA: 60% BTC,
30% ETH, 10% altcoin a rotazione). L'interesse non è puramente accademico:
se il sistema dimostrerà affidabilità out-of-sample, l'utente vuole arrivare
a live trading.

**Decisione**:
- **Fase corrente (ricerca)**: nessuna esecuzione, nessuna chiamata ad
  exchange con permessi di trading
- **Sviluppo guidato dall'obiettivo finale**: progettare i moduli (data
  pipeline, signal generator, risk manager) tenendo a mente che dovranno
  reggere un eventuale path verso live, ma **senza** implementare integrazioni
  premature
- **Gate per il passaggio a paper trading**: completata Fase 4 con risultati
  out-of-sample che battono benchmark passivo su almeno 12 mesi rolling
- **Gate per il passaggio a live trading**: nuova ADR esplicita + minimo
  3 mesi di paper trading con metriche documentate + risk management framework
  formalizzato

**Conseguenze**:
- Le API key di lettura dati sono safe; quelle con permessi di trading
  restano off-limits fino a nuova ADR
- Aggiunto vincolo architetturale: separazione netta tra signal generation
  e order execution (anche se l'execution non esiste ancora)
- I costi di transazione (fee + slippage) vanno modellati realisticamente
  fin dalla Fase 2 — non è esercizio teorico

---

## ADR-005 — Asset universe iniziale

**Data**: 2026-05-28
**Stato**: Accepted
**Risolve**: OPEN_QUESTIONS Q2

**Contesto**: Definire quali asset analizzare condiziona ingestion, storage
e cross-asset analysis. L'utente ha esposizione reale a specifici asset crypto.

**Decisione**: Universe a due livelli.

**Tier 1 — "Held assets" (priorità massima)**:
- BTC (Bitcoin)
- ETH (Ethereum)
- SOL (Solana)
- LINK (Chainlink)
- POL (Polygon, ex MATIC — rinominato sett. 2024)

**Tier 2 — "Top 20 crypto by market cap"**: lista dinamica, ricalcolata
periodicamente (es. mensile). Serve per:
- Identificare segnali di rotazione settoriale
- Cross-asset correlations
- Benchmark relativi

**Asset esterni (per contesto, non target predittivo iniziale)**:
- BTC dominance, total crypto market cap
- DXY (US Dollar Index)
- S&P 500, NASDAQ (per correlazione macro)
- Oro (safe-haven correlation)

**Conseguenze**:
- Pipeline di ingestion deve gestire un universe dinamico (top 20) +
  un universe fisso (held)
- Survivorship bias: la "top 20" oggi non era la top 20 di 5 anni fa.
  Mantenere lista storica delle "top 20 at time t" per evitare bias nel backtest
- Tier 1 ha priorità per profondità di analisi (on-chain, sentiment specifico);
  Tier 2 inizialmente solo OHLCV + indicatori tecnici

---

## ADR-006 — Multi-timeframe predittivo

**Data**: 2026-05-28
**Stato**: Accepted
**Risolve**: OPEN_QUESTIONS Q3

**Contesto**: L'utente vuole segnali su breve, medio e lungo termine. Sono
orizzonti con dinamiche, feature rilevanti e rumore molto diversi.

**Decisione**: Modelli separati per tre orizzonti (operativamente definiti):

| Orizzonte | Definizione | Granularità dati | Use case tipico |
|---|---|---|---|
| **Breve** | 1–7 giorni | dati giornalieri (chiusura UTC) | timing tattico DCA, evitare drawdown imminenti |
| **Medio** | 2–8 settimane | dati giornalieri, feature settimanali | swing, rotazione tra asset |
| **Lungo** | 3–12 mesi | dati settimanali/mensili, feature macro+cicli | allocazione strategica, posizionamento cicli halving |

**Implicazioni operative**:
- Target variable diversa per ogni orizzonte
- Set di feature diverso: breve ⇒ sentiment + tecnico; medio ⇒ tecnico + on-chain;
  lungo ⇒ macro + cicli + on-chain + regime
- Training/validation split temporale rispettoso del timeframe (es. per il
  lungo termine servono molti anni di storia)

**Conseguenze**:
- Lavoro di modellazione triplica (un modello per orizzonte)
- Backtesting framework deve supportare valutazioni multi-orizzonte
- Output finale aggrega o presenta separatamente le tre view
- Possibili tensioni tra orizzonti (breve dice "sell", lungo dice "accumula"):
  vanno presentate come informazione, non risolte arbitrariamente

---

## ADR-007 — Output del modello: multi-dimensionale

**Data**: 2026-05-28
**Stato**: Accepted
**Risolve**: OPEN_QUESTIONS Q4

**Contesto**: L'utente vuole il massimo dell'informazione. Le priorità sono
direzione, rendimento atteso e probabilità.

**Decisione**: Per ogni asset e per ogni orizzonte (breve/medio/lungo), il
sistema produce:

**Output primari (obbligatori)**:
1. **Direzione**: classificazione `{up, down, sideways}` con soglia di
   "sideways" definita per timeframe (es. ±2% per breve, ±10% per lungo)
2. **Rendimento atteso**: stima puntuale del log-return atteso
3. **Probabilità**: distribuzione di probabilità sulla direzione + probabilità
   di movimento >X% (tail risk)

**Output secondari (best-effort)**:
4. **Volatilità attesa**: utile per dimensionare posizione e per asimmetria
   rischio/rendimento
5. **Confidence score**: meta-metrica che dice "quanto il modello è sicuro
   di sé" (basata su agreement tra modelli, dispersione predittiva, regime
   correntemente identificato)
6. **Top contributing factors**: feature importance per il segnale specifico
   (interpretabilità)

**Conseguenze**:
- Approccio modulare: ogni output può venire da un modello distinto
  (classificazione, regressione, modello probabilistico, GARCH per volatilità)
- O da un unico modello ensemble che produce tutto
- Decisione di architettura modello rinviata a Fase 4

---

## ADR-008 — Budget dati: gratuiti prima, premium dopo conferma di necessità

**Data**: 2026-05-28
**Stato**: Accepted
**Risolve**: OPEN_QUESTIONS Q5

**Contesto**: Esistono dati gratuiti di buona qualità (specialmente OHLCV
e on-chain base). Le sorgenti premium (Glassnode Pro, Nansen, Kaiko) sono
costose ma offrono granularità superiore.

**Decisione**:
- **Fase 1–3**: solo sorgenti gratuite o free tier. Esempi accettabili:
  - Market data: CoinGecko, Binance/Coinbase/Kraken public API, Yahoo Finance
  - On-chain: Blockchain.com, mempool.space, Etherscan, Glassnode free tier
  - News: RSS feed pubblici, CryptoPanic free tier
  - Macro: FRED (Federal Reserve), Yahoo Finance, dati BCE pubblici
- **Da Fase 4 in poi**: rivalutare. Se identifichiamo feature potenzialmente
  predittive che richiedono dati premium, valutare investimento (budget
  indicativo: fino a ~30€/mese, da confermare quando si presenta il caso)
- Ogni eventuale acquisto di dati premium richiede una nuova ADR specifica

**Conseguenze**:
- Documentare per ogni fonte: rate limit, storico disponibile, licenza
- Implementare caching aggressivo per non sprecare quote
- Accettare che alcune analisi (es. flussi inter-exchange granulari) saranno
  più povere o impossibili nelle prime fasi

---

## ADR-009 — Stack tecnologico

**Data**: 2026-05-28
**Stato**: Accepted
**Risolve**: OPEN_QUESTIONS Q6

**Contesto**: L'utente ha delegato la scelta. Vincoli: progetto data-science
intensive, NLP, ML, possibile esposizione futura a esecuzione real-time.

**Decisione**:

**Linguaggio**: **Python 3.12+** (de facto standard per data science e ML;
qualsiasi altra scelta sarebbe attrito senza beneficio)

**Package & env manager**: **`uv`** (Astral) — moderno, ordini di grandezza
più veloce di pip/poetry, sta diventando standard nella community

**Esplorazione**: **Jupyter** notebook (`.ipynb`) per analisi e
visualizzazione. Marimo considerato ma scartato per inerzia ecosistema

**Codice "production-like"** (pipeline, moduli riusabili): script `.py`
modulari, non notebook

**Type checking**: **pyright** in modalità *basic* per default,
*strict* per moduli core (data pipeline, signal generation)

**Linting & formatting**: **ruff** (replace black + isort + flake8;
ordini di grandezza più veloce)

**Test**: **pytest** quando arriverà codice testabile (presumibilmente da
Fase 2 in poi)

**Data manipulation**: **pandas** + **polars** (pandas come standard;
polars per dataset grandi o operazioni performance-critical)

**ML classico**: **scikit-learn**, **statsmodels**, **XGBoost**,
**LightGBM**

**Deep learning** (se servirà, Fase 4+): **PyTorch** (più flessibile, più
adottato in ricerca)

**NLP**: **Hugging Face transformers**, **sentence-transformers**, **spaCy**.
Modelli baseline: **FinBERT** per sentiment finanziario.
Eventuale uso di **LLM API** (Anthropic/OpenAI) solo se baseline open-source
non funziona — è la decisione da prendere in Fase 3

**Visualizzazione**: **matplotlib** + **seaborn** per analisi statica,
**plotly** per dashboard interattive

**Backtesting**: da decidere in Fase 2 (opzioni: **vectorbt**, **backtrader**,
o custom). Custom è probabile per controllo totale sul no-look-ahead

**Storage** (inizialmente): file **parquet** in `data/` (gitignored). DB
time-series valutato in seguito

**Conseguenze**:
- `pyproject.toml` + `uv.lock` come fonte di verità per dipendenze
- Setup ambiente in Fase 1, prima ancora di scrivere codice utile
- Convenzione cartelle: `src/` per moduli, `notebooks/` per esplorazione,
  `data/raw/` `data/processed/` per dati (gitignored), `tests/` per test

---

## ADR-010 — Paper trading engine come feature integrale del sistema

**Data**: 2026-05-28
**Stato**: Accepted

**Contesto**: L'utente vuole poter "investire" su segnali generati dal sistema
con un budget virtuale (euro fittizi), subendo gli stessi guadagni e perdite
che subirebbe con denaro reale. Lo scopo è validare il sistema **senza
rischiare capitale reale**, costituendo allo stesso tempo il gate verso un
eventuale live trading (vedi ADR-004).

**Decisione**: Il paper trading non è un add-on accessorio, ma una componente
**centrale** della roadmap (nuova Fase 6 dedicata). I principi di design sono
non negoziabili:

### Principi non negoziabili

1. **No look-ahead**: un ordine generato dal segnale al tempo `t` viene
   simulato come eseguito al prossimo prezzo disponibile `t+1`, mai al prezzo
   che ha generato il segnale. È l'errore più comune e annichilisce ogni
   credibilità del test.

2. **Costi reali**: ogni trade simulato applica:
   - **Fee**: modello tarato sull'exchange di riferimento (default proposto:
     Binance spot, 0.1% maker/taker — calibrabile)
   - **Slippage**: modello iniziale lineare basato su bid-ask spread e size
     dell'ordine; raffinabile con modelli di market impact
   - **Funding rate** se in futuro entreranno strumenti derivati
   - **Spread** tra denaro/lettera, non solo prezzo "fair"

3. **Latenza simulata**: il segnale non si esegue istantaneamente. Margine
   minimo: una candela del timeframe corrente (per "breve" daily ⇒ esecuzione
   alla candela successiva).

4. **Stesso codebase tra paper e live**: l'engine di esecuzione è uno solo.
   Il modulo di execution ha due implementazioni intercambiabili dietro la
   stessa interfaccia: `PaperBroker` (simulato) e `LiveBroker` (reale, mai
   abilitato senza nuova ADR). Questo evita il "gap" tra paper e live, dove
   in genere si scopre che il codice di backtest non regge in produzione.

5. **Stato persistente e auditabile**: portfolio, posizioni aperte, storico
   ordini, equity curve devono essere persistiti (parquet/SQLite) in modo
   che ogni risultato sia **riproducibile** e **ispezionabile** giorni dopo.

6. **Metriche coerenti col backtest** (Fase 2): Sharpe, Sortino, max
   drawdown, hit rate, profit factor, time underwater, Calmar, ecc. Le stesse
   metriche del backtest, applicate all'equity curve simulata. Così paper e
   backtest sono confrontabili direttamente.

7. **Verità è l'equity curve, non i singoli trade**: un singolo trade vincente
   non dice niente. Il P&L cumulativo su molti trade indipendenti è quello
   che conta.

### Parametri operativi iniziali (calibrabili)

| Parametro | Default proposto | Note |
|---|---|---|
| Capitale virtuale iniziale | 10 000 EUR | Da confermare; potrebbe essere allineato al portafoglio reale (~1 200 EUR/anno) o multiplo per testare scale |
| Exchange di riferimento | Binance spot | Per modello fee e spread |
| Direzione | Solo long inizialmente | Coerente col portafoglio reale dell'utente, no leverage, no short. Short via derivati introducibile in seguito con nuova ADR |
| Tipi di ordine supportati | Market, Limit | Stop-loss e take-profit in seconda iterazione |
| Position sizing | Percentuale fissa del capitale (configurabile) | Strategie più sofisticate (Kelly, vol-targeting) testabili in seguito |
| Granularità di esecuzione | Una candela del timeframe del segnale | "Breve" daily ⇒ esecuzione daily |
| Allocation across assets | Il segnale può proporre allocazione multi-asset | Es. "60% BTC, 30% ETH, 10% cash" |

### Conseguenze

- **Nuova Fase 6 in `ROADMAP.md`**, dedicata al paper trading engine. La
  precedente "Fase 6 — Output, dashboard, sintesi" diventa Fase 7.
- L'engine sarà un modulo `src/execution/` con interfaccia `Broker` astratta
  e implementazioni `PaperBroker` (Fase 6) e `LiveBroker` (futuro, ADR esplicita)
- La modellazione realistica dei costi è prerequisito: già richiesto dalla
  Fase 2 (backtest), ora ancora più rilevante
- Il paper trading "live" (su segnali generati in tempo reale, non storici)
  richiede che la data pipeline sia anche eseguibile in modalità real-time
  o quasi-real-time. Dipende da Q10 (frequenza ingestion notizie) e dal
  timeframe scelto
- **Open question aperta**: capitale virtuale iniziale (Q13), exchange di
  riferimento (Q14), modello di slippage (Q15) — vedi `OPEN_QUESTIONS.md`

### Cosa NON fa il paper trading

- Non ti dice che "guadagnerai" davvero: un mese positivo in paper non
  garantisce nulla nel mondo reale. Servono mesi e mesi di equity curve
  positiva contro benchmark
- Non sostituisce il backtest: il backtest è la fase di "ottimizzazione e
  selezione", il paper trading è la fase di "validazione finale e onesta"
- Non simula gli effetti psicologici reali del trading (paura/avidità).
  Questo limite è inevitabile e va ricordato

---

## ADR-011 — Paper trading: scenari multipli con possibilità di reset

**Data**: 2026-05-28
**Stato**: Accepted
**Risolve**: OPEN_QUESTIONS Q13

**Contesto**: ADR-010 ha richiesto di definire il capitale virtuale iniziale.
L'utente vuole l'opzione **multi-scenario** (più portafogli paralleli con
size diverse) e la possibilità di **riavviare** (resettare) gli scenari.

**Decisione**:

- Il `PaperBroker` supporta **N scenari indipendenti**, ciascuno identificato
  da un `scenario_id` (es. `small_1k`, `mid_10k`, `large_100k`, o nomi
  custom). Default proposti: 1 000 / 10 000 / 100 000 EUR.
- Ogni scenario ha il proprio portfolio, storico ordini, equity curve.
- Esiste un comando di **reset** che azzera uno scenario specifico (capitale
  riportato all'iniziale, posizioni chiuse, storico archiviato e non
  cancellato — l'archivio resta per audit/confronto).
- Esiste un comando di **fork**: clonare uno scenario in un nuovo ID per
  testare strategie alternative dallo stesso punto di partenza.
- Lo storico degli scenari "archiviati" tramite reset resta consultabile.
  Non si cancella mai nulla: l'archivio è valore per analisi a posteriori
  (es. "cosa ha funzionato sul mio scenario 10k tra gen e mar 2027?").

**Conseguenze**:

- Schema dati con scenario_id come dimensione di partizionamento
- Engine deve gestire più portfolio simultanei → necessità di state isolato
  per scenario
- UI futura (Fase 7) deve permettere selezione scenario e comparazione
  side-by-side
- Vincolo: gli scenari sono **paralleli**, non sequenziali. Tutti vedono
  gli stessi segnali nello stesso momento, differiscono solo in capitale e
  sizing — utile per studiare scaling

---

## ADR-012 — Paper trading: doppio modello broker, Binance e Kraken

**Data**: 2026-05-28
**Stato**: Accepted
**Risolve**: OPEN_QUESTIONS Q14

**Contesto**: ADR-010 proponeva Binance come exchange di riferimento per il
modello fee. L'utente fa trading reale su **Kraken**. Per la futura
transizione a live, modellare anche Kraken è prezioso.

**Decisione**:

- Modelliamo **due broker simulati** in parallelo: **Binance** e **Kraken**.
- Default per scenari nuovi: **Binance** (più liquido, fee più bassa, è il
  benchmark "best-case").
- L'utente può creare scenari con broker = **Kraken** per simulare le
  condizioni reali del suo exchange.
- Il modello fee è **parametrizzato per broker**:
  - Binance spot: ~0.10% maker/taker (default tier 0)
  - Kraken spot: ~0.16% maker / ~0.26% taker (tier "Starter", calibrabile)
- Il confronto Binance-vs-Kraken sullo stesso segnale mostra l'impatto reale
  delle fee sulle metriche.

**Conseguenze**:

- Interfaccia `Broker` astratta espone configurazione fee parametrica
- Aggiunta colonna `broker` nello schema scenari
- Documentazione dei tier di fee con riferimenti ufficiali (vanno
  ri-verificati prima dell'effettivo go-live, le fee cambiano)
- Quando arriverà il momento del live trading reale, il default broker sarà
  Kraken (allineato al portafoglio dell'utente). Decisione formale rinviata
  alla futura ADR sul live trading

---

## ADR-013 — Modello di slippage: proporzionale al bid-ask spread

**Data**: 2026-05-28
**Stato**: Accepted
**Risolve**: OPEN_QUESTIONS Q15

**Contesto**: ADR-010 richiedeva di definire il modello di slippage del paper
broker. L'utente ha delegato la scelta.

**Decisione**: Modello a due componenti, semplice ma non ingenuo.

```
slippage_cost = max(half_spread_pct, base_cost_bps) * size_adjustment
size_adjustment = 1 + impact_coeff * (order_value / avg_daily_volume)
```

Dove:

- **`half_spread_pct`**: metà del bid-ask spread medio storico per
  l'asset (rolling 30 giorni). Per asset Tier 1: tipicamente 1–5 bps su BTC/ETH,
  più alto per SOL/LINK/POL
- **`base_cost_bps`**: floor minimo per evitare slippage zero su asset
  illiquidi senza dati di spread (default 2 bps)
- **`impact_coeff`**: coefficiente di market impact (default 0 inizialmente:
  per gli scenari fino a 100k EUR su asset Tier 1, l'impatto è trascurabile;
  attiveremo il termine se passeremo a scenari grossi o asset illiquidi)
- **`order_value`**: valore notional dell'ordine in EUR
- **`avg_daily_volume`**: volume giornaliero medio dell'asset (rolling 30 giorni)

**Direzione futura**: passare a un modello **square-root market impact** se
i risultati mostreranno sensitività significativa al modello (tipico per
ordini > 0.1% del volume giornaliero).

**Conseguenze**:

- Servono dati di spread (bid-ask) e volume per ogni asset, almeno daily
- Per dati storici di spread su crypto: Kaiko (a pagamento) o approssimazione
  via percentile inferiore di high-low (proxy gratuito)
- Il modello è calibrabile per asset, non costante — necessario per essere
  equo tra BTC e altcoin più piccole

---

## ADR-014 — Architettura asset-class-agnostic (preparare l'espansione a equity)

**Data**: 2026-05-28
**Stato**: Accepted

**Contesto**: L'utente ha espresso la volontà di estendere il sistema in
futuro al **mercato azionario classico** (equity). Le borse tradizionali
hanno proprietà diverse dal mercato crypto: orari di mercato, weekend e
festività, dividendi, splits, gap di apertura, currency multiple, fiscalità
diversa, regolamentazione diversa, set di dati e provider diversi.

Far emergere queste differenze come "patch" su una codebase crypto-only
sarebbe molto costoso. Va deciso ora il principio architetturale.

**Decisione**: Tutti i moduli del sistema (data ingestion, feature
engineering, models, backtesting, paper broker, dashboard) sono progettati
per essere **asset-class-agnostic** fin dalla Fase 1.

Concretamente:

- `Asset` è una struttura prima classe con campi:
  ```
  symbol, asset_class, exchange, currency, trading_calendar,
  fee_model, data_source, lot_size, tick_size
  ```
- `asset_class ∈ {crypto, equity, etf, forex, ...}` — enum estendibile
- Il `trading_calendar` astrae 24/7 (crypto) vs 9:30–16:00 NY (NYSE) vs
  9:00–17:30 Milano (Borsa Italiana) ecc.
- I modelli ML non assumono nulla sulla asset class. Le feature possono
  essere class-specific (on-chain solo per crypto, fondamentali solo per
  equity) ma il framework le aggrega in modo uniforme.
- Il `Broker` ha implementazioni `BinancePaperBroker`, `KrakenPaperBroker`
  (ADR-012) e in futuro `IBKRPaperBroker` o simile per equity, dietro la
  stessa interfaccia.

**Fase di implementazione effettiva**: il sistema **gira solo su crypto**
fino a paper trading consolidato (Fase 6). L'espansione equity diventa
**Fase 8** della roadmap. Ma la Fase 1 (ingestion) e le successive sono
scritte già asset-agnostic.

**Conseguenze**:

- Lieve overhead di astrazione fin dall'inizio, accettabile
- Quando aggiungeremo equity, l'effort sarà focalizzato su:
  data sources, fee models, calendari, gestione corporate actions —
  NON riscrittura di pipeline
- Vincolo per i contributori (Claude inclusa): non hardcodare assunzioni
  crypto-only (es. "il mercato è sempre aperto", "non ci sono dividendi")
- Le feature di sentiment/news sono già universalmente applicabili
- L'universe equity (quale borsa, quali titoli) è una **Open Question**
  da risolvere prima della Fase 8

---

## ADR-015 — Modulo didattico multi-livello come componente del progetto

**Data**: 2026-05-28
**Stato**: Accepted

**Contesto**: L'utente vuole un modulo didattico integrato che insegni il
mercato azionario per livelli crescenti: principiante → intermedio →
avanzato → "wolf of wall street" (esperto/pro). L'idea è duplice:
formare l'utente stesso mentre il progetto cresce, e mantenere un riferimento
consultabile sui concetti usati nel sistema.

**Decisione**:

- Il modulo didattico è una **componente di primo livello** del progetto,
  non un add-on. Vive in `education/` come collezione di documenti markdown
  organizzati per livello e tema, integrabili in futuro con notebook
  Jupyter e con la dashboard finale (Fase 7).

- **Quattro livelli**:

  1. **Principiante** (`L1_principiante/`) — *"Investor 101"*
     - Cos'è un asset, azione, obbligazione, crypto
     - Borsa, exchange, broker, custodian
     - Tipi di ordini (market, limit, stop)
     - Lettura di un grafico OHLCV
     - Fee, spread, slippage spiegati senza math
     - Concetti base di portafoglio e diversificazione
     - Fiscalità essenziale (capital gain) — solo concettuale, non consulenza

  2. **Intermedio** (`L2_intermedio/`) — *"Smart Investor"*
     - Indicatori tecnici (MA, MACD, RSI, BB) con esempi sui Tier 1
     - Analisi fondamentale: bilanci, multipli, settori
     - Risk management: position sizing, stop loss, drawdown
     - Bias cognitivi (FOMO, loss aversion, anchoring)
     - DCA vs lump sum
     - Cicli di mercato e regimi
     - Halving Bitcoin, on-chain basics

  3. **Avanzato** (`L3_avanzato/`) — *"Quantitative Investor"*
     - Backtesting onesto: look-ahead, survivorship, overfitting
     - Modelli statistici (ARIMA, GARCH)
     - ML in finanza (feature engineering, time-series CV)
     - Sentiment analysis su news
     - Derivati: futures, perpetuals, funding rate
     - Volatility e modelli di volatilità
     - Sharpe, Sortino, Calmar e quando ognuno conta

  4. **Esperto / "Wolf"** (`L4_esperto/`) — *"Professional"*
     - Market microstructure, order book dynamics
     - Factor models (Fama-French, momentum, quality)
     - Statistical arbitrage e pairs trading
     - Reflexivity e behavioral finance avanzata
     - Risk parity, Black-Litterman
     - Deep learning per series temporali
     - Considerazioni regolatorie e di compliance

- **Principi di stesura**:
  - Ogni contenuto include **esempi pratici sui dati del progetto stesso**
    (es. "ecco cosa è successo a BTC il giorno del lancio degli ETF" usando
    i nostri dati). Questa sinergia è il valore aggiunto rispetto a un
    qualsiasi libro generico.
  - I livelli sono **cumulativi**: chi legge L3 si assume conosca L1+L2.
  - Lingua: **italiano** (coerente con ADR-003).
  - Onestà: ogni capitolo include "cosa non ti sto dicendo" e "limiti di
    questo approccio". Niente promesse di facile arricchimento.

- **Cosa NON è il modulo**:
  - Non è consulenza finanziaria personalizzata
  - Non è un corso certificato
  - Non è esauriente come un libro di testo: rimanda a letture esterne
    (Hull, Tsay, Lopez de Prado, ecc.)

- **Track parallelo**: il modulo didattico cresce in **parallelo** alle fasi
  tecniche, non come fase dedicata. Si lavora su un capitolo quando il
  contenuto è "fresco" (es. scrivere il capitolo su backtesting quando si
  sta implementando la Fase 2, non prima e non a fine progetto).

**Conseguenze**:

- Nuova cartella `education/` con sottocartelle `L1_principiante/`,
  `L2_intermedio/`, `L3_avanzato/`, `L4_esperto/`
- Indice navigabile (`education/README.md`) creato all'inizio della Fase 1
- Nessuna fase dedicata in roadmap: stream parallelo
- Il modulo può essere consumato standalone (markdown) o integrato in
  dashboard (Fase 7)
- Vincolo per i contributori: quando si lavora su un argomento tecnico,
  considerare se aggiunge un capitolo educational pertinente

---

## ADR-016 — Ruolo dell'AI: filtro e sintetizzatore, non oracolo

**Data**: 2026-05-28
**Stato**: Accepted

**Contesto**: L'utente ha chiesto se l'app sarà in grado di acquisire e
processare "tutte" le informazioni utili — finanziarie, generali, di
qualsiasi tipo possa influenzare i mercati — anche tramite AI. È necessario
fissare con onestà cosa l'AI farà nel sistema, cosa NON farà, e con quale
stack e budget.

Errori comuni da evitare:
- Trattare gli LLM come oracoli predittivi ("chiediamo a Claude se BTC sale")
- Sostituire i modelli quantitativi con generative AI
- Spendere su API LLM senza un caching aggressivo
- Dipendere esclusivamente da provider esterni per funzioni critiche

**Decisione**: ruolo dell'AI definito in due layer, con confini espliciti.

### Cosa l'AI FA nel sistema

L'AI è impiegata esclusivamente sul **flusso di informazione testuale**
(news, social, documenti) per:

1. **Classificare** la rilevanza di news rispetto all'asset universe
   (binary "relevant"/"noise" + topic class)
2. **Estrarre entità** (NER): asset menzionati, persone, organizzazioni,
   eventi, paesi
3. **Calcolare sentiment** finanziario contestuale (per asset menzionato)
4. **Riassumere** documenti lunghi (FOMC minutes, white paper, relazioni
   trimestrali, lunghi thread di forum)
5. **Tradurre** news non-inglesi per normalizzare il flusso
6. **Topic modeling** e detection di narrative emergenti su finestre temporali
7. **Anomaly detection** sul volume di news (picchi, divergenze)
8. **Ricerca per similarità** ("cosa è successo in passato in situazioni
   simili?") via embedding + RAG sull'archivio storico

### Cosa l'AI NON FA

1. **Non genera segnali predittivi diretti**: i segnali di direzione,
   rendimento atteso e probabilità (ADR-007) vengono dai modelli ML
   quantitativi (sklearn, XGBoost, eventualmente PyTorch) sui dati strutturati
2. **Non sostituisce** statistica e backtesting rigoroso
3. **Non decide** di eseguire trade (paper o reali)
4. **Non interpreta** dati di mercato strutturati ("Claude, BTC è
   ipercomprato?") — quello è dominio dei modelli quantitativi
5. **Non è un componente real-time** mission-critical: la pipeline deve
   degradare graziosamente se l'AI fallisce (rate limit, downtime API)

### Stack AI a due layer

**Layer 1 — Open-source, default, gratis, riproducibile, offline**:

- **FinBERT** (o variante più recente, es. `ProsusAI/finbert`): sentiment
  finanziario su frasi/titoli
- **sentence-transformers** (es. `all-MiniLM-L6-v2` per velocità,
  `multilingual-e5` per multi-lingua): embedding per RAG e similarity
- **spaCy** (modello `en_core_web_lg` e `it_core_news_lg`): NER, parsing
- **Hugging Face transformers**: classificazione zero-shot via BART/Flan-T5,
  modelli specializzati al bisogno
- Tutto in Python, eseguibile localmente o su GPU consumer

Questo layer copre l'80% dei casi: classificazione rilevanza, NER, sentiment
base, embedding per RAG.

**Layer 2 — LLM API, selettivo, a pagamento, con budget cap**:

- **Anthropic Claude API** (preferito, in coerenza con questo ambiente di lavoro)
  o **OpenAI GPT API** come fallback
- Usato SOLO per casi che il Layer 1 non gestisce bene:
  - Summarization di documenti lunghi e complessi (>2 pagine)
  - Classificazione fine di news ambigue dove FinBERT è incerto (low-confidence triage)
  - Ricerca di analogie storiche e ragionamento qualitativo (RAG augmented)
  - Detection di narrative emergenti che richiedono ragionamento (non solo pattern)
- **Caching aggressivo obbligatorio**: ogni risposta API è cachata localmente
  (file SQLite o parquet) con hash dell'input. La stessa elaborazione non si
  paga due volte
- **Budget cap mensile iniziale: 15 EUR/mese**. Quando si avvicina al limite,
  pipeline degrada al solo Layer 1 senza interrompersi. Da calibrare in Fase 3
  con dati reali di consumo
- **Niente streaming, batch quando possibile**: ridurre overhead, sfruttare
  caching server-side

### Cosa NON acquisiamo (limiti esistenziali)

Per onestà, riportiamo cosa il sistema **non potrà mai** acquisire:

- Informazioni private, leak, insider trading (illegale, fuori scope)
- Decisioni di banche centrali prima dell'annuncio (per definizione)
- Dati Bloomberg Terminal (costo proibitivo ~24 000 EUR/anno)
- Twitter/X API tier utili (costo proibitivo ~5 000 EUR/mese, in continuo
  aumento). Da Fase 3 valutiamo alternative: scraping limitato (rischioso
  legalmente), Mastodon/Bluesky come proxy, ignorare X del tutto
- Dati real-time L2 order book (richiede infrastruttura dedicata, fuori scope
  ricerca)
- Black swan veri (per definizione imprevedibili)

**Conseguenze**:

- Modulo `src/ai/` con sotto-moduli `nlp_local/` (Layer 1) e `llm_api/`
  (Layer 2) chiaramente separati
- Interfaccia uniforme: il codice chiamante non sa se la classificazione viene
  da Layer 1 o Layer 2 (decisione presa dal router interno in base a
  confidence e budget)
- File `.env` per chiavi API (mai in commit, già coperto in CLAUDE.md)
- Modulo di tracking del budget speso (utility da implementare in Fase 3)
- Cache layer condiviso tra Layer 1 e Layer 2
- Pipeline deve essere testata anche in modalità "Layer 2 disabilitato" per
  garantire degrado grazioso

---

## ADR-017 — Tassonomia prioritizzata delle fonti dati

**Data**: 2026-05-28
**Stato**: Accepted

**Contesto**: L'utente vuole un sistema che integri il maggior numero
possibile di informazioni rilevanti. Per evitare l'errore di "acquisire tutto"
(rumore, costi, overfitting, scope ingovernabile) servono **tier di priorità**
chiari, ciascuno collegato alla fase della roadmap in cui viene integrato.
Principio guida: ADR-014 (asset-class-agnostic), VISION principio 8
(selettività > volume).

**Decisione**: quattro tier di fonti, con criterio di **potere incrementale**
da verificare prima di consolidare ogni fonte.

### Tier 1 — Core (da implementare in Fase 1–2)

Sono le fonti **indispensabili** per qualsiasi modello credibile.

| Fonte | Categoria | Accesso | Note |
|---|---|---|---|
| **Binance Public API** | Market data crypto (OHLCV, depth) | Free, REST + WebSocket | Standard de facto, storico decennale |
| **Coinbase Pro API** | Market data crypto secondario | Free | Per cross-check e ridondanza |
| **CoinGecko** | Aggregato market data + metadata | Free tier limitato | Lista top 20, market cap, dominance |
| **Yahoo Finance** | Equity & indici per contesto | Free | DXY, S&P 500, NASDAQ, oro (ADR-005) |
| **Etherscan** | On-chain Ethereum base | Free tier | Transazioni, gas, balance, eventi |
| **Blockchain.com / mempool.space** | On-chain Bitcoin base | Free | Hash rate, mempool, halving timeline |
| **Glassnode free tier** | On-chain metrics aggregate | Free limitato | Active addresses, exchange flows base |
| **FRED (Federal Reserve)** | Macro USA | Free, ampio storico | Tassi, inflazione, M2, treasury yields |
| **CryptoPanic free tier** | News crypto aggregate | Free limitato | Triage iniziale del flusso news |

### Tier 2 — Estensione (Fase 3–4)

Fonti che aggiungono **segnale ortogonale** rispetto al Tier 1.

| Fonte | Categoria | Accesso | Razionale |
|---|---|---|---|
| **RSS Cointelegraph / CoinDesk / The Block** | News crypto specializzate | Free | Più granulari di CryptoPanic |
| **RSS Reuters / Bloomberg headlines / FT** | News finanza generale | Free (RSS) | Macro narrative, eventi globali |
| **ECB SDW** | Macro europeo | Free | DXY è USA-centric, serve contesto EUR |
| **Google Trends** | Attenzione/hype proxy | Free | Lead indicator per retail interest |
| **Reddit API** | Social sentiment retail | Free, OAuth | r/cryptocurrency, r/wallstreetbets, r/CryptoMarkets |
| **Hacker News API** | Sentiment tech | Free | Adoption signals, opinion leaders tech |
| **TechCrunch / The Verge RSS** | News tech | Free | Annunci adoption, partnership, regulation tech |
| **Telegram canali pubblici** | Social sentiment crypto | Free via bot | Selezionati, con filtro qualità |

### Tier 3 — Avanzata (Fase 4–5, condizionata a valore aggiunto dimostrato)

Fonti che richiedono **infrastruttura più complessa** o sono utili solo per
analisi specifiche.

| Fonte | Categoria | Accesso | Note |
|---|---|---|---|
| **GDELT** | Eventi globali geopolitici | Free, ma enorme | Database di eventi mondiali, utile per macro |
| **RSS Politico / Foreign Affairs / Foreign Policy** | News geopolitica | Free | Per analisi macro/regulation |
| **Calendario eventi** (Investing.com, Forex Factory) | Eventi calendarizzati | Free scraping | FOMC, halving, earnings, CPI release |
| **Reddit r/CryptoMoonShots, altcoin-specifici** | Retail buzz altcoin | Free | Per Tier 2 asset (ADR-005) |
| **Substack / Medium feeds selezionati** | Long-form analysis | Free RSS | Curatela necessaria |
| **Earnings call transcripts** (per equity Fase 8) | Fondamentale equity | Free su SEC EDGAR | Solo quando entreremo in equity |

### Tier 4 — Premium (gated da ADR-008)

Fonti **a pagamento** valutabili solo se le precedenti dimostrano limiti
concreti.

| Fonte | Costo indicativo | Quando valutarla |
|---|---|---|
| **Glassnode Standard/Pro** | ~30–800 EUR/mese | Se on-chain free risulta insufficiente |
| **Nansen** | ~150 EUR/mese | Per smart money tracking, gated da uso reale |
| **CryptoQuant Pro** | ~30 EUR/mese | Per exchange flows granulari |
| **Kaiko market data** | Custom | Per spread/order book storico (slippage modeling) |
| **CryptoPanic Pro** | ~30 EUR/mese | Se Tier 2 news risulta limitante |

### Esclusioni esplicite (NON acquisiamo)

| Fonte | Motivo | Tipo di esclusione |
|---|---|---|
| **Bloomberg Terminal** | Costo proibitivo (~24 000 EUR/anno) | Economica (rivisitabile con budget) |
| **Twitter / X API tier utili** | Costo proibitivo (~5 000 EUR/mese), policy volatile | Economica (rivisitabile) |
| **Refinitiv Eikon** | Costo proibitivo | Economica (rivisitabile) |
| **Insider information** | Inaccessibile per natura + reato (MAR UE Art. 14) | Impossibile + illegale (ADR-018 Categoria A) |
| **Leak già pubblici** (Panama Papers e simili) | Uso come signal vietato da MAR indipendentemente dall'origine | Scelta etico-legale (ADR-018 Categoria B) |
| **Scraping aggressivo** (aggirare CAPTCHA, anti-bot, ToS) | Violazione ToS, rischio art. 615-ter c.p., IP ban | Scelta etico-legale (ADR-018 Categoria B) |
| **Dati real-time L2 order book per tutti gli asset** | Infrastruttura dedicata, fuori scope ricerca | Tecnica + scope |

**Vedi ADR-018** per la classificazione completa (impossibile vs scelta vs
zona grigia) e la procedura di valutazione per fonti grey-zone.

### Criterio di "potere incrementale"

Prima di consolidare ogni nuova fonte:

1. **Hypothesis**: scrivere quale segnale ci si aspetta che aggiunga, e in
   quale fase del modello
2. **Bias check**: la fonte è soggetta a survivorship bias? look-ahead? È
   stata "scoperta" dopo aver visto il dato?
3. **Orthogonality test**: la fonte è correlata >0.7 con fonti già presenti?
   Se sì, probabilmente è duplicata
4. **Cost/benefit**: il costo (denaro + complessità pipeline + manutenzione)
   è giustificato dal segnale atteso?
5. **Drop policy**: se a 3 mesi dall'integrazione non ha mostrato segnale,
   si rimuove dalla pipeline

Ogni decisione di **aggiungere o rimuovere una fonte** dopo la Fase 1 va
documentata con una nota in `DECISIONS.md` (non serve ADR completa, basta
una riga di log).

**Conseguenze**:

- `src/ingestion/` organizzato per tier, ciascuno con la sua sotto-cartella
- Configurazione delle fonti in `config/sources.yaml` (o equivalente):
  enable/disable, rate limit, schedule
- Caching e rate-limiting condivisi tra tutte le fonti
- Log centralizzato dei dati acquisiti con quality metrics
- La Fase 1 implementa **solo Tier 1**. I tier successivi entrano dopo
  decisione esplicita sul valore aggiunto

---

## ADR-018 — Etica e legalità nell'acquisizione dati: impossibile vs scelta

**Data**: 2026-05-28
**Stato**: Accepted

**Contesto**: ADR-017 elenca "esclusioni esplicite" delle fonti dati che non
acquisiamo. Tra queste comparivano "insider info, leak, scraping aggressivo
— illegale o legalmente grigio", in una formulazione ambigua che mescola due
ragioni profondamente diverse di esclusione:

1. **Impossibilità tecnica**: fonti **non accessibili** in nessuna forma
   legittima (sarebbe necessario commettere un reato per ottenerle)
2. **Scelta etico-legale**: fonti **tecnicamente accessibili** ma che
   scegliamo di non integrare per ragioni di legalità, etica, rischio
   reputazionale o sistemico

La differenza non è accademica: gli **impossibili tecnici sono fissi**, le
**scelte sono revisabili** con una nuova ADR (es. se cambia la legge, o se
emerge una via legalmente pulita). Inoltre esiste una **zona grigia** che
richiede valutazione caso per caso e va resa esplicita per non risolverla
in modo arbitrario sotto pressione.

Riferimento normativo principale per l'ambito UE/IT (giurisdizione di
riferimento del progetto): **Regolamento (UE) 596/2014** (Market Abuse
Regulation, MAR), in particolare artt. 7 (definizione di inside information),
8 (insider dealing), 14 (divieto di insider dealing). Anche **GDPR**
(Reg. 2016/679) per qualsiasi dato personale, e **art. 615-ter c.p.**
italiano (accesso abusivo a sistema informatico).

**Decisione**: tre categorie esplicite con trattamento diverso.

### Categoria A — Impossibile tecnicamente (e illegale)

Fonti che richiederebbero un reato per essere ottenute. Non esiste una via
legittima per acquisirle.

| Fonte | Perché impossibile |
|---|---|
| **Insider information** (notizie materiali non pubbliche su aziende quotate o asset) | Per definizione non pubbliche; possedute solo dagli insider; arrivare a noi richiederebbe complicità nel reato di insider dealing |
| **Documenti riservati di banche centrali pre-annuncio** | Sotto embargo, accesso fisicamente controllato |
| **Order book private di market maker / dark pools** | Infrastruttura privata, non disponibile a soggetti esterni |
| **Comunicazioni private** (Slack/email aziendali, chat di trading desk) | Confidenzialità contrattuale + segreto industriale |
| **Dati ottenibili solo tramite hacking** (es. exchange internals, wallet privati) | Reato penale a prescindere dall'uso |

**Revocabilità**: nessuna. Sono limiti fisici per costruzione. Se un giorno
qualcosa di questi diventasse pubblico, riclassifichiamo nella relativa
categoria (B o C).

### Categoria B — Tecnicamente possibile ma scelta di non integrare

Fonti accessibili in qualche forma, che scegliamo consapevolmente di non
toccare.

| Fonte | Tecnicamente accessibile perché | Perché la escludiamo |
|---|---|---|
| **Leak già pubblici** (Panama Papers, Pandora Papers, leak di SEC filings, breach di exchange) | Una volta pubblicati restano spesso online | MAR Art. 14 vieta l'uso di "inside information" *indipendentemente dall'origine*. Rischio penale, civile e reputazionale. Eticamente: lesivo del fair price discovery |
| **Scraping aggressivo** (aggirare CAPTCHA, anti-bot, proxy rotation per violare rate limit) | Tools come Selenium/Playwright + servizi di proxy lo rendono fattibile | Violazione ToS (responsabilità contrattuale); possibile violazione di norme su accesso abusivo (art. 615-ter c.p. se ci sono misure di sicurezza aggirate); GDPR se ci sono dati personali; IP ban definitivo che ci toglierebbe anche l'accesso legittimo |
| **API Twitter/X via account non legittimi** o reverse engineering dell'app | Tecnicamente fattibile | Violazione ToS, rischio account ban a cascata, scelte di Musk-era policy non garantiscono stabilità |
| **Reverse engineering di app finanziarie chiuse** (es. interfaccia interna broker) | Spesso fattibile | Violazione ToS, possibili violazioni di copyright/DMCA-equivalenti |
| **Acquisto di dataset di provenienza incerta** (es. mercato "grey" di dati on-chain etichettati) | Esistono fornitori non ufficiali | Catena di provenienza non verificabile = rischio legale ed etico |
| **Dati personali scrapeable da social** (profili pubblici di trader specifici da seguire) | Tecnicamente fattibile | GDPR: il fatto che siano pubblicamente visibili non li rende liberamente processabili a fini di profilazione |

**Revocabilità**: ognuna di queste esclusioni è **revisabile** con una nuova
ADR se cambiano le condizioni che la giustificano (cambio di legge,
disponibilità di una via legalmente pulita, mutamento del rischio
reputazionale). Non è una "esclusione morale per sempre", è una decisione
operativa tracciata.

### Categoria C — Zona grigia (judgement call documentato caso per caso)

Fonti che **non sono nettamente classificabili** e richiedono valutazione
specifica al momento della valutazione. Quando una di queste fonti viene
presa in considerazione, va aggiunta una nota in `DECISIONS.md`
(non serve ADR completa) con la decisione e il razionale.

| Tipologia | Considerazioni |
|---|---|
| **Dataset accademici con dati Twitter pre-2023** | Spesso raccolti legalmente quando le API erano permissive. Caso per caso: verificare la licenza del dataset, l'attualità dei dati, l'assenza di dati personali sensibili |
| **Dataset Kaggle / HuggingFace con licenza permissiva** | Verificare provenienza dichiarata, licenza esplicita, eventuali clausole "research only" |
| **Web archive (archive.org) di pagine ora paywalled** | Tecnicamente accessibili. Considerare se l'archivio era autorizzato dal publisher (archive.org rispetta robots.txt) |
| **Forum e mailing list pubbliche** (es. Bitcoin-dev, ethereum-research) | OK se ricerca di interesse pubblico, attenzione ai dati personali |
| **Telegram canali pubblici di "trader influencer"** | Pubblici ma con potenziali questioni GDPR per dati personali. Anonimizzare quando possibile |
| **Discord pubblici di community crypto** | Stessa logica di Telegram |
| **GitHub di progetti aperti** (es. monitoraggio commit attivity di protocolli) | Generalmente OK, GitHub ToS lo permettono |
| **Filings ufficiali in forma machine-readable** (SEC EDGAR, ESMA) | Pubblici per design, integrazione benvenuta |

**Procedura per zona grigia**:

1. Quando si valuta una fonte di Categoria C, scrivere in `DECISIONS.md` una
   voce in formato:
   ```
   ### Nota grey-zone YYYY-MM-DD — <fonte>
   - Provenienza dichiarata: ...
   - Licenza: ...
   - Rischio identificato: ...
   - Decisione: usare / non usare / usare con vincoli (quali)
   - Riferimento ADR principale: ADR-018
   ```
2. Se la decisione è "non usare" e la fonte sembra strategica, considerare
   se trovare un'alternativa di Categoria pulita
3. Se la decisione è "usare con vincoli" (es. anonimizzazione, filtri),
   i vincoli vanno implementati nel codice di ingestion

### Procedura per riclassificare o revisare

- **B → A**: se una fonte di Categoria B diventa fisicamente inaccessibile
  (es. il sito chiude), spostarla in A
- **B → C**: se emerge una via legalmente pulita per accedere a parte dei
  dati (es. nuova API ufficiale), aprire una nota grey-zone
- **C → integrazione**: se valutata positivamente, la fonte entra nella
  tassonomia di ADR-017 al tier appropriato
- **Revoca di esclusione B**: richiede nuova ADR che cita esplicitamente
  questa ADR-018 e motiva il cambio di condizioni

### Perché questa distinzione conta

- **Per la trasparenza del progetto**: chi legge i file capisce che alcune
  esclusioni sono **principi**, altre sono **opportunità di lavoro futuro**
- **Per non rivisitare le decisioni sotto pressione**: quando arriva la
  tentazione di "violare un ToS per un mese per vedere se il segnale c'è",
  questa ADR è già la risposta documentata: no, e perché
- **Per il valore del sistema**: un sistema che opera in chiarezza legale
  ha valore di lungo termine, uno che opera in zona grigia è una bomba a
  orologeria reputazionale

**Conseguenze**:

- Aggiornata sezione "Esclusioni esplicite" di ADR-017 con riferimento a
  questa ADR
- Nuovo template "Nota grey-zone" disponibile in `DECISIONS.md` per zona
  grigia (sopra)
- Il modulo `src/ingestion/` non deve mai contenere codice per scraping
  aggressivo (no proxy rotation per aggirare rate limit, no CAPTCHA solver,
  no fake user-agent oltre lo strettamente necessario per essere identificabili
  come bot del nostro progetto). Convenzione: ogni richiesta HTTP usa un
  `User-Agent` esplicito identificativo
- Nessun dato personale (PII) viene memorizzato senza necessità documentata
  e base giuridica chiara (GDPR Art. 6)

---

## ADR-019 — Mapping ticker per POL: usare MATIC-USD su Yahoo

**Data**: 2026-05-28
**Stato**: Accepted
**Risolve**: Q21 (parzialmente — vedi "Conseguenze")

**Contesto**: Il ticker `POL-USD` su Yahoo Finance — pur essendo il simbolo
post-rebrand corretto per Polygon (rinominato MATIC→POL nel settembre 2024)
— ha uno storico troncato a **2020-08-07 → 2023-10-31** (1181 righe, nessun
dato successivo). Il vecchio simbolo `MATIC-USD`, invece, copre
**2019-04-28 → 2025-03-24** (2158 righe, 0 gap), perché Yahoo ha continuato
a popolarlo come ticker storico del pre-rebrand fino al cutover di marzo
2025, dopo cui anche MATIC-USD è stato congelato.

Nessun simbolo Yahoo, da solo, fornisce uno storico continuo dalla nascita
del token fino ad oggi (2026).

**Decisione**:
- L'asset interno resta `POL` (simbolo canonico del progetto, riflette il
  rebrand)
- Sul provider Yahoo, mappiamo `POL.yahoo_symbol = "MATIC-USD"` per ottenere
  lo storico più lungo e continuo disponibile da Yahoo
- Su altri provider (Binance, CoinGecko, quando aggiunti), usiamo i simboli
  post-rebrand (`POLUSDT`, `polygon-ecosystem-token`)
- Il gap residuo (2025-03-24 → presente, ~14 mesi) sarà chiuso quando in
  Fase 1 aggiungeremo Binance/CoinGecko come sorgenti

**Conseguenze**:
- ✅ Storico Yahoo per POL passa da ~3 anni a ~6 anni (utile per EDA storico)
- ⚠️ POL su Yahoo è incompleto fino a quando non aggiungiamo altri provider:
  qualsiasi feature engineering basato solo su Yahoo per POL deve trattare
  i dati come "storici, non aggiornati"
- ⚠️ Q21 non è completamente chiusa: il gap recente resta da risolvere via
  multi-source (rimandato al punto 3 dello "Cosa serve fare" in STATUS.md)
- 🔄 Quando in Fase 1+ avremo dati Binance, andrà valutato se concatenare
  Yahoo (storico fino 2025-03) + Binance (da lì in poi) o se affidarsi a un
  singolo provider (Binance copre POLUSDT post-2024 e MATICUSDT pre-2024,
  decisione da prendere quando avremo i dati Binance in mano)
- 💡 Lezione generale: il mapping `Asset → simbolo provider` non è 1:1
  banale dopo eventi corporate (rebrand, merger, fork). Va trattato come
  configurazione esplicita per ogni provider, non assunto come `f"{symbol}-USD"`

---

## ADR-020 — Binance via api.binance.us per restrizione geografica

**Data**: 2026-05-28
**Stato**: Accepted
**Risolve**: parte operativa di Q21bis (gap recente POL) e la decisione
implicita "quale Binance".

**Contesto**: ADR-017 prevede Binance come sorgente Tier 1 per granularità
intra-day e volumi di exchange. La sessione 2 ha verificato che
`api.binance.com` risponde **HTTP 451 — restricted location** dalla
regione di rete del nostro ambiente (esito coerente con i termini di
servizio Binance, non con la network policy del sandbox).

Per ADR-018 questa è una "scelta etico-legale": non tentiamo di aggirare
il blocco geografico (VPN, proxy, fake-UA), perché la decisione di
Binance è esplicita e nei suoi ToS.

**Decisione**:
- L'implementazione `BinanceSource` parametrizza il base URL.
- **Default**: `https://api.binance.us` (entità USA-compliant, schema REST
  identico a binance.com). Tutti i nostri Tier 1 pair sono disponibili
  (BTCUSDT, ETHUSDT, SOLUSDT, LINKUSDT, POLUSDT, MATICUSDT).
- In ambienti con accesso a binance.com, si può istanziare
  `BinanceSource(base_url="https://api.binance.com")` senza altre
  modifiche.
- L'errore HTTP 451 viene rilevato esplicitamente e ri-lanciato come
  `PermissionError` con messaggio che cita questo ADR.

**Conseguenze**:
- ✅ Sblocca l'integrazione Binance in questo ambiente con un solo flag
- ✅ Apre dati granulari (klines intra-day) e cross-validation con Yahoo
- ✅ Chiude la parte "fetch reale" di Q21bis: POLUSDT su binance.us
  parte da 2025-01-16, copre quindi il gap che Yahoo non serviva
- ⚠️ Universe più piccola di binance.com: alcuni asset (es. token non
  registrati SEC) sono assenti. Non impatta i nostri 5 Tier 1 attuali,
  ma da tenere a mente per future espansioni
- ⚠️ Volumi binance.us << binance.com: per analisi di order flow / depth
  che dipendono dal volume assoluto i numeri non sono rappresentativi
  del mercato globale. Per il prezzo (che è oggetto della Fase 1) la
  differenza è trascurabile (cross-validation BTC con Yahoo:
  log-return correlation 0.996)
- 🔄 Quando il sistema andrà fuori dal sandbox (deployment futuro),
  basta cambiare la stringa del base URL — niente refactor

**Riferimenti**:
- POL/MATIC consistency validata (rapporto 0.998 ± 0.007 sull'overlap
  2025-01-16 → 2025-03-24, log-return correlation 0.977)
- BTC consistency Yahoo↔Binance.us su 2439 giorni comuni: differenza
  % media 0.14%, mediana 0.07%, max 3.72% (un singolo outlier 2021-12-14)

---

## ADR-021 — Composizione multi-source: concat con flag di provenance

**Data**: 2026-05-28
**Stato**: Accepted
**Risolve**: Q22

**Contesto**: Dopo ADR-019 + ADR-020 abbiamo, per POL, due serie storiche
che insieme coprono dal 2019 al presente ma nessuna delle due da sola lo
fa. Validazione (ADR-020) mostra che i prezzi sono operativamente
equivalenti (ratio 0.998 ± 0.007 nei 68 giorni di overlap, log-return
correlation 0.977).

Servono regole esplicite per produrre una "serie POL canonical" che il
feature engineering possa usare senza ricostruire la composizione ogni
volta. Stesso problema si ripresenterà per qualunque asset multi-source
(es. quando aggiungeremo CoinGecko per BTC dominance, o se in futuro
splittiamo BTC tra Coinbase+Binance).

**Decisione**:
- Funzione pura `compose_ohlcv(sources)` in `src/ingestion/composer.py`.
  Input: lista di `(DataFrame, source_name)` in ordine di **priorità
  crescente**.
- **Policy di overlap**: later-listed source wins. Quando due (o più)
  serie hanno la stessa data, la più "fresca/autoritaria" (ultima in
  lista) vince; la precedente viene scartata silenziosamente per quella
  riga.
- **Colonna `source`** aggiunta all'output: ogni riga porta il proprio
  provenance label (`"yahoo"`, `"binance"`, ecc.). Mai perdere l'audit
  trail.
- **No re-baselining** del livello al cutover: per POL il ratio è ~1
  (0.998), quindi una concatenazione semplice non crea salti visibili.
  Se in futuro emergerà un asset con ratio significativamente diverso
  da 1, si valuterà allora un adjustment di livello (separato dal
  composer base).
- Output persistito in `data/processed/{symbol}_{interval}.parquet`,
  separato dai raw per provider.

**Conseguenze**:
- ✅ Feature engineering downstream opera su una sola serie per asset,
  zero accoppiamento ai provider
- ✅ La colonna `source` consente filtri di sanity ("usa solo Yahoo se
  vuoi long history pulita", "salta i giorni Binance se sospetti
  qualità diversa", ecc.) senza ri-ingest
- ✅ Nuovi provider si aggiungono in coda alla lista → diventano
  authoritative per l'overlap. Semantica naturale.
- ⚠️ La policy "later wins" è una scelta di default. Asset con
  qualità inversa (provider nuovo peggiore dei precedenti) chiederanno
  un over-ride esplicito. Soluzione: invertire l'ordine in lista quando
  si compongono — la funzione resta neutra
- ⚠️ Non viene riconciliato il **volume** (le venue hanno scale diverse).
  Il composer prende il volume dalla source vincente per ogni riga; va
  bene come ordering ma non per analisi di market depth assoluta.
  Documentare in `OPEN_QUESTIONS` quando diventerà rilevante
- 💡 Per ora applicato solo a POL. Gli altri Tier 1 hanno copertura
  Yahoo sufficiente e non beneficiano della composizione. Aggiungere
  on demand

**Output di prima applicazione**:
- `data/processed/POL_1d.parquet`: 2588 righe, 2019-04-28 → 2026-05-28
  (Yahoo 2090 + Binance 498 dopo dedup di 68 giorni di overlap)

---

## ADR-022 — Snapshot persistence: parallel "latest" + append "history"

**Data**: 2026-05-29
**Stato**: Accepted
**Risolve**: Q24

**Contesto**: A partire da Sessione 2 (CoinGecko, `global_latest.parquet`
+ `top_20_latest.parquet`) ed esteso in Sessione 3 (Etherscan: ETH supply,
gas oracle, ETH price, ERC-20 supplies — 5 file in più), il sistema
produce **snapshot di stato corrente** che ogni run sovrascriveva. Sette
file potenzialmente preziosi venivano distrutti ad ogni fetch.

La dominance time series, le supply storiche, il gas mainnet **sono
feature naturali** per la Fase 2 (regime detection, on-chain signals). Se
non li accumuliamo dal momento in cui li abbiamo a disposizione, perdiamo
mesi di history che non torneranno (alcune di queste serie storiche
non sono disponibili sui portali free).

Q24 aveva quattro opzioni:
- **A**: `_latest` overwrite + `_history` append in parallelo
- **B**: solo file datati `{label}_YYYYMMDD.parquet` + glob al read
- **C**: DuckDB su questi snapshot
- **D**: solo latest, rinunciamo alla history

**Decisione**: Opzione **A**.

- Per ogni snapshot scrivo **due file** parallelamente:
  - `{label}_latest.parquet`: sovrascritto, sempre lo stato più recente
    (utile per query "qual è il valore corrente?")
  - `{label}_history.parquet`: appended (utile per build di time
    series dai snapshot ripetuti)
- Implementazione: funzione pura `write_snapshot()` in
  `src/ingestion/snapshot.py`. Due modi:
  - **Single-row snapshot** (DataFrame con DatetimeIndex named
    `snapshot_at`): dedup history sull'index, idempotente nello stesso
    minuto
  - **Multi-row snapshot** (DataFrame indexed da una primary key come
    `rank` o `symbol`): passa `snapshot_at` + `primary_key=[…]`, la
    funzione fa `reset_index()`, aggiunge la colonna `snapshot_at`, e
    dedup history su `(snapshot_at, *primary_key)`
- **Ordine di scrittura**: history first, latest after. Un latest stale
  è recuperabile dalla history; il contrario no
- Frequenza di esecuzione: a discrezione di chi lancia gli script. Per
  popolare history serve eseguire periodicamente (cron, GitHub Actions
  schedulata, o esecuzione manuale). Decisione di automation rimandata
  a quando l'utente vorrà popolare history seriamente

**Conseguenze**:
- ✅ Gas, dominance, supply, prezzi snapshot ora accumulano time series
  reali dal momento in cui si esegue il fetch
- ✅ API stabile e testata (7 test unitari, no network), riutilizzabile
  per qualsiasi futuro source snapshot-based
- ✅ `_latest` continua a funzionare per le query single-state; consumer
  esistenti non cambiano
- ⚠️ History cresce indefinitamente. Per ora non serve gestione — i
  snapshot single-row pesano pochissimo, anche 10 anni di snapshot
  giornalieri = ~3.6k righe. Top-20 cresce di 20 righe/snapshot, ma
  resta in MB anche con anni di history
- ⚠️ Schema della history è fisso. Se in futuro Etherscan aggiunge
  campi (es. ulteriori componenti di ETH supply), il read di history
  vecchia avrà colonne `NaN`. Gestibile, ma da tenere a mente
- 💡 Per snapshot ad alta frequenza in futuro (es. gas oracle ogni
  minuto), si valuterà se passare a DuckDB (opzione C originale) o a
  un layout partizionato per data. Per la Fase 1-2 attuale, parquet
  semplici sono adeguati
- Il pattern usato da CoinGecko (`global`, `top_20`) ed Etherscan
  (5 snapshot) è subito disponibile per qualsiasi futuro provider
  snapshot-based (es. Blockchain.com per BTC on-chain, FRED ALFRED
  per macro vintages, ecc.)

---

## ADR-023 — Sentiment Layer 1: lessico (VADER) come punto di partenza

**Data**: 2026-05-30
**Stato**: Accepted
**Risolve**: Q9

**Contesto**: ADR-016 definisce una scala a layer per il testo. La Fase 3 ha
bisogno di un primo scorer di sentiment sulle news. Opzioni (Q9): Layer 1
lessico (VADER / Loughran-McDonald), Layer 2 transformer finance-tuned
(FinBERT → `transformers`+`torch`, ~2-3 GB), Layer 3 LLM API (costo per
chiamata). CLAUDE.md vieta dipendenze pesanti senza giustificazione; ADR-016
prescrive di partire dal layer più economico e salire solo se un segnale
misurato lo giustifica.

**Decisione**: partire con **Layer 1 = VADER** (`vaderSentiment`):
- Lexicon+rules, deterministico, nessun peso/GPU/API; dipendenza leggera (no torch)
- Compound score in `[-1, +1]`; scoring sul **titolo** (i summary RSS sono rumorosi)
- Modulo `src/ai/lexicon/` (Layer 1, distinto da `src/ai/nlp_local/` = Layer 2)
- **Caveat onesto**: VADER è general-domain, non finance-tuned → è un *baseline*.
  Salita a FinBERT (Layer 2) **solo** se il potere predittivo misurato lo
  giustifica — decisione separata, futura ADR

**Conseguenze**:
- `score_text`, `score_news_frame`, `daily_sentiment` in `src/ai/lexicon/`
- Nessun download di modelli, nessun budget LLM impegnato (Q19/Q20 restano aperte)
- La promozione a Layer 2 è subordinata a evidenza empirica, non assunta

## ADR-024 — Allineamento temporale news↔prezzo: publication-time + lag di sicurezza

**Data**: 2026-05-30
**Stato**: Accepted
**Risolve**: Q12

**Contesto**: per testare se il sentiment anticipa i prezzi serve un
allineamento news↔return privo di look-ahead. I feed danno in modo affidabile
solo il **publication time** (non l'event time). Una news pubblicata "durante"
il giorno D è in parte già nel prezzo di D: usarla per spiegare il return di D
introdurrebbe leakage intrabar.

**Decisione**:
1. Timestamp news = **publication time, UTC** (l'unico affidabile)
2. Aggregazione a **giorno di calendario UTC** (`normalize()`): `mean_sentiment`
   + `news_count` per giorno
3. **Lag di sicurezza** di default **1 giorno**: la feature delle news del giorno
   `D` viene etichettata `D+1` (`shift(freq="D")`) prima del join coi return. Il
   return spiegato sul giorno `t` usa solo news pubblicate fino a fine `t-1`
4. Coerente con ADR-007 (timeframe breve = daily) e con "UTC midnight = fine
   giornata" (anticipato in Q12)

**Conseguenze**:
- `lag_daily_features` / `align_sentiment_returns` in `src/ai/lexicon/`, con test
  esplicito anti-look-ahead
- Il lag è un parametro: studi lead/lag potranno esplorare lag>1, ma il default
  conservativo è 1 giorno
- L'allineamento macro a *release date* (CPI/M2) resta un punto distinto del
  backlog (Fase 2.1/4), non coperto qui

## ADR-025 — News history versionata: eccezione mirata ad ADR-009

**Data**: 2026-05-30
**Stato**: Accepted
**Risolve**: Q10 (frequenza ingestion = batch giornaliero)
**In tensione con**: ADR-009 (dati in `data/` gitignored)

**Contesto**: i feed news espongono solo le ultime ~settimane. Un test lead/lag
serio del sentiment richiede **mesi** di storia. I container (sessione e runner
CI) sono effimeri: senza persistenza durevole ogni fetch riparte da zero.
ADR-009 tiene i parquet fuori dalla repo (dimensione, licenze), ma quella
motivazione non si applica a *headline metadata*: titolo, URL, timestamp e
sentiment precalcolato sono piccoli (un anno di fetch giornalieri ≈ pochi MB) e
a basso rischio di licenza (no testo integrale dell'articolo).

**Decisione**: eccezione **stretta e motivata** ad ADR-009. Un **singolo parquet
compatto** versionato in `data/news_history/news.parquet`, alimentato da un job
schedulato:
- **Schema compatto**: `item_id, source, title, url, sentiment` (+ index
  `published` UTC). **Si scarta il `summary`** (dimensione + zona grigia licenza;
  il Layer 1 legge comunque solo il titolo, ADR-023)
- **Carve-out** nel `.gitignore`: `!data/news_history/` + `!data/news_history/*.parquet`
  (dopo la regola globale `*.parquet`)
- **GitHub Actions** `news-history.yml`: cron giornaliero (06:30 UTC, Q10),
  esegue `update_history`, committa il parquet con `[skip ci]`
- Dedup su `item_id` (riusa `append_news`): una storia vista in run successive è
  salvata una sola volta
- Permessi workflow: `contents: write`; concurrency-group per evitare commit
  sovrapposti

**Conseguenze**:
- ✅ La storia news cresce nel tempo nonostante i container effimeri
- ✅ Sblocca il test lead/lag su orizzonte significativo (Fase 3)
- ✅ Q10 chiusa (batch giornaliero), coerente con timeframe breve daily (ADR-006)
- ⚠️ È l'unico dato versionato in `data/`: l'eccezione è **limitata a news
  headline+sentiment**. Altri dataset restano gitignored (ADR-009 invariato)
- ⚠️ Se la history diventasse grossa (improbabile per headline), si rivaluterà
  uno storage esterno con nuova ADR
- 🔁 Revocabile: rimuovere carve-out + workflow ripristina ADR-009 puro

---

## ADR-026 — Ticker Yahoo per POL: da MATIC-USD a POL28321-USD

**Data**: 2026-06-05
**Stato**: Accepted
**Estende**: ADR-019 (mapping ticker POL)

**Contesto**: lo strumento di attribuzione eventi ha rivelato che POL non
restituiva più dati da Yahoo (`MATIC-USD: possibly delisted`). Indagando:
sia `POL-USD` che `MATIC-USD` ora tornano vuoti su Yahoo. Il vecchio dato
`MATIC-USD` si era **congelato** (~marzo 2026) restando bloccato a ~0.22 senza
aggiornarsi — un dato *stale* che mascherava il vero crollo di POL.

**Decisione**: usare `yahoo_symbol="POL28321-USD"`, l'unico ticker Yahoo che
restituisce il feed POL vivo. **Cross-validato 1:1**: Yahoo POL28321-USD =
0.0838 == CoinGecko `polygon-ecosystem-token` = 0.0838 (stesso giorno). È
effettivamente POL.

**Conseguenze**:
- ✅ POL di nuovo analizzabile (prezzo reale ~0.084, non lo stale 0.22)
- ✅ Cross-source confermato (Yahoo == CoinGecko)
- ⚠️ Lezione: un ticker che "funziona" ma è congelato è peggio di uno che
  fallisce — il fallimento è visibile, lo stale no. → **Implementato** il check
  di freschezza (`src/ingestion/freshness.py`, PR #22): i cron di raccolta
  segnalano `STALE FEED` se l'ultimo dato supera la soglia
- 🔁 La storia frammentata di POL (POL-USD → MATIC-USD → POL28321-USD) resta il
  caso d'uso principale del composer multi-source (ADR-021)

---

## ADR-027 — News azionarie: Google News per-settore nella stessa pipeline

**Data**: 2026-06-05
**Stato**: Accepted
**Estende**: ADR-017 (tassonomia fonti), ADR-023 (sentiment Layer 1)

**Contesto**: l'attribuzione eventi è stata estesa agli ETF settoriali equity
(Fase 8), ma lo storico news era **solo crypto** (`googlenews_<coin>` +
Cointelegraph/CoinDesk). Per un ETF azionario quegli articoli sono fuorvianti,
quindi l'attribuzione mostrava solo lo split market-wide/settore-specifico
(rif. S&P 500) senza catalizzatori. Serviva un canale news azionario, evitando
però dipendenze pesanti o un secondo sistema parallelo.

**Decisione**: riusare **identica** la pipeline crypto (Google News RSS → VADER
→ history versionata ADR-025), aggiungendo **una ricerca Google News curata per
ogni ETF settoriale/tematico** (`SECTOR_NEWS_QUERIES` in `feeds.py`), con nome
sorgente `googlenews_<symbol>` come per le crypto. Le query sono in dominio
azionario e **non** contengono il qualificatore "crypto". Il singolo cron news
giornaliero (`news-history.yml`) accumula così entrambi gli universi nello stesso
parquet. L'attribuzione sugli ETF aggancia queste news, mantenendo riferimento di
mercato S&P 500 e soglia "giornata grande" all'1% (vs ~3% crypto).

**Conseguenze**:
- ✅ Attribuzione eventi completa anche su equity: classificazione + catalizzatori
- ✅ Zero nuove dipendenze: stessa infra, stesso scorer VADER general-domain
- ✅ Sentiment simmetrico già esistente → cattura sia crolli sia balzi positivi
- ⚠️ Lo storico equity parte da zero (come le crypto a inizio Fase 3): per
  settimane molti movimenti ETF mostreranno "nessuna news nella finestra" finché
  la storia non si addensa. La classificazione market-wide/settore regge intanto
- ⚠️ VADER è general-domain: baseline onesta, non un modello finance-tuned; si
  sale di complessità (FinBERT, ADR-016) solo se un segnale misurato lo giustifica
- 🔗 La query per settore è curata a mano per alta pertinenza; nuovi ETF aggiunti
  a `SECTOR_ETFS` senza voce in `SECTOR_NEWS_QUERIES` usano un fallback dal nome

---

## ADR-028 — Attribuzione eventi v2: trigger doppio, severità, canale world-news

**Data**: 2026-07-02
**Stato**: Accepted
**Estende**: ADR-024/025/027 (pipeline news + attribuzione)

**Contesto**: la dashboard "Eventi" è rimasta senza nuove correlazioni per
giorni nonostante la pipeline fosse sana (news e cron regolari). Diagnosi su
dati reali: (1) il trigger **solo z-score** (|z| ≥ 2.5 su vol rolling 30gg) si
auto-acceca nei regimi ad alta volatilità — il *volatility clustering*
documentato in Fase 1 gonfia la baseline, così nel bear 2026 BTC richiedeva
±7%/giorno per fare evento e giornate da −4% risultavano "normali"; (2) tutte
le fonti news erano coin/settore-specific: la correlazione "borsa ↔ evento del
mondo" (Fed, geopolitica) **non poteva emergere per costruzione**, malgrado la
VISION la preveda.

**Decisione**:
1. **Trigger doppio**: un giorno è evento *major* se |z| ≥ 2.5 **oppure**
   |return| ≥ soglia assoluta per-universo (4% crypto, 2.5% ETF equity).
   La soglia assoluta è regime-robusta per definizione.
2. **Severità a livelli**: nuovo tier *notable* (1.5 ≤ |z| < 2.5), campo
   `severity` su ogni move — la dashboard degrada con grazia nei periodi calmi
   invece di andare in silenzio binario.
3. **Market pulse**: `events.json` espone per benchmark (BTC, SPX) il quadro
   di oggi (return, z, max|z| 10gg) e i giorni dall'ultimo evento major — il
   silenzio diventa "mercato calmo da N giorni", non "pipeline rotta".
4. **Canale world-news**: 3 fonti Google News (`googlenews_world/fed/macro`,
   query geopolitica/Fed/macro USA) nello stesso cron e parquet (ADR-025);
   nei movimenti classificati **market-wide** queste fonti sono pesate quanto
   la fonte asset-specific nell'attribuzione (su una giornata di mercato, un
   titolo Fed è plausibile almeno quanto uno di coin).

**Conseguenze**:
- ✅ Replay sui 30gg correnti: eventi per asset da 1-3 a 4-6; BTC recupera i
  giorni −4.0%/−4.5% di inizio giugno che la soglia z ignorava
- ✅ Il "nessun evento" ora è informazione esplicita (pulse), non ambiguità
- ✅ Il canale world abilita finalmente l'attribuzione mondo↔mercato; storico
  world parte da zero (stesso rodaggio di ADR-027 per l'equity)
- ⚠️ Le soglie assolute (4%/2.5%) sono giudizio a priori, non fittate; da
  rivedere se producono troppi/troppo pochi eventi (misurare, poi calibrare)
- ⚠️ Più eventi mostrati = più responsabilità del disclaimer: associazione,
  non causa (invariato da ADR-024)

---

## ADR-029 — Stato del paper trading versionato nel repo

**Data**: 2026-07-04
**Stato**: Accepted
**Estende**: ADR-010/011 (paper trading), ADR-025 (pattern history versionata)

**Contesto**: la Fase 6 richiede che il paper trading giri in **live-shadow
per mesi senza interventi manuali** (criterio di completamento). I job girano
su container effimeri (GitHub Actions): senza persistenza esterna, ogni run
ripartirebbe da zero e il track record — che È il deliverable della fase —
non esisterebbe.

**Decisione**: lo stato dei portafogli paper vive in **`data/paper/`,
committato** nel repo (eccezione mirata ad ADR-009, stesso razionale di
ADR-025): `scenarios.json` (registry), per scenario `state.json` (portfolio +
ultimo bar processato), `orders.parquet` (audit trail completo),
`equity.parquet` (curva, append idempotente per bar). I **reset** spostano i
file in `_archive/` — non si cancella mai nulla (ADR-011). File piccoli
(KB), nessun problema di licenza (è output nostro).

**Conseguenze**:
- ✅ Il track record sopravvive ai container e resta auditabile via git
  (ogni commit del cron è uno snapshot verificabile)
- ✅ Riproducibilità: chiunque cloni il repo vede l'intera storia degli ordini
- ⚠️ Un solo writer sequenziale (il cron): la concorrenza non è gestita, per
  scelta — se un giorno servisse, si passa a uno store esterno con lock
- 🔗 Prima applicazione: `src/execution/` (PaperBroker, ScenarioStore)

---

## ADR-030 — Piano di accumulo: la scelta sulla quota satellite è ribilanciamento, non previsione

**Data**: 2026-08-24
**Stato**: Accepted
**Estende**: ADR-005 (asset universe), ADR-007 (output del sistema)

**Contesto**: richiesta esplicita dell'utente — il piano reale è 100€/mese
(60 BTC, 30 ETH, 10 su **uno** tra SOL/LINK/POL) e serviva che il sistema
dicesse (a) quale dei tre conviene comprare e (b) quali altre crypto valutare
per un accumulo a 5-10 anni. La domanda "quale conviene" è, letteralmente, una
domanda predittiva — ed è esattamente quella a cui le Fasi 0-5 hanno risposto
**no**: nessun edge direzionale daily su questo universo.

**Decisione**: implementare la funzione, ma **cambiando la domanda** in una a
cui si può rispondere onestamente. La regola (`src/features/dca_advisor.py`) non
esprime alcuna vista direzionale: sceglie l'asset **più sotto peso rispetto al
target** dell'allocazione. È aritmetica di ribilanciamento, non una scommessa.

La regola è stata validata (`src/features/dca_backtest.py`) replicando i flussi
di cassa reali su 2020-04 → 2026-08 (77 acquisti mensili, commissioni 0.5%),
contro: divisione in parti uguali, rotazione, momentum, buy-the-dip, singolo
asset, e un controllo casuale a 200 semi. Risultati:

| | rendimento | allocazione |
|---|---|---|
| regola vs split (periodo) | 1.013 | drift 80 pp vs 102 pp |
| regola vs split (1ª metà) | 1.19 | — |
| regola vs split (2ª metà, OOS) | 0.91 | drift 5.3 pp vs 30.5 pp |
| percentile vs 200 estrazioni casuali | 54.5° | — |

Lettura: **sul rendimento la regola non ha alcun edge** — 54° percentile contro
il caso, e il rapporto con lo split si alterna fra le due metà, che è la firma
del rumore. **Sull'allocazione l'effetto è reale e regge OOS.** Quindi la regola
resta, ma il suo scopo dichiarato è la disciplina di allocazione.

Due sotto-decisioni derivate:
- **`DEFAULT_GAP_WEIGHT = 1.0`**: la componente "sconto" (comprare chi è più in
  basso nel proprio range) era al **96° percentile in-sample** e **ultima** nella
  metà out-of-sample — miraggio da campione. Non guida più il punteggio: rompe
  solo i pareggi esatti.
- **Il momentum è documentato come la scelta peggiore** (40.5° percentile, sotto
  il caso). È l'istinto più comune e va detto, non lasciato implicito.

Per le candidate a lungo termine (`src/features/dca_candidates.py`): filtri
**meccanici** (già in portafoglio, stablecoin/pegged, wrapped/derivati, soglia di
capitalizzazione, banda di liquidità su volume/market cap), nessun giudizio di
merito, e la **lista degli scarti con il motivo** restituita insieme alla
shortlist. L'età è derivata dalla data di minimo storico ed è deliberatamente
**a senso unico**: alza il punteggio, non esclude mai (un minimo recente non
significa moneta giovane — Zcash è del 2016 e il dato la darebbe a 2 anni).

**Conseguenze**:
- ✅ La richiesta è soddisfatta senza promettere previsioni: `REPORT_DCA.md`,
  `public/data/dca_report.json` e il tab "Piano di accumulo" della dashboard
- ✅ I numeri della validazione **viaggiano dentro l'output**: il tab non può
  mostrare la scelta senza mostrare che non produce rendimento extra
- ✅ Un esperimento fallito documentato (la componente sconto), come da CLAUDE.md
- ⚠️ 77 acquisti mensili sono **decine** di osservazioni, non migliaia: la
  conclusione "nessun edge" è solida, un'eventuale conclusione opposta non lo
  sarebbe stata
- ⚠️ **Survivorship bias non risolvibile** sulle candidate: la classifica di oggi
  contiene solo i sopravvissuti, e le monete morte non sono nei dati. La soglia
  di capitalizzazione è un indizio, non una garanzia
- ⚠️ Senza `holdings_units` in `config/dca_plan.yaml` la posizione è **stimata**
  replicando il piano; l'output lo dichiara invece di far finta di saperlo
- 🔗 Nessun trade reale, in nessun ambiente (vincolo CLAUDE.md invariato)

---

## ADR-031 — Le candidate si giudicano sui fondamenti del progetto, non sulle proprietà del ticker

**Data**: 2026-08-24
**Stato**: Accepted
**Corregge**: ADR-030 (sezione candidate)

**Contesto**: lo screen introdotto con ADR-030 ordinava le candidate su
capitalizzazione, liquidità ed età. Feedback dell'utente, immediato e corretto:
quelle sono proprietà **del ticker**, non del progetto che ci sta dietro. Con
quel punteggio Dogecoin usciva secondo — grande, liquido, undici anni di storia,
e sotto niente che leghi il prezzo a un'attività della rete. L'utente ha
precisato che DOGE era solo l'esempio: il punto è che i titoli scelti devono
avere **basi solide alle spalle**.

Nota su cosa NON era il bug: il punteggio non conteneva momentum (rimosso in
ADR-030 perché risultato peggiore del caso). DOGE non usciva perché saliva, ma
perché lo screen non aveva alcuna nozione di *cosa faccia* un progetto — il che
è peggio.

**Decisione**: separare le due responsabilità.

1. `dca_candidates` diventa un **puro pre-filtro**. Mantiene i filtri meccanici
   (già in portafoglio, stablecoin/pegged, wrapped, soglia di capitalizzazione,
   banda di liquidità) e **perde il punteggio**: i sopravvissuti escono ordinati
   per capitalizzazione e nient'altro, perché ordinare per dimensione è
   un'affermazione sulla dimensione e questo modulo non ne fa altre.
2. `src/features/fundamentals.py` fa il ranking su quattro assi: **cattura del
   valore**, **diluizione**, **sviluppo**, **track record**.
3. `src/assets/token_economics.py` è un registro **curato a mano** — con
   meccanismo, fonte e data di verifica — perché nessuna API gratuita risponde
   alla domanda "il valore prodotto arriva a chi tiene il token".

Tre regole che nascono da errori commessi mentre lo si costruiva:

- **Sconosciuto non è zero.** Ogni asse può essere ignoto, gli assi ignoti sono
  esclusi dalla media invece che imputati, e la riga porta una `confidence` pari
  al peso di ciò che si sapeva davvero. Un progetto non studiato non deve
  sembrare un progetto bocciato.
- **La tesi monetaria è esente dall'asse cattura, non penalizzata da esso.**
  Bitcoin non cattura ricavi di protocollo ed è l'asset di maggior successo della
  categoria; un punteggio che lo mettesse ultimo su "cattura del valore" sarebbe
  rotto in una direzione nuova, non riparato.
- **Zero commit recenti è una domanda, non un verdetto.** Monero e Aave
  riportano entrambi zero commit in quattro settimane e sono entrambi vivi: il
  dato a monte dipende da quale repository il provider ha mappato e invecchia.
  Un repo silenzioso con una lunga storia di contributori è etichettato
  *quiet_or_stale* e vale **ignoto**, mai "morto".

Una soglia `DEFAULT_MIN_CONFIDENCE = 0.5` nasce da un caso concreto: Bitcoin Cash
prendeva 1.0 sulla sola diluizione e finiva quinto, davanti a Solana. Il numero
era aritmeticamente giusto e privo di significato.

**Conseguenze**:
- ✅ Il report non è più una classifica ma una **scheda per progetto**, raggruppata
  per verdetto: cosa fa, chi cattura il valore, quanta offerta deve arrivare, chi
  lo sviluppa. Il motivo viaggia col nome
- ✅ I progetti **scartati sui fondamentali** restano sempre visibili anche se
  fuori dal top-N: vedere dov'è l'asticella vale quanto vedere chi la supera
- ⚠️ **Manca il dato più importante: i ricavi di protocollo.** `api.llama.fi`,
  Token Terminal e Dune sono **bloccati dalla policy di rete** dell'ambiente
  (403 al CONNECT). Senza, si misura *se* un meccanismo di cattura esiste, non
  *quanto* valga — un burn enorme e uno simbolico oggi prendono lo stesso
  punteggio, ed è il motivo per cui NEAR compare a pari merito con Ethereum.
  Sbloccando `api.llama.fi` si aggiungono fees, revenue, TVL e il rapporto P/F
- ⚠️ **Niente backtest, e non è colpa della fretta**: la storia di fee e
  valutazioni dei protocolli è lunga pochi anni ed è piena di sopravvissuti.
  A differenza della regola sulla quota satellite (ADR-030), qui **non si può
  dire che questi assi battano il caso**. Descrivono, non predicono
- ⚠️ Il registro curato copre i nomi principali e **invecchia**: `verified_on`
  dice quando un umano ha controllato l'ultima volta
- 🔗 Il client DefiLlama **non è stato scritto**: codice HTTP contro un host
  irraggiungibile non è verificabile, e si romperebbe nel cron. Si scrive quando
  l'host è raggiungibile

---

## ADR-032 — Direzione di prodotto: market intelligence probabilistica (ranking ETF)

**Data**: 2026-08-24
**Stato**: Accepted
**Contesto operativo**: `docs/PIANO_SVILUPPO.md` (commissionato dall'utente lo
stesso giorno). Questa ADR registra la direzione; il piano ne è l'esecuzione.

**Contesto**: le Fasi 0–5 hanno prodotto un risultato netto e negativo: **non
c'è edge direzionale daily** né dal tecnico, né dal tecnico+macro, né dal
sentiment Layer 1, né dal momentum cross-sectional sui settori (i numeri sono in
`STATUS.md`, sezione "Risultati empirici consolidati"). Quello che invece ha
mostrato struttura è il **condizionamento**: il rendimento cambia natura per
regime e per fase di ciclo, al punto che la media full-sample è un artefatto.

Il repo si è quindi allargato in ampiezza — screener di rotazione, attribuzione
eventi, report auto-aggiornati, piano di accumulo, paper trading — senza che
esistesse **un prodotto predittivo dichiarato** su cui misurarsi. Ampiezza senza
un bersaglio è il modo più comodo per non scoprire mai di non avere segnale.

Serviva scegliere un bersaglio che fosse: (a) **cross-sectional** invece che
direzionale, perché "quale sale di più" è una domanda più facile e più utile di
"il mercato sale?"; (b) **probabilistico e calibrato**, perché una probabilità
si può falsificare mentre un "compra ora" no; (c) su un universo con **storia
lunga e pulita** (ETF settoriali dal 2012, contro ~1,5 cicli di halving crypto).

**Decisione**: il primo prodotto predittivo del progetto è un **ranking
cross-sectional di ETF settoriali con probabilità calibrate di sovraperformare
il benchmark**. Non "quanto salirà il mercato", ma "dato lo stato di oggi, con
che probabilità questo settore batte SPY nelle prossime 20 sedute, e quanto è
incerta quella stima".

Vincoli che fanno parte della decisione, non contorno:

1. **La probabilità è il prodotto**, non un accessorio del segnale. Deve essere
   calibrata (isotonic su train) e misurata con **Brier score** contro la
   baseline climatologica, non con l'accuracy.
2. **Ipotesi pre-registrate** (H1–H3 del piano §2.1, copiate verbatim
   nell'ADR-034 prima del primo backtest) e **barra di adozione fissata prima**:
   IC di Spearman medio OOS ≥ 0,03 **e** spread top−bottom quintile positivo al
   netto dei costi in **entrambe** le metà dell'OOS **e** Brier ≤ climatologica.
   Sotto la barra, il paper portfolio parte comunque ma con **momentum semplice
   dichiarato non-predittivo**: vale l'infrastruttura, non si finge l'edge.
3. **Validazione con embargo/purging** nel walk-forward: `walk_forward_splits`
   oggi non ce l'ha, e senza embargo un target a 20 sedute sporca il fold di test.
4. **Nessun "compra ora"** in output, in nessuna vista (rif. ADR-002, ADR-016):
   probabilità, incertezza e fattori che la spiegano.
5. **Un LLM non produce mai un numero di segnale** (rif. ADR-016): al più
   estrae e classifica eventi, con audit di fonte/timestamp/hash/versione prompt.

**Decisioni operative allegate** (default adottati dal piano §2; l'utente può
emendarli finché il WP che li usa non è partito, dopo cambiarli significa rifare
il WP):

| # | Decisione | Default | Usata da |
|---|---|---|---|
| D1 | Universo | i 20 ETF di `SECTOR_ETFS` | WP2 |
| D2 | Benchmark | **SPY** (nuovo `Asset`, ETF, yahoo `SPY`) | WP2 |
| D3 | Orizzonte | **20 sedute** primario, 60 secondario | WP2–3 |
| D4 | Target primario | `P(excess_return > 0)` a 20 sedute | WP3 |
| D5 | Frequenza decisione | settimanale, lunedì pre-apertura | WP4 |
| D6 | Portafoglio paper | top 5 equal-weight, cap 20%/asset, fill t+1, `default_cost_model()` | WP4 |
| D7 | Soglia di confidenza | nessun acquisto se `P(outperform) < 0,55` per il 5° classificato | WP4 |

D4, D7 e D8 (storage, ADR-033) restano **soggette a conferma esplicita
dell'utente**; le altre valgono come default operativi. D9 (provider LLM) non è
decisa e tiene WP6 bloccato.

**Ipotesi pre-registrate** (piano §2.1, riportate qui perché il vincolo di
`CLAUDE.md` è che le ipotesi si scrivano **prima** dei risultati):

- **H1**: il ranking per momentum relativo 60g ha IC di Spearman medio OOS > 0 a
  20 sedute sull'universo D1.
- **H2**: la logistica regolarizzata sulle feature di WP2 batte il momentum puro
  in Brier score OOS.
- **H3**: lo spread top-quintile − bottom-quintile, **al netto dei costi**, è
  positivo in *entrambe* le metà temporali dell'OOS.

Nota di coerenza: H1 riguarda il momentum **relativo a 60g su orizzonte 20
sedute**, mentre il finding già acquisito ("il momentum non dà edge") è misurato
per **bucket a 63 sedute**. Non è la stessa misura, quindi H1 non è già decisa —
ma l'evidenza esistente rende un esito negativo il più probabile, ed è scritto
qui prima di guardare i risultati.

**Contesto misurato — crescita del repository** (rilevato in WP0; è il contesto
che l'**ADR-033** deve citare):

| Path | Blob distinti | MiB cumulati | % |
|---|---:|---:|---:|
| `data/news_history/news.parquet` | 479 | 7 532,7 | **97,5%** |
| `public/data/events.json` | 473 | 131,5 | 1,7% |
| `data/category_history/categories_history.parquet` | 86 | 24,7 | 0,3% |
| `public/data/market_series.json` | 81 | 16,5 | 0,2% |
| `STATUS.md` | 71 | 2,9 | 0,04% |

Totale: 2 927 blob, **7 727 MiB** non compressi, pack di **1,17 GiB**, su 812
commit di cui **676 (83%) automatici**. Un solo file riscritto integralmente a
ogni run del cron spiega il 97,5% del peso.

**Conseguenze**:
- ✅ Il progetto ha finalmente **una previsione falsificabile** e una barra
  scritta prima: da qui in poi si può dire "ha funzionato" o "non ha funzionato"
  senza spostare i pali (precedente da non ripetere: nb 12 / FinBERT).
- ✅ L'equity ETF diventa il terreno primario di ricerca: storia lunga, universo
  stabile, benchmark ovvio. Il crypto resta coperto da screener, DCA e cicli.
- ⚠️ **Non è una promessa di rendimento.** L'esito più probabile, viste le Fasi
  0–5, è che le baseline non superino la barra: in quel caso vince
  l'infrastruttura (ledger, calibrazione, paper portfolio) e l'esito negativo
  viene pubblicato come gli altri.
- ⚠️ La calibrazione impone rigore in più: split con embargo, isotonic **fittata
  solo sul train**, niente riuso del test per scegliere le soglie.
- 🔒 Numeri ADR **riservati**: 033 (storage, WP1), 034 (esito baseline e
  ipotesi verbatim, WP3), 035 (event intelligence, WP6, gated su D9).
- 🚫 Fuori scope: rename della repository (D10), storage esterno dei dati (rinviato
  in ADR-033), nuove dipendenze per WP0–WP5 (D11: logistica, ridge e isotonic
  sono già in scikit-learn).
- 📌 Le serie FRED **non** entrano nel condizionamento in questa fase (D12): il
  regime è calcolato dai soli prezzi, già causale. Quando entreranno, sarà con
  regola di ritardo di pubblicazione ≥ 45 giorni, mai col valore revisionato alla
  data di riferimento.

---

## ADR-033 — Storage storico: partizionamento mensile dei parquet in-repo

**Data**: 2026-08-24
**Stato**: Accepted (D8 confermata dall'utente il 2026-08-24)
**Contesto operativo**: `docs/PIANO_SVILUPPO.md` §5, WP1. Decisione pre-registrata
**D8**, che il piano lasciava all'utente: confermata prima dell'implementazione.

**Contesto**: la misura di WP0 non lascia margini di interpretazione. Su 812
commit di `main`, **676 (83%) sono commit automatici dei cron**; il pack git pesa
**1,17 GiB** e il contenuto non compresso dei blob **7 727 MiB** su 2 927 blob.
Un solo file spiega quasi tutto:

| Path | Blob distinti | MiB cumulati | % del totale |
|---|---:|---:|---:|
| `data/news_history/news.parquet` | 479 | 7 532,7 | **97,5%** |
| `public/data/events.json` | 473 | 131,5 | 1,7% |
| `data/category_history/categories_history.parquet` | 86 | 24,7 | 0,3% |
| `public/data/market_series.json` | 81 | 16,5 | 0,2% |
| `STATUS.md` | 71 | 2,9 | 0,04% |
| tutto il resto | — | ~19 | 0,2% |

La causa non è il volume dei dati — la storia news compatta è **26,6 MB, 50 129
righe** — ma la **forma della scrittura**. Un parquet si riscrive per intero a
ogni append: il cron gira ogni 3 ore (8 volte al giorno) e ogni run deposita in
git un blob nuovo, quasi identico al precedente e **grande quanto tutta la
storia**. Il costo per run non è costante: **cresce con la storia stessa**. È una
crescita quadratica nel tempo, e a fine 2026 il repo sarebbe stato ingestibile
per una ragione puramente meccanica, non per la quantità di informazione.

Il vincolo di partenza (ADR-025) resta valido e non è in discussione: la storia
news **deve** essere versionata, perché i feed espongono solo poche settimane e
i container di Actions sono effimeri. Il problema è *come* la si scrive.

**Decisione**: la storia news è **partizionata per mese di pubblicazione** —
`data/news_history/news_YYYY-MM.parquet` — e resta **dentro il repo**.

1. **Scrittura**: `update_history()` raggruppa gli item entranti per mese e
   riscrive **solo le partizioni toccate**, normalmente il mese corrente. I mesi
   passati diventano blob immutabili che git non ristora mai più.
2. **Lettura trasparente**: `read_news_history()` concatena le partizioni e
   restituisce **un solo frame**, con la stessa forma di prima. I consumatori
   (`build_events`, `attribution_cli`, gli script dei notebook) non conoscono il
   layout: l'API è invariata.
3. **Dedup su due livelli**, e la distinzione è sostanziale: `append_news`
   deduplica *dentro* la partizione in scrittura, `read_news_history` deduplica
   *fra* partizioni in lettura. Il secondo copre il caso raro in cui un feed
   ripubblica una storia con data diversa: la copia vecchia resta nel suo mese
   (riscriverlo vanificherebbe tutto) e la lettura tiene la riga del mese più
   recente.
4. **Migrazione one-shot**: il monolite è stato diviso in 92 partizioni. La
   storia git **non viene riscritta**: i vecchi blob restano dove sono, questa è
   una decisione sul futuro, non una pulizia del passato. La migrazione è
   idempotente ed è invocata anche da `update_history.py` all'avvio, così un
   worktree anteriore alla migrazione si converte da solo invece di riscrivere
   silenziosamente il file da 26 MB.
5. **Il monolite resta leggibile**: `read_news_history` include `news.parquet` se
   ancora presente, ordinandolo prima delle partizioni. Un checkout precedente al
   commit di migrazione non perde storia.

**Effetto misurato** (26,6 MB il monolite, 6,14 MB la partizione di 2026-08 al
24 agosto):

| Metrica | Prima | Dopo | Δ |
|---|---:|---:|---:|
| Blob riscritto per run, oggi | 26,66 MB | 6,14 MB | **−77,0%** |
| Blob per run, media sui prossimi 30 giorni | ~31,4 MB | ~4,0 MB | **−87,2%** |
| Costo per run fra 12 mesi (proiezione a ~8 MB/mese) | ~119 MB | ~4 MB | **−96,6%** |

Il numero che conta non è la percentuale di oggi ma la **forma della curva**: il
costo per run del monolite cresce senza limite, quello della partizione è
**limitato a un mese di news (~8 MB) e si azzera ogni primo del mese**. Da
crescita quadratica a crescita lineare.

**Alternative valutate e rinviate** (dall'handoff §4.1). Nessuna è stata scartata
perché sbagliata: sono state scartate perché il partizionamento basta, e
introdurle ora significherebbe pagarne il costo prima di averne bisogno.

- **Cloudflare R2 / object storage esterno**: risolve il problema alla radice e
  si integra con il worker già in uso. Costo: credenziali da gestire nei cron, un
  layer di fetch da scrivere e testare, e i dati escono dal repo — cioè si perde
  la proprietà che li rende oggi riproducibili da un semplice `git clone`.
  **Rinviata**: da riconsiderare se la storia supera i ~500 MB o se serviranno i
  corpi degli articoli.
- **Git LFS**: sposta i blob fuori dal pack ma introduce una quota, un passo di
  setup per ogni clone e un fallimento silenzioso (file-puntatore) per chi non ha
  LFS. **Rinviata**: il rapporto beneficio/attrito è sfavorevole per file da
  pochi MB.
- **Release artifact / GitHub Releases**: gratuito e fuori dal pack, ma perde il
  versionamento fine (un artifact per release, non per run) e richiede comunque
  un layer di download. **Rinviata**.
- **Database esterno (DuckDB remoto, Postgres)**: la soluzione "giusta" per un
  sistema in produzione; qui aggiungerebbe un servizio da mantenere a un progetto
  di ricerca che gira su cron gratuiti. **Rinviata** esplicitamente a quando
  esisterà un prodotto con utenti, non prima.
- **Riscrittura della storia git** (`filter-repo`): recupererebbe l'1,17 GiB già
  speso. **Esclusa**, non rinviata: invalida ogni clone e ogni riferimento a
  commit esistente, per un beneficio una tantum su un repo che comunque non
  ricrescerà più a quel ritmo.

**Conseguenze**:
- ✅ La crescita del repo passa da quadratica a lineare, senza storage esterno,
  senza credenziali nuove, senza riscrivere la storia e senza toccare la raccolta
  dati. `git clone` resta sufficiente a riprodurre tutto.
- ✅ L'API per i consumatori è invariata: chi legge la storia chiama una funzione
  e riceve un frame, come prima.
- ⚠️ Il numero di file cresce: 92 partizioni oggi, +1 al mese. 89 di esse sono
  mesi antichi con 1–30 righe (Google News restituisce ogni tanto un articolo
  vecchio) e pesano ~1,2 MB in totale. Rumore in `ls`, irrilevante per git.
- ⚠️ `read_news_history()` legge N file invece di 1. A 92 partizioni il costo è
  trascurabile; se un giorno diventasse un problema, il passo successivo è un
  dataset parquet partizionato (pyarrow `dataset`) sulla stessa struttura di
  file, non un cambio di formato.
- ⚠️ **Il commit del cron non può selezionare "il mese corrente" per data**: un
  run del giorno 1 deposita ancora item nel mese precedente, e un feed può
  esporre un articolo vecchio. Il workflow committa quindi le partizioni
  **effettivamente modificate**, e verifica anche i file *untracked* — senza quel
  controllo, la partizione nuova del primo del mese sarebbe invisibile a
  `git diff` e non verrebbe mai committata.
- 🚫 **`category_history` non è stato partizionato** (perimetro WP1: "stesso
  pattern *se banale*, altrimenti annotare e fermarsi"). Non è banale: quel file
  è scritto dal `write_snapshot` generico di ADR-022, condiviso con macro,
  settori, CoinGecko ed Etherscan; partizionarlo significa cambiare l'API comune
  e i suoi sei call site. Costo alto, beneficio 0,3% del peso. Se un giorno la
  dinamica si ripete su quel file, si applica lo stesso schema a `write_snapshot`
  con una ADR dedicata.
- 📌 Leva non usata e disponibile: le partizioni usano la compressione di default
  (snappy). Passare a zstd ridurrebbe ancora il blob per run, ma tocca
  `append_news`, condiviso — vale una decisione a sé, non un effetto collaterale
  di questa.

---

## ADR-034 — Ranking ETF: esito della validazione pre-registrata

**Data**: 2026-08-24
**Stato**: Accepted — **esito misurato e registrato** (barra di adozione NON superata)
**Contesto operativo**: `docs/PIANO_SVILUPPO.md` §2.1 e §5 (WP3). Le ipotesi qui
sotto sono state committate in `6b3ffd3`, **prima** che esistesse il codice che
le misura (`5423c88`, `4fdd673`) e prima di qualunque risultato: il timestamp git
è la prova della pre-registrazione. L'esito è stato aggiunto dopo, senza toccare
una sola soglia.

**Contesto**: il progetto ha già pagato il prezzo di concludere dopo aver visto i
dati. Il caso `news_count`/`|return|` (correlazione +0,32 su n=23, svanita a
−0,07 con n=143) e il notebook 12 su FinBERT sono in `STATUS.md` proprio come
promemoria: una soglia scelta *dopo* aver guardato i risultati non è una soglia,
è una descrizione. `CLAUDE.md` lo mette tra i punti non negoziabili — «le ipotesi
vanno scritte **prima** di vedere i risultati, non dopo».

WP2 ha consegnato il panel (93 517 righe × 27 colonne, 20 ETF settoriali + SPY,
2005→2026) e con esso la **baseline climatologica**: l'outperformance
incondizionata vs SPY è 0,489 a 20 sedute e 0,482 a 60. È il numero da battere,
ed è noto prima di aver addestrato qualsiasi cosa.

**Decisione**: si adottano come **pali fissi** le ipotesi e le soglie qui sotto,
copiate **verbatim** da `docs/PIANO_SVILUPPO.md` §2.1. Non si spostano dopo aver
visto i risultati. Se una variante viene provata e fallisce, viene elencata nel
report anche se fallita.

### Ipotesi pre-registrate (verbatim da §2.1)

- **H1**: il ranking per momentum relativo 60gg ha IC di Spearman medio OOS > 0
  a 20 sedute sull'universo D1.
- **H2**: la logistica regolarizzata sulle feature di WP2 batte il momentum puro
  in Brier score OOS (probabilità calibrate su train con isotonic).
- **H3**: lo spread top-quintile − bottom-quintile, **al netto dei costi** D6, è
  positivo in *entrambe* le metà temporali dell'OOS.
- **Metrica primaria**: Brier score vs baseline climatologica (frequenza storica
  di outperformance nel train) + IC Spearman. Le altre metriche (§WP3) sono
  diagnostiche.
- **Barra di adozione** (il modello entra nel paper portfolio di WP4 solo se):
  IC Spearman medio OOS ≥ 0.03 **e** H3 vera **e** Brier ≤ baseline
  climatologica. Altrimenti WP4 procede con il **momentum semplice** come regola
  dichiaratamente non-predittiva (il ledger e l'infrastruttura valgono comunque)
  e l'esito negativo viene documentato in STATUS/ADR come da convenzione.

### Protocollo di validazione, fissato ora

Anche il *come* si misura va congelato prima, altrimenti la scelta del protocollo
diventa essa stessa un grado di libertà da sfruttare a posteriori:

1. **Walk-forward con embargo**: il test di ogni fold inizia `embargo = horizon`
   osservazioni dopo la fine del train. Senza embargo l'ultima riga di train ha
   un target che si realizza *dentro* il test: contaminazione, non predizione.
2. **Campionamento settimanale** del panel (lunedì), coerente con D5.
3. **Calibrazione isotonic fit solo sul train** del fold, mai sul test.
4. **Due metà temporali OOS** valutate separatamente: H3 richiede che il segno
   tenga in *entrambe*, non in media.
5. **Controlli negativi obbligatori**: `RandomRanker` con seed e
   `ClimatologyBaseline`. Se un modello non batte il caso, il confronto con le
   altre baseline non significa nulla.

### Esito misurato (run del 2026-08-24, `docs/REPORT_RANKING.md`)

Panel WP2, 93 517 righe, campionamento settimanale (1 020 lunedì), walk-forward
train 156 / test 52 settimane con embargo pari all'orizzonte. 14 950 previsioni
OOS per modello e orizzonte.

| Modello | IC Spearman (20g) | t | Brier | ECE | TMB netto |
|---|---:|---:|---:|---:|---:|
| `momentum` (H1) | 0,0010 | 0,08 | 0,2510 | 0,025 | −0,0052 |
| `logistic` (H2) | 0,0299 | 2,50 | 0,2638 | 0,077 | +0,0008 |
| `ridge` | 0,0308 | 2,56 | 0,2558 | 0,051 | +0,0014 |
| `random` (controllo) | 0,0022 | 0,26 | 0,2506 | 0,016 | −0,0024 |
| `climatology` (controllo) | — | — | **0,2501** | 0,009 | −0,0033 |

- **H1 — vera *come scritta*, ma il numero è rumore.** IC del momentum = 0,0010
  con t = 0,08: letteralmente > 0, statisticamente indistinguibile da zero, e
  **inferiore a quello del ranker casuale** (0,0022). L'ipotesi chiedeva solo
  `IC > 0` senza magnitudine, quindi passa; la soglia non è stata spostata a
  posteriori. Si registra invece la lezione: *un'ipotesi senza magnitudine è
  quasi gratis da superare*, e in una futura pre-registrazione va evitata.
- **H2 — falsa.** La logistica ha Brier 0,2638 contro 0,2510 del momentum: non lo
  batte, lo peggiora. A 60 sedute il divario si allarga (0,2794 vs 0,2527).
- **H3 — falsa.** Lo spread top−bottom al netto dei costi è positivo nella prima
  metà OOS (+0,0051 per `ridge`) e **negativo nella seconda** (−0,0022). A 60
  sedute l'IC stesso cambia segno tra le due metà (+0,057 → −0,047).
- **Barra di adozione: NON superata.** Richiedeva IC ≥ 0,03 **e** H3 **e** Brier
  ≤ climatologia: la prima condizione è soddisfatta (`ridge` 0,0308), le altre
  due no.

### Cosa dice davvero questo risultato

Non è un "niente". I due modelli lineari mostrano un IC intorno a **0,03 con
t ≈ 2,5**: un accenno di capacità di ordinamento cross-sectional, l'unica cosa in
tutto il run che non somigli al caso. Ma non sopravvive a nessuno dei tre
controlli che contano:

1. **Non regge nel tempo.** Positivo nella prima metà OOS, svanito o invertito
   nella seconda. Un segno che tiene in una sola metà è un regime, non un edge.
2. **Le probabilità sono peggio di una costante.** Tutti i modelli hanno Brier
   *superiore* alla climatologia (0,2501). La reliability table è il dato più
   netto del run: nella banda 0,90–1,00 la logistica predice 0,974 e si realizza
   **0,461**. Il modello è spettacolarmente troppo sicuro proprio dove pretende
   di saperne di più. La calibrazione isotonic, fit sul train, non trasferisce
   OOS — perché la relazione che apprende non è stabile.
3. **I costi mangiano quel che resta.** Il TMB lordo di `ridge` è +0,0038, il
   netto +0,0014: il 63% dell'edge lordo è commissioni e slippage, e comunque non
   regge in entrambe le metà.

Il **momentum relativo è indistinguibile dal caso** (0,0010 vs 0,0022): conferma
diretta, ora su base probabilistica e con costi, del risultato già in `STATUS.md`
— inseguire i settori forti non paga.

**Conseguenze**:

- **WP4 procede con il momentum semplice**, dichiaratamente *non predittivo*,
  esattamente come §2.1 prescriveva per questo caso. Il prediction ledger e
  l'infrastruttura di portafoglio restano pienamente giustificati: servono a
  **misurare** onestamente, non a guadagnare.
- Nessun modello entra in produzione con probabilità presentate come affidabili.
  Dato ADR-032 (il prodotto è *probabilità calibrate*), pubblicare questi numeri
  come tali sarebbe la cosa peggiore che il sistema possa fare.
- L'IC ≈ 0,03 di `ridge`/`logistic` resta un filo da tirare **solo** con un
  protocollo che ne accerti la stabilità (più fold, orizzonti diversi, feature
  ablation). Non è un mandato per aggiungere modelli più potenti: un learner più
  forte sulle stesse feature renderebbe solo più facile nascondere l'overfitting
  (D11 resta in vigore).
- Metodologico, da riportare nella prossima pre-registrazione: **ogni ipotesi
  deve avere una magnitudine**, non solo un segno.

<!--
Template per nuove ADR:

## ADR-NNN — Titolo breve
**Data**: YYYY-MM-DD
**Stato**: Accepted
**Risolve**: (riferimento a OPEN_QUESTIONS se applicabile)
**Contesto**:
**Decisione**:
**Conseguenze**:
-->
