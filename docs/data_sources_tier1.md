# Inventario sorgenti dati — Tier 1

> Tier 1 (ADR-017): le fonti **indispensabili** per Fase 1–2.
> Solo gratuite o free tier. Vedi ADR-008 per il budget e ADR-018 per
> i limiti etico-legali.

Per ogni fonte sono documentati: scope, storico disponibile, rate limit,
campi forniti, licenza e note operative.

---

## 1. Yahoo Finance — Market data (multi-asset)

| Campo | Valore |
|---|---|
| **Scope** | OHLCV + adjusted close per crypto, equity, indici, FX, commodity |
| **Access** | Libreria `yfinance` (free, no API key) |
| **Storico** | Dal 2014 per BTC, dal 2017 per ETH, variabile per altcoin (POL solo dal 2024) |
| **Granularità** | 1m–3mo; storico intra-day limitato (60 giorni per 1m) |
| **Rate limit** | Non documentato ufficialmente; suggerito ≤2 req/s per evitare ban |
| **Licenza** | Uso personale/non commerciale OK; Yahoo ToS proibisce redistribuzione massiva |
| **Pro** | Copre tutti i nostri asset class in un unico endpoint; nessuna API key |
| **Contro** | Quality variabile per altcoin; intra-day storico molto limitato; downtime occasionali |
| **Implementato in** | `src/ingestion/tier1/yahoo_finance.py` |

**Note**:
- I simboli crypto sono nella forma `BTC-USD`, `ETH-USD`, etc.
- Indici: `^GSPC` (S&P 500), `^NDX` (NASDAQ 100), `^VIX`, `DX-Y.NYB` (DXY)
- POL-USD copre solo dal Sept 2024 (rename da MATIC); pre-rename è sotto MATIC-USD
- yfinance ritorna timestamp in TZ variabile; il nostro adapter normalizza a UTC

---

## 2. Binance Public API — Market data crypto granulare

| Campo | Valore |
|---|---|
| **Scope** | OHLCV ad alta granularità, order book depth, trade history |
| **Access** | REST + WebSocket pubblici, no API key per dati pubblici |
| **Storico** | Dal 2017 per la maggior parte dei pair |
| **Granularità** | 1s–1mo (klines: 1m/3m/5m/15m/30m/1h/2h/4h/6h/8h/12h/1d/3d/1w/1mo) |
| **Rate limit** | 1200 req/min per IP (peso 1 per richiesta semplice) |
| **Licenza** | Uso libero per dati pubblici; vedi Binance Terms |
| **Pro** | Storico granulare, dati di qualità, depth disponibile |
| **Contro** | Pair denominati in USDT (non USD nativo); copertura altcoin variabile |
| **Implementato in** | *Pianificato, Fase 1.1* |

**Note**:
- Endpoint principale per klines: `GET /api/v3/klines`
- Per BTC/ETH/SOL/LINK usare suffix `USDT` (es. `BTCUSDT`)
- POL: il simbolo è `POLUSDT` dal rename; pre-rename `MATICUSDT`
- Caching: archiviare risposte localmente per evitare ri-fetch

---

## 3. Coinbase Pro / Advanced Trade API — Market data secondario

| Campo | Valore |
|---|---|
| **Scope** | OHLCV crypto via candles endpoint |
| **Access** | REST pubblico, no API key per dati pubblici |
| **Storico** | Da 2015 per BTC; copertura altcoin minore di Binance |
| **Granularità** | 1m/5m/15m/1h/6h/1d |
| **Rate limit** | 10 req/s pubblico |
| **Licenza** | Coinbase Terms; uso pubblico permesso |
| **Pro** | Liquidità USD nativa; cross-check vs Binance per data quality |
| **Implementato in** | *Pianificato, Fase 1.1* |

**Note**:
- Endpoint klines: `GET /products/{id}/candles`
- IDs: `BTC-USD`, `ETH-USD`, `SOL-USD`, etc.
- Massimo 300 candele per richiesta

---

## 4. CoinGecko API — Aggregato market + metadata

| Campo | Valore |
|---|---|
| **Scope** | Prezzi aggregati, market cap, dominance, top 20 list, metadata coin |
| **Access** | REST, free tier senza API key (10-30 calls/min) |
| **Storico** | Daily da 2013 (gratuito limitato a ultimi 365 giorni; storico completo a pagamento) |
| **Granularità** | Daily principalmente; intra-day a pagamento |
| **Rate limit** | Free: ~10-30 calls/min; Demo plan free con key: 30/min |
| **Licenza** | Free tier per uso non commerciale |
| **Pro** | Lista top N dinamica, market cap, dominance, ranking |
| **Contro** | Storico intra-day limitato in free tier |
| **Implementato in** | *Pianificato, Fase 1.1* |

**Note**:
- Useremo CoinGecko soprattutto per `/coins/markets` (top N by market cap) e
  `/global` (BTC dominance, total market cap)
- Per dati OHLCV preferiamo Binance/Yahoo (più liquidi)

---

## 5. Etherscan API — On-chain Ethereum base

| Campo | Valore |
|---|---|
| **Scope** | Transazioni, balance, gas, eventi smart contract, ERC20 transfers |
| **Access** | REST, API key gratuita (necessaria) |
| **Storico** | Dal genesis di Ethereum |
| **Rate limit** | 5 calls/s free tier |
| **Licenza** | Free tier per uso personale/sviluppo |
| **Pro** | Standard de facto per on-chain Ethereum |
| **Contro** | Endpoint orientati a singoli address/tx, non aggregati; per metriche aggregate serve aggregare client-side |
| **Implementato in** | *Pianificato, Fase 1.2* |

