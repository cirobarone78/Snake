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

## Fase 1 — Esplorazione dati ✅ *completata (2026-05-29)*

**Obiettivo**: capire quali dati sono accessibili (gratis o low-cost), in che
forma, con quale qualità.

### Deliverable
- [x] **Inventario di sorgenti dati** (`docs/data_sources_tier1.md` +
      integrazioni concrete): Yahoo Finance, Binance.us (ADR-020),
      CoinGecko, FRED, Etherscan — ciascuna con API, frequenza,
      storico, rate limit, caveat documentati
- [x] **Setup ambiente Python**: `uv` + Python 3.12, `pyproject.toml` con
      ruff + pyright basic + pytest (ADR-009 confermato)
- [x] **Script di ingestion** estesi oltre il deliverable minimo:
  - Tutti i 5 Tier 1 crypto (BTC/ETH/SOL/LINK/POL) + context assets
    (DXY/SPX/NDX/GOLD) via Yahoo
  - Tutti i Tier 1 anche via Binance.us (cross-validation)
  - Market chart + global dominance + top-20 dinamica via CoinGecko
  - 7 serie macro USA (DFF, DGS2, DGS10, DTWEXBGS, CPIAUCSL, M2SL,
    UNRATE) via FRED
  - On-chain snapshot per ETH (supply, components staking/burnt/withdrawn,
    gas oracle, prezzo Etherscan) e ERC-20 supply (LINK, POL) via
    Etherscan
  - Composer multi-source (ADR-021) per asset con copertura provider
    mista (caso POL chiuso)
  - Snapshot persistence con _latest + _history append (ADR-022) per
    accumulare time series da snapshot ripetuti
- [x] **Notebook di esplorazione** (3 notebook eseguiti, findings
      documentati in `STATUS.md`):
  - `01_exploration_btc_eth.ipynb`: stylized facts crypto su tutti i 5
    Tier 1 (vol annualizzata 65-136%, fat tails, volatility clustering),
    correlazioni cross-asset
  - `02_crypto_vs_macro.ipynb`: crypto vs equity indices + DXY + GOLD
    su 974 giorni comuni — crypto risk-on, non digital gold
  - `03_crypto_vs_fred_macro.ipynb`: crypto vs tassi + curve slope +
    CPI/M2/UNRATE — BTC vs CPI YoY mensile −0.40 (smonta narrativa
    "inflation hedge"); yield curve invertita per 536 giorni
    consecutivi 2022-07 → 2024-08
- [x] **Strategia di storage definita**: pipeline a 3 layer
  - `data/raw/{provider}/{class}/{SYMBOL}_{interval}.parquet`
  - `data/processed/{SYMBOL}_{interval}.parquet` con colonna `source`
    per provenance (ADR-021)
  - Snapshot: `_latest.parquet` (overwrite) + `_history.parquet`
    (append) in parallelo (ADR-022)
  - Tutto gitignored, retention policy locale
- [x] **Test coverage**: 67/67 pytest verde, copertura simmetrica sui 5
      provider (Yahoo, Binance, CoinGecko, FRED, Etherscan) + composer
      + snapshot helper + assets

### Criterio di completamento
✅ Sappiamo esattamente quali sorgenti dati useremo, in che formato,
con quali limiti. ADR-019 ÷ ADR-022 registrano le decisioni chiave
emerse durante la fase (POL via MATIC-USD, Binance via .us, composer
policy, snapshot history). Open question rimaste (Q23 volume
cross-venue, Q18 granularità educational) non bloccano l'avanzamento
alla Fase 2.

### Cosa NON è stato fatto (e perché)
- **Blockchain.com (BTC on-chain)**: rimasto come stretch goal.
  Etherscan copre ETH/LINK/POL ma non BTC che vive su una chain
  diversa. Da fare a richiesta se in Fase 4 servirà
- **Granularità intra-day via Binance**: l'interfaccia c'è già
  (`BinanceSource` supporta tutti gli interval), ma `fetch_tier1.py`
  estrae solo daily. Si attiverà se in Fase 2 si decide di lavorare
  anche a 1h
