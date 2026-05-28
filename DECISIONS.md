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