**Note**:
- Necessaria API key (gratuita, `.env`)
- Useremo soprattutto: balance di exchange addresses, ERC20 transfer volume,
  gas price storico

---

## 6. Blockchain.com Charts / mempool.space — On-chain Bitcoin base

| Campo | Valore |
|---|---|
| **Scope** | Hash rate, difficulty, mempool size, transaction volume, halving timeline |
| **Access** | REST pubblico, no API key |
| **Storico** | Dal 2009 (genesis Bitcoin) |
| **Rate limit** | Moderato, suggerito ≤1 req/s |
| **Licenza** | Pubblico (vedi termini specifici) |
| **Pro** | Dati Bitcoin di base affidabili e gratis |
| **Contro** | Solo aggregati di alto livello |
| **Implementato in** | *Pianificato, Fase 1.2* |

**Note**:
- Blockchain.com chart API: `GET /charts/{chart-name}` (es. `hash-rate`, `n-transactions`)
- mempool.space utile per stato mempool real-time

---

## 7. Glassnode Free Tier — On-chain metrics aggregate

| Campo | Valore |
|---|---|
| **Scope** | Active addresses, exchange flows, supply distribution, MVRV (limitato in free) |
| **Access** | REST con API key (free tier disponibile) |
| **Storico** | Variabile per metrica, generalmente multi-anno |
| **Rate limit** | Free tier: limitato; suggerito caching aggressivo |
| **Licenza** | Free tier per uso personale; Pro per features avanzate |
| **Pro** | Metriche on-chain prodotte da analista, non solo raw chain data |
| **Contro** | Free tier copre solo un sottoinsieme delle metriche; le interessanti (SOPR, Realized Cap, etc.) sono a pagamento |
| **Implementato in** | *Pianificato, Fase 1.2* |

**Note**:
- API key gratuita richiesta (`.env`)
- Selezionare con attenzione le metriche del free tier per non sprecare richieste

---

## 8. FRED (Federal Reserve Economic Data) — Macro USA

| Campo | Valore |
|---|---|
| **Scope** | Tassi di interesse, CPI, M2, treasury yields, employment, GDP |
| **Access** | REST con API key gratuita; libreria `fredapi` |
| **Storico** | Decennale per quasi tutto, secolare per molte serie |
| **Rate limit** | 120 req/min con API key |
| **Licenza** | Pubblico (dati Federal Reserve) |
| **Pro** | Standard accademico, dati ufficiali, storico lunghissimo |
| **Contro** | Macro USA-centric (per macro EU usare ECB SDW, Tier 2) |
| **Implementato in** | *Pianificato, Fase 1.2* |

**Note**:
- Serie chiave: `FEDFUNDS` (Fed Funds rate), `CPIAUCSL` (CPI), `M2SL` (M2),
  `DGS10` (10Y Treasury), `DGS2` (2Y Treasury), `T10Y2Y` (yield spread)
- Frequenza: monthly per molte serie macro, daily per yield

---

## 9. CryptoPanic Free Tier — News aggregate crypto

| Campo | Valore |
|---|---|
| **Scope** | Aggregato di news crypto da centinaia di fonti, con tagging e sentiment proxy |
| **Access** | REST con API key (free tier disponibile) |
| **Storico** | Limitato in free tier (qualche giorno); per storico più lungo serve Pro |
| **Rate limit** | Free: ~1 req/s, dettagli su pagina API |
| **Licenza** | Free tier per personal/research |
| **Pro** | Aggregato di fonti, evita di gestire decine di feed RSS separati |
| **Contro** | Storico breve in free; per backtest serio dovremo archiviare incrementalmente |
| **Implementato in** | *Pianificato, Fase 3* (news entrano in Fase 3) |

**Note**:
- API key gratuita richiesta
- In Fase 3 inizieremo ad archiviare incrementalmente per costruire un nostro
  storico di news

---

## Stato di implementazione

| Fonte | Stato | Note |
|---|---|---|
| Yahoo Finance | ✅ Implementata | `src/ingestion/tier1/yahoo_finance.py` |
| Binance API | ⏳ Pianificata | Fase 1.1 |
| Coinbase API | ⏳ Pianificata | Fase 1.1 |
| CoinGecko | ⏳ Pianificata | Fase 1.1 |
| Etherscan | ⏳ Pianificata | Fase 1.2 (richiede API key) |
| Blockchain.com / mempool | ⏳ Pianificata | Fase 1.2 |
| Glassnode free | ⏳ Pianificata | Fase 1.2 (richiede API key) |
| FRED | ⏳ Pianificata | Fase 1.2 (richiede API key) |
| CryptoPanic | ⏳ Pianificata | Fase 3 (richiede API key) |

## Prerequisiti operativi

- **Network policy**: l'ambiente di esecuzione deve consentire outbound HTTPS
  verso i domini elencati. In Claude Code on the web, configurare l'allowlist:
  `query2.finance.yahoo.com`, `query1.finance.yahoo.com`,
  `api.binance.com`, `api.exchange.coinbase.com`,
  `api.coingecko.com`, `api.etherscan.io`, `api.blockchain.info`,
  `mempool.space`, `api.glassnode.com`, `api.stlouisfed.org`,
  `cryptopanic.com`.
- **API keys** (per fonti che le richiedono): conservare in `.env` locale,
  mai in commit (già nel `.gitignore`).