- **Schedulazione automatica fetch snapshot** (cron / GitHub Actions
  per popolare history nel tempo): pattern pronto via ADR-022, ma
  la schedulazione effettiva è decisione operativa rimandata
- **Stagionalità e ciclo halving**: analisi pianificate ma non
  prioritarie per il completamento di Fase 1. Pre-tabellate come
  esperimenti specifici per Fase 2 (regime detection)

---

## Fase 2 — Baseline tecnica & backtesting rigoroso ✅ *completata (2026-05-30)*

**Obiettivo**: costruire l'infrastruttura di valutazione **prima** dei modelli
complessi. Senza questa, qualsiasi risultato successivo è inattendibile.

### Hook empirici dalla Fase 1
La Fase 1 ha prodotto tre osservazioni che vincolano la Fase 2:
- **Volatility clustering forte** (ACF(|r|) lag 1 = 0.16-0.27) → famiglia
  GARCH/HAR è candidata naturale come baseline di varianza condizionata
- **Correlazioni rolling instabili** (std 0.12-0.17) → regimi esistono,
  il modello baseline deve essere valutato anche **regime-aware** non
  solo full-sample
- **BTC vs CPI YoY = −0.40** (e dollar headwind robusto) → almeno una
  feature macro va affiancata al solo prezzo per testare se aggiunge
  potere predittivo

### Deliverable
- [x] Indicatori tecnici classici implementati (`src/features/indicators.py`):
      SMA, EMA, MACD, RSI (Wilder), Bollinger Bands, ATR (Wilder), OBV.
      Funzioni pure su OHLCV, causali per costruzione (test di non-look-ahead),
      asset-class-agnostic (finestre in osservazioni, ADR-014)
