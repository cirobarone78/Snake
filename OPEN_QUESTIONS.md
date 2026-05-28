# OPEN_QUESTIONS.md

> Domande aperte, ipotesi da validare, decisioni rinviate.
> Quando una domanda viene risolta: spostala in `DECISIONS.md` come ADR e
> rimuovila da qui (o marca con `[RISOLTA → ADR-NNN]`).

---

## 🔴 Decisioni critiche da prendere prima della Fase 1

### Q1 — Scope finale: trading reale o solo ricerca?
Anche se l'ADR-002 ha stabilito che partiamo come **ricerca**, vale la pena
esplicitare l'ambizione finale.

Opzioni:
- **A**: solo ricerca e segnali (output: dashboard/report)
- **B**: ricerca ora, paper trading in futuro
- **C**: ricerca ora, live trading in futuro (con tutti i requisiti che implica:
  risk management, broker integration, sicurezza, capital allocation)

*Impatto*: determina molti requisiti tecnici e di sicurezza.

---

### Q2 — Asset universe iniziale
Su cosa concentrare l'effort iniziale di ingestion e analisi?

Opzioni:
- **A**: Solo Bitcoin (BTC) — più dati storici, mercato più maturo
- **B**: BTC + ETH — coppia di riferimento crypto
- **C**: Top 10 crypto per market cap
- **D**: Top 10 + alcuni indici tradizionali (S&P 500, NASDAQ) per correlazione
- **E**: Universe ampio (top 50+) — più rumore, più dati

*Raccomandazione personale*: iniziare con **A** o **B**. Espandere solo dopo
che la pipeline funziona.

---

### Q3 — Timeframe predittivo
Per quale orizzonte temporale produciamo segnali?

Opzioni:
- **A**: Intraday (minuti-ore) — richiede dati ad alta frequenza, latenza bassa
- **B**: Daily (1-7 giorni) — più gestibile, meno rumore
- **C**: Settimanale/mensile — meno operazioni, più analisi macro
- **D**: Multi-timeframe (es. predire sia daily che weekly)

*Raccomandazione*: partire **daily** è il sweet spot ricerca/complessità.

---

### Q4 — Tipo di output del modello (target variable)
Cosa prevediamo esattamente?

Opzioni:
- **A**: Direzione (up/down) — classificazione binaria
- **B**: Rendimento atteso (regressione)
- **C**: Probabilità di movimento >X% in N giorni
- **D**: Volatilità attesa (utile anche se la direzione è incerta)
- **E**: Combinazione (es. direzione + confidenza + volatilità)

*Nota*: la scelta determina la "ground truth" usata in training e backtest.

---

### Q5 — Budget per dati premium
Alcune fonti (Glassnode, Nansen, Bloomberg, Kaiko, Coin Metrics Pro) hanno
dati di qualità ma sono a pagamento. Free tier sono limitati.

Opzioni:
- **A**: Solo gratuiti (CoinGecko, Binance/Coinbase public API, Yahoo Finance,
  RSS news feed, etc.) — fino a quando regge
- **B**: Eventualmente piccolo budget per 1-2 fonti chiave (es. Glassnode Lite)
- **C**: Budget significativo da subito

*Raccomandazione*: **A** fino a Fase 3, poi rivalutare quando si conoscono i
limiti concreti.

---

### Q6 — Stack tecnologico
Linguaggio e ecosistema.

Opzioni:
- **A**: **Python** (pandas, NumPy, scikit-learn, statsmodels, PyTorch/TF,
  Hugging Face per NLP) — standard de facto per data science e ML
- **B**: Python per analisi + Rust/Go per ingestion ad alta performance
- **C**: R per statistica + Python per ML
- **D**: JavaScript/TypeScript (stack moderno, ma debole su ML)

*Raccomandazione*: **A**. Tutto il resto è prematura ottimizzazione.

Sotto-decisioni se Python:
- Package manager: `uv` (moderno, veloce) vs `poetry` vs `pip+venv`
- Notebook: Jupyter vs Marimo
- Type checking: mypy/pyright sì o no?

---

## 🟡 Decisioni importanti ma non bloccanti

### Q7 — Storage dei dati
Come persistiamo i dati raccolti?

Opzioni:
- **A**: File parquet/CSV locali in `/data` (gitignored)
- **B**: SQLite per dati strutturati piccoli
- **C**: DB time-series locale (DuckDB, TimescaleDB, InfluxDB)
- **D**: Cloud object storage (S3-compatible)

*Probabile*: iniziare con **A** (parquet), evolvere se serve.

---

### Q8 — Forma finale dell'output
Quando arriviamo a Fase 6, in che forma il sistema espone i risultati?

Opzioni:
- **A**: Dashboard web (Streamlit/Gradio/Dash) — interattiva
- **B**: Report markdown/HTML generato periodicamente
- **C**: Alerting (Telegram/email) su segnali significativi
- **D**: API + client a scelta
- **E**: Combinazione

---

### Q9 — Modello di "verità di base" per news
Quando estraiamo sentiment da news, come validiamo che sia corretto?

- LLM commerciale (Claude/GPT API) ha costo per chiamata
- Modelli open-source (FinBERT, sentence-transformers) sono gratuiti ma meno accurati
- Labeling manuale è lento ma è ground truth

*Decisione rinviata a Fase 3.*

---

### Q10 — Frequenza di ingestion notizie
Real-time vs batch giornaliero?

*Decisione rinviata a Fase 3, dipende anche da Q3 (timeframe).*

---

## 🟢 Domande di ricerca (non decisioni operative)

Queste sono ipotesi da testare nel corso del progetto, non da risolvere a priori.

- Il sentiment delle news ha potere predittivo *lead* sui prezzi, o è solo *concomitante/lagging*?
- Le notizie tech (es. annunci adoption, exploit, regulation) hanno impatto più forte di quelle macro?
- I cicli di halving Bitcoin sono ancora predittivi nel 2026+ o sono "pricedin" dal mercato?
- Esistono regimi di mercato distinguibili sistematicamente?
- L'integrazione multifattoriale aggiunge davvero valore o il tecnico puro è sufficiente?
- Quali sono i lag temporali tipici tra una notizia e la reazione di prezzo?
- Le correlazioni cross-asset (BTC vs S&P, vs gold, vs DXY) sono stabili o regime-dependent?

*Queste vanno trasformate in esperimenti specifici durante le fasi corrispondenti.*
