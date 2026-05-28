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