- [~] Framework di **backtesting walk-forward** (engine custom) con:
  - [x] Niente look-ahead bias: walk-forward splitter rolling/expanding
    (`src/backtest/splits.py`), invariante "test dopo train" forzata alla
    costruzione di `Split` e verificata nei test. Per macro FRED → uso di
    *release date* non *reference date* ancora da fare
  - [x] Costi di transazione inclusi (`src/backtest/costs.py`): fee
    per-broker (Binance/Kraken, ADR-012) + slippage ADR-013
    (max(half_spread, floor) × size_adj) + proxy di spread da range OHLC.
    Capitolo educational L1.04 come prerequisito mentale
  - [ ] Survivorship bias mitigato (se possibile)
  - [x] **CI riproducibile** (`.github/workflows/ci.yml`): ruff + pytest
    bloccanti, pyright bloccante sui moduli core (backtest/features/models)
    e informativo sul resto. Verde su ogni push/PR (VISION principio #2)
  - [x] Out-of-sample mandatory: notebook `04_baseline_backtest.ipynb`
    esegue end-to-end indicatori/forecast → walk-forward expanding (solo
    test windows) → costi → confronto vs buy-and-hold/DCA su BTC/ETH/LINK
    reali (2019-2026). Ipotesi scritte prima dei risultati, bias
    documentati
- [~] Modello **baseline**: random walk + momentum semplice + ARIMA
  - [x] Random walk (martingala, forecast = 0) e momentum (media mobile
    trailing dei rendimenti) in `src/models/baseline.py`, causali per
    costruzione (test di non-look-ahead), + mapping forecast→posizione
    (long-only di default per spot ADR-012), strategy returns al netto
    dei costi (turnover × cost model), e metriche di forecast
    (directional accuracy, MAE)
  - [ ] ARIMA: rimandato finché non si aggiunge `statsmodels` allo stack
    installato (è in ADR-009 ma non ancora in `pyproject.toml`)
- [x] **Suite di metriche** (`src/backtest/metrics.py`): Sharpe, Sortino,
      max drawdown (+ durata), Calmar, hit rate, profit factor, time
      underwater, total/annualized return & vol, `summarize()` aggregato.
      Annualizzazione parametrica (asset-class-agnostic, ADR-014)
- [x] Confronto baseline vs buy-and-hold eseguito (notebook 04): momentum
      net long-only batte buy-and-hold in Sharpe/drawdown su BTC ed ETH ma
      **non** su LINK (2 su 3 → non è un segnale affidabile); il valore è
      difensivo (stare flat nei crash), non direzionale (dir-acc ~50%)
- [x] **Regime detection** (anticipata da Fase 5: i regimi erano troppo
      importanti per essere ignorati al livello di baseline). Classificatore
      causale bull/bear price-vs-SMA200 (`src/features/regime.py`) +
      decomposizione metriche per regime. Risultato chiave: l'edge del
      momentum è **difensivo** (riduce drawdown nei bear su BTC/ETH) non
      direzionale, e **non robusto** cross-asset (controproducente su LINK
      per whipsaw). Un HMM/regime-switching resta candidato Fase 5

### Esito (completata 2026-05-30)
Consegnati: **harness di valutazione** (`src/backtest/`, engine custom per
controllo totale su no-look-ahead) — metriche, walk-forward splitter,
benchmark passivi — il **cost model** (fee per-broker + slippage ADR-013 +
proxy di spread), gli **indicatori tecnici** (`src/features/indicators.py`:
SMA/EMA/MACD/RSI/Bollinger/ATR/OBV), i **modelli baseline**
(`src/models/baseline.py`: random walk + momentum, forecast→posizione,
strategy returns net-of-cost, metriche directional accuracy/MAE) e la
**classificazione di regime** (`src/features/regime.py`, causale bull/bear
+ decomposizione metriche). 160/160 pytest verde, ruff + pyright puliti sui
moduli core, **CI GitHub Actions verde**. **Esecuzione out-of-sample
end-to-end + regime-aware fatta** (notebook 04 su BTC/ETH/LINK reali): il
momentum net batte buy-and-hold su 2 asset su 3 con un edge **difensivo**
(meno drawdown nei bear), non direzionale; la decomposizione per regime
spiega perché fallisce su LINK (whipsaw nei bear). Mancano: ARIMA (serve
`statsmodels`), allineamento macro a *release date* (FRED), IRR per DCA.

### Criterio di completamento ✅
Possiamo confrontare qualsiasi nuovo modello con baseline solide e affidabili.
**Raggiunto**: framework walk-forward no-look-ahead con costi, baseline
(random walk + momentum) valutati out-of-sample su dati reali, metriche
decomposte per regime, CI riproducibile verde. PR #4 consolidata.

---

## Fase 2.1 — Rifiniture baseline (non bloccante, opportunistica)

**Obiettivo**: completare i residui di Fase 2 che non bloccano l'avanzamento
a Fase 3. Affrontabili quando comodo, anche in parallelo ad altre fasi.

### Deliverable
- [ ] **ARIMA** come terzo baseline → richiede `statsmodels` in
      `pyproject.toml`. Le evidenze del notebook 04 (daily return = rumore,
      random walk vince su MAE) suggeriscono che perderà contro il momentum,
      ma va testato per completezza
- [ ] **IRR money-weighted** per un confronto DCA corretto (il `total_return`
      del DCA non è comparabile time-weighted — vedi caveat notebook 04)
- [ ] **Allineamento macro FRED a *release date*** (non reference date) nel
      walk-forward → serve quando si useranno feature macro nei modelli
- [x] **Robustezza cross-asset del filtro di regime** (notebook 05):
      esteso a SOL/POL. **Ipotesi "danno = whipsaw da volatilità" SMENTITA**
      (corr vol↔Δsharpe bear = −0.09): il momentum protegge 4 asset su 5
      *inclusi i due più volatili* (SOL, POL). LINK è un outlier specifico,
      non spiegato dalla volatilità → indagine mirata aperta
- [x] **Sensibilità del momentum al `lookback`** (notebook 05): griglia
      5-150 su tutti e 5 i Tier 1. Edge **robusto** (collina, non picco) su
      BTC/ETH/SOL/POL; `beats_bh` su 4-7 lookback su 8. LINK fragile (2/8).
      Il risultato del notebook 04 non era un artefatto del parametro
- [ ] **Pulizia debito pyright** ingestion (~147 finding pandas-stubs) per
      rendere la CI pyright-bloccante ovunque, non solo sui moduli core

### Criterio di completamento
Nessuno stringente: è un backlog di qualità. Si chiude quando i punti
diventano rilevanti per le fasi successive o quando c'è banda per farli.

---

## Fase 3 — Sentiment & notizie 🔄 *in corso (2026-05-30)*

**Obiettivo**: introdurre la dimensione "informativa" non-numerica.

> ✅ **Sblocco rete confermato**: news (Cointelegraph/CoinDesk/Google News) e
> HuggingFace raggiungibili. I feed publisher nativi sono anti-bot instabili da
> IP datacenter (non aggirati, ADR-018); Google News fa da backbone affidabile.

### Deliverable
- [x] Pipeline ingestion notizie da ≥2 fonti (Cointelegraph + CoinDesk +
      Google News per asset). `src/ingestion/news/` (PR #6, in `main`):
      `parse_rss`, `feeds`, `persist`, `fetch_news`. Girata su dati reali (560 item)
- [~] NLP pipeline: **sentiment scoring Layer 1 (VADER) fatto** (ADR-023,
      `src/ai/lexicon/`). Entity recognition / topic classification: non fatti
      (rinviati: l'evidenza non giustifica ancora di salire di complessità)
- [x] Feature derivate: `src/features/news_features.py` — sentiment rolling,
      variazione di tono, volume notizie + z-score (causali, testate)
- [x] Test di correlazione lead/lag sentiment & news-volume vs rendimenti /
      volatilità (`notebooks/06`). **Esito onesto: nessun segnale lead** con i
      dati attuali (il +0.32 di n=23 svanisce a n=143 → artefatto). Da rieseguire
      su storia più lunga (cron ADR-025 attivo)
- [ ] Pipeline estendibile a Twitter/X, Reddit (se accesso disponibile)
- [ ] Storia news densa (mesi) → rieseguire nb 06; per-asset su tutti i Tier 1

### Criterio di completamento
Abbiamo dataset news-derived allineato temporalmente con dati di mercato (✅), e
abbiamo testato statisticamente se il sentiment ha potere predittivo (✅, esito
negativo sui dati attuali — da riconfermare su più storia).

---

## Fase 4 — Modelli multifattoriali 🔄 *avviata (2026-05-30)*

**Obiettivo**: combinare tecnico + sentiment + macro in modelli ML.

### Deliverable
- [x] Macro features: tassi, DXY, M2, yield treasury — `src/features/macro_features.py`,
      **point-in-time-safe** (publication lag per release date, chiude il debito
      look-ahead del nb 03). Funzioni causali + 10 test offline
- [ ] On-chain features (se accessibili): hash rate, active addresses, exchange flows
- [x] Feature engineering pipeline pulita e riproducibile — `src/features/dataset.py`
      (`assemble_design_matrix`: join tecnico+macro+news, lag 1 anti-look-ahead)
- [~] Modelli ML in ordine di complessità: **logistic regression fatta**
      (`src/models/multifactor.py`, walk-forward OOS, scaler fit-on-train).
      Gradient boosting (XGBoost/LightGBM) → solo se un fattore mostra edge
- [x] Cross-validation temporale rigorosa — walk-forward (riusa Fase 2), scaler
      fit-on-train-only (no leakage di preprocessing)
- [ ] Feature importance analysis — quando un modello mostrerà segnale
- [x] Confronto out-of-sample vs baseline Fase 2 — nb 07 (tecnico: 0.497 ≈
      coin-flip) + nb 08 (tecnico vs tecnico+macro su indice comune n=2249:
      0.5007 → 0.5060, delta nel rumore). **Nessun edge** in entrambi

### Criterio di completamento ✅ (risposta data)
Sappiamo dire (con metriche, non con sensazioni) se l'integrazione
multifattoriale aggiunge valore predittivo rispetto al tecnico puro.
**Risposta (nb 08)**: a frequenza **daily** su BTC, l'aggiunta della macro **non
aggiunge** valore predittivo direzionale (delta accuracy nel rumore). Coerente
con la EDA Fase 1 (segnale macro mensile, ~0 daily). Resta aperto se conti a
orizzonte mensile e/o con le news quando il cron avrà accumulato storia.

---

## Fase 5 — Cicli, regimi & contestualizzazione 🔄 *criterio raggiunto (2026-05-31)*

**Obiettivo**: il mercato non è omogeneo nel tempo. Identificare regimi e
adattare l'analisi.

### Deliverable
- [x] Detection di market regime: trend bull/bear (Fase 2) + **vol high/low**
      (`classify_vol_regime`, soglia relativa causale) + **4-stati**
      (`combine_regimes`). Scelta deliberata: soglie trasparenti, **non** HMM
      (niente scatole nere/dipendenze pesanti — coerente con ADR Fase 2)
- [x] Analisi cicli specifici crypto: **halving clock** (`src/features/cycles.py`):
      days since/to halving + `halving_phase` ciclica, puramente calendariali
- [x] Modelli condizionati al regime: feature regime/ciclo aggiunte alla design
      matrix (`is_bull`, `is_highvol`, `halving_phase`), laggate anti-look-ahead
- [x] Test "i modelli migliorano se sanno il regime?": notebook 09, accuracy OOS
      **0.498 → 0.510** (delta +0.0115, nel rumore su n=2430) → **conditioning
      non dà edge**. Ma la **decomposizione** è netta: rendimento BTC fortemente
      regime-dipendente (bull_high_vol Sharpe 2.97 vs bear_high_vol −1.20)

### Criterio di completamento ✅ (risposta data)
Capiamo se e quanto la contestualizzazione per regime migliora le predizioni.
**Risposta (nb 09)**: il *conditioning* non produce edge predittivo direzionale
a daily (delta nel rumore), ma la *decomposizione* per regime è descrittivamente
essenziale — i rendimenti sono fortemente regime-dipendenti, quindi ogni metrica
va letta per regime, mai in media. Coerente con l'edge difensivo di Fase 2.1.

---

## Fase 6 — Paper trading engine

**Obiettivo**: permettere all'utente di "investire" con un budget virtuale sui
segnali generati dal sistema, simulando con realismo guadagni e perdite. È il
**gate di validazione finale** prima di qualsiasi considerazione di live
trading. Vedi ADR-010 per i principi non negoziabili.

### Deliverable
- [x] Modulo `src/execution/` con interfaccia `Broker` astratta
- [~] Implementazione `PaperBroker` (nucleo in PR, latenza=1 barra implicita nel fill a t+1):
  - [x] No look-ahead (ordine al tempo `t` ⇒ fill alla candela `t+1`, all'**open**; guardia `created_at >= bar.ts` testata)
  - [x] Modello fee tarato su Binance spot (riusa `TransactionCostModel` ADR-012 — stesso modello dei backtest)
  - [x] Modello slippage (ADR-013, peggiora il prezzo nel verso del trade)
  - [x] Latenza simulata: una candela, strutturale nel fill a t+1
- [x] Portfolio manager: posizioni (average cost), P&L realizzato/non, equity, fee cumulate
- [x] Persistenza completa (`ScenarioStore`: state.json + orders/equity parquet,
      committata in `data/paper/` per sopravvivere ai container — ADR-029)
- [x] Tipi di ordine: Market, Limit (Stop e TP in seconda iterazione)
- [x] Position sizing configurabile (frazione di cassa, `qty_for_cash_fraction`)
- [x] Long-only inizialmente (sell > held e buy > cash **rigettati**, auditabile)
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

### Backlog eventi/dashboard (da revisione 2026-07-02, ADR-028)
- [x] Attribuzione v2: trigger doppio (z OR return assoluto), severità
      major/notable, market pulse, canale world-news (ADR-028)
- [x] **(C1)** Cron news da 6h a 3h — freschezza della sezione Eventi
- [x] **(C2)** `market_series.json` da 4 a 10 serie: tutti i Tier 1 +
      NDX + Tech (XLK) + Semi (SMH). La UI è a chip (una serie alla volta)
- [x] **(D1)** Test empirico VADER vs FinBERT (notebook 12, eseguito su
      6.971 titoli dopo sblocco allowlist CDN HF). Ipotesi e regola di
      adozione **pre-registrate in git prima dei risultati**. Esito:
      accordo di polarità solo 49.7% (H1 ✓); FinBERT correla meglio
      same-day su entrambi (BTC ρ 0.517 vs 0.379, +36%; ETH 0.476 vs
      0.256 n.s., +86%) ma la **barra pre-registrata (≥+50% su entrambi)
      NON è superata** → **si resta su VADER** (i pali non si spostano
      post-hoc). Nessun lead per nessuno dei due (H3 ✓, conferma nb 06);
      la stampa insegue il prezzo. **Follow-up**: rieseguire nb 12 a
      campione raddoppiato (n≈80-90 giorni, ~fine agosto 2026); se la
      barra è superata su entrambi → ADR di adozione FinBERT
- [x] **(D2)** Spike di volume di copertura (`src/features/news_volume.py`):
      conteggio titoli/giorno vs baseline rolling causale con floor di
      Poisson (feed costanti) e `min_count` (feed sottili). Annota ogni
      move con `coverage {count, zscore, spike}` → badge in dashboard.
      Validato su dati reali: XLK 5/6 (−6.7%) → spike z=8.4; POL 5/6
      (−10.5%) → nessuno spike (crollo senza notizie, stampa il giorno
      dopo) — i due segnali si completano. Caveat: nel periodo di rampa
      dei feed (fine maggio) gli spike riflettono la maturazione
      dell'archivio, artefatto che svanisce col tempo
- [ ] **(D3)** Calibrare le soglie assolute ADR-028 (4%/2.5%) dopo qualche
      settimana di eventi osservati

### Criterio di completamento
Dato lo stato corrente dei mercati e delle notizie, il sistema produce un
output sintetico, comprensibile e onesto sulla confidenza dei segnali, e
l'utente può consultare lo stato del paper portfolio in qualsiasi momento.

---

## Fase 8 — Espansione al mercato azionario tradizionale (equity)

**Obiettivo**: estendere il sistema, già validato su crypto via paper
trading, al **mercato azionario classico** (equity, ETF, indici). Vedi
ADR-014 per il principio architetturale: il sistema è già scritto
asset-class-agnostic dalla Fase 1, quindi questa fase è
**implementazione + adattamento**, non riscrittura.

> 🟡 **Anticipo pragmatico (2026-06-05)**: su richiesta utente è stato avviato un
> primo tassello equity **fuori dall'ordine stretto dei prerequisiti** (il paper
> trading crypto non è ancora consolidato), perché serviva *ora* per "vedere cosa
> si muove in borsa e perché". Già in `main`: **screener di rotazione settoriale**
> (~20 ETF, `REPORT_EQUITY.md` auto-aggiornato), **attribuzione eventi** sugli ETF
> (rif. S&P 500) e **fonte news azionaria** (Google News per-settore, ADR-027). Il
> grosso della Fase 8 (paper broker equity, calendari, corporate actions,
> riallenamento modelli) resta subordinato ai prerequisiti.

### Prerequisiti
- Fasi 1–6 completate con paper trading crypto consolidato
- Decisioni sull'universe equity prese (open question)

### Deliverable
- [ ] Decidere universe equity iniziale (S&P 500? NASDAQ 100? FTSE MIB
      italiano? Combinazione?) — vedi `OPEN_QUESTIONS.md` Q16
- [ ] Integrare sorgenti dati equity: Yahoo Finance (free, baseline),
      Alpha Vantage, Polygon.io free tier
- [ ] Gestione **trading calendar** (orari di mercato, weekend, festività)
- [ ] Gestione **corporate actions**: dividendi, splits, spin-off
- [~] Estensione del sentiment/news per coprire equity-specifico: **fatto a
      livello settoriale** (Google News per-settore, ADR-027, stessa pipeline
      VADER) → attribuzione eventi sugli ETF ha un canale news. Earnings/analyst
      ratings/10-K-10-Q più granulari restano da fare
- [ ] Estensione del paper broker per equity: nuovo `EquityPaperBroker` con
      fee model di un broker realistico (proposta: Interactive Brokers,
      che è uno standard di riferimento; calibrabile per altri)
- [ ] Riallenamento modelli su asset equity con metriche dedicate
- [ ] Comparazione **portfolio cross-asset** (crypto + equity nello stesso
      paper portfolio)

### Criterio di completamento
Il sistema produce segnali e paper-trade su almeno una manciata di asset
equity, con metriche out-of-sample paragonabili al crypto.

---

## Fase 9 (eventuale) — Live trading

**Non in roadmap attiva.** Vedi ADR-004 per i gate:
- ≥ 3 mesi di paper trading positivo vs benchmark
- Risk management framework formalizzato
- Nuova ADR esplicita
- Conferma documentata dell'utente

---

## Stream parallelo — Modulo didattico

Vedi ADR-015. Cresce in `education/` **in parallelo** alle fasi tecniche.
Non ha una fase dedicata: si scrive un capitolo quando l'argomento è
"fresco" perché lo stiamo toccando nel codice.

**Quattro livelli**:
- `L1_principiante/` — Investor 101
- `L2_intermedio/` — Smart Investor
- `L3_avanzato/` — Quantitative Investor
- `L4_esperto/` — Wolf of Wall Street / Professional

### Cosa va fatto nella Fase 1 ✅ *completato (2026-05-29)*
- [x] Creare `education/README.md` come indice navigabile
- [x] Stub delle 4 cartelle di livello con un README ciascuna
- [x] Primo capitolo L1: "Cos'è un asset, una borsa, un broker"
- [x] **Bonus L1 completo** (oltre il minimo di Fase 1):
      tutti i 10 capitoli di L1 pubblicati durante la Sessione 3.
      Asset/borsa/broker, tipi di ordine, lettura grafico,
      fee/spread/slippage, portafoglio, DCA, vol/drawdown, custodia,
      fiscalità, "cosa NON è il trading". L1 chiuso.

### Capitoli da scrivere mentre si lavora alle fasi tecniche
- Durante Fase 1 (ingestion): L1 — basics di mercato, OHLCV, fee
- Durante Fase 2 (backtest): L3 — backtesting onesto, look-ahead bias
- Durante Fase 3 (NLP/news): L2 — bias cognitivi, FOMO; L3 — sentiment analysis
- Durante Fase 4 (ML): L3 — ML in finanza, time-series CV
- Durante Fase 5 (regimi/cicli): L2 — cicli; L3 — regime detection
- Durante Fase 6 (paper trading): L1 — DCA vs lump sum; L2 — risk management
- Durante Fase 7 (output): integrazione capitoli in dashboard
- Durante Fase 8 (equity): L1 e L2 — equity basics, fondamentali

I capitoli di **L4 ("Wolf")** sono scritti per ultimi e includono argomenti
che probabilmente non implementeremo (es. market microstructure, HFT
considerations) ma che vanno conosciuti per onestà intellettuale.

---

## Note sulla roadmap

- **Le fasi sono lineari ma rivisitabili**: scoperte in Fase 3 possono
  richiedere di tornare in Fase 1 (nuove sorgenti dati). Va bene, basta
  tracciarlo in `STATUS.md`.
- **Ogni fase può "fallire"**: scoprire che non c'è segnale è un risultato
  valido.
- **Le fasi 5, 6, 7, 8 sono condizionate**: ha senso affrontarle solo se le
  fasi precedenti producono baseline funzionanti. In particolare:
  - **Fase 6 (paper trading)** ha senso solo se Fase 4 produce modelli che
    battono benchmark out-of-sample
  - **Fase 8 (equity)** ha senso solo se Fase 6 dimostra che il sistema
    funziona su crypto: estendere un sistema non-funzionante non lo fa
    diventare funzionante
- **Lo stream educational è disaccoppiato**: cresce in parallelo, non
  blocca e non è bloccato dalle fasi tecniche.
- **Eventuale Fase 9 — Live trading**: vedi sopra, condizionata e fuori
  roadmap attiva.
