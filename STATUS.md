# STATUS.md

> **Fotografia dello stato corrente.** Non è un diario: la cronaca delle
> sessioni passate vive in [`docs/STATUS_ARCHIVIO.md`](./docs/STATUS_ARCHIVIO.md).
> Chi riprende il lavoro (umano o agente) legge questo file per primo, e tiene
> questo file **sotto le 200 righe**: se cresce, la cronaca si sposta in archivio.

**Ultimo aggiornamento**: 2026-08-24 — WP1 (storage partizionato) e WP2 (dataset ETF) mergiati

---

## Dove siamo

- **`main` = `8de7ea2`**: PR #52, WP0, **WP1** (#55) e **WP2** (#56) tutti mergiati.
- **Test**: 517 passati (`uv run pytest -q`), ruff pulito, pyright pulito sui
  moduli core e su `src/ingestion/news`.
- **Milestone corrente**: **Fase 9 — Ranking ETF probabilistico**; WP0/WP1/WP2
  chiusi, **il prossimo è WP3**. Il piano operativo è
  [`docs/PIANO_SVILUPPO.md`](./docs/PIANO_SVILUPPO.md): riferimento per tutti i WP,
  con decisioni D1–D12 e ipotesi H1–H3 scritte **prima** di qualunque backtest.
- **Fasi 0–8**: chiuse o in accumulo dati (`ROADMAP.md`). Il nucleo di ricerca ha
  già risposto alla domanda predittiva daily: **nessun edge direzionale** (sotto).

## Workflow (GitHub Actions)

| Workflow | Cadenza | Stato |
|---|---|---|
| `ci.yml` | push/PR | 🟢 verde |
| `news-history.yml` | ogni 3h | 🟢 attivo (ultimo commit bot 2026-08-24) |
| `category-history.yml` | giornaliero | 🟢 attivo (2026-08-24) |
| `sector-history.yml` | giornaliero | 🟢 attivo (2026-08-24) |
| `macro-history.yml` | giornaliero | 🟢 attivo (2026-08-24) |
| `paper-shadow.yml` | giornaliero | 🟢 attivo (2026-08-24) |
| `dca.yml` | giornaliero | ⏳ mergiato con la PR #52, **primo run ancora da osservare** |
| `etf-dataset.yml` | solo manuale | 🟢 **primo run 2026-08-24 verde** (21/21 ticker, vedi sotto) |

I cron committano con `[skip ci]`. GitHub schedula con **ritardo variabile** (un
cron delle 07:00 può girare alle 12:36 UTC): fidarsi del timestamp nel report.

## Risultati empirici consolidati

Elenco di ciò che è stato **misurato**, non di ciò che si spera. Gli esiti
negativi contano quanto i positivi e restano qui apposta.

- **Battere SPY è più difficile di quanto sembri.** Sul panel WP2 (2005→2026,
  20 ETF settoriali) l'outperformance **incondizionata** vs SPY è **0,489 a 20
  sedute** (n=93 117) e **0,482 a 60** (n=92 317): il settore mediano batte SPY
  meno di una volta su due — nel periodo l'S&P cap-weighted è stato trainato
  dalle mega-cap. È la **baseline climatologica** che H2 deve battere in Brier
  score, piantata *prima* di modellare (WP3).

- **Nessun edge direzionale daily.** Modelli tecnici e tecnico+macro su BTC in
  walk-forward OOS: accuracy 0.5007 → 0.5060 (n=2249) — dentro il rumore. La
  macro **non** aggiunge potere predittivo a frequenza daily (il segnale CPI vive
  a frequenza mensile). Nessun leakage: un bug avrebbe gonfiato il delta.
- **Il sentiment news (VADER, Layer 1) non anticipa nulla** con i dati attuali.
  Il `corr(news_count, |return|) = +0.32` visto su n=23 è **svanito a n=143**
  (≈ −0.07 a lag 1): artefatto di piccolo campione. Caso di studio permanente su
  quanto costa concludere presto.
- **Il momentum relativo non dà edge cross-sectional** sui 20 ETF settoriali
  (2012→2026): il bucket `strong` ≈ baseline a 5/21 sedute e **fa peggio a 63**
  (−2.1 pp di hit-rate). Con finestre non sovrapposte la differenza svanisce; OOS
  il `strong` resta ultimo a 63g in **entrambe** le metà. L'unico segnale stabile
  è negativo: non inseguire i settori più forti su hold di 3 mesi.
- **È il regime a condizionare, non il momentum.** Forward più alti dopo
  `bear_high_vol` (21g +3%, 63g +7%); il pericolo è `bear_low_vol`. Coerente con
  la Fase 5: il rendimento BTC è fortemente regime-dipendente (Sharpe
  `bull_high_vol` **+2.97** vs `bear_high_vol` **−1.20**) — **la media
  full-sample mescola mondi opposti**. Conoscere il regime però **non** predice:
  accuracy 0.498 → 0.510, nel rumore.
- **La fase di ciclo crypto (halving) condiziona forte** — forward 126g: early
  mediana +23% (hit 0.64), late +18% (hit 0.66), **mid mediana −29% (hit 0.21)**;
  "mid = zona pericolo" è OOS-stabile in direzione. ⚠️ **Descrittivo, non un edge
  provato**: ~1,5–2 cicli di halving = essenzialmente 2 bear (2018, 2022).
- **Piano di accumulo (ADR-030)**: la regola "compra ciò che è più sotto peso"
  non ha edge di **rendimento** (54,5° percentile contro 200 semi casuali) ma ha
  un effetto **reale e OOS-stabile sull'allocazione** (distanza finale dal target
  5,3 pp vs 30,5 pp nella metà OOS). Il momentum come regola di scelta è la
  peggiore (40,5° percentile, *sotto* il caso). La componente "buy-the-dip" era
  96° percentile in-sample e **ultima OOS** → rimossa dal punteggio di default.
- **Fondamentali dei progetti (ADR-031)**: descrivono, non predicono, e non è
  possibile un backtest onesto (storia corta, piena di sopravvissuti). Tre
  trappole codificate: sconosciuto ≠ zero; la tesi monetaria (BTC) è esente
  dall'asse "cattura del valore"; zero commit ≠ progetto morto.
- **Lo screen delle candidate è survivorship-biased per costruzione** e non è
  risolvibile con questi dati: la classifica di oggi contiene solo i sopravvissuti.
  È scritto nel modulo, nel report e nel tab.

## Fase 9 — WP2: dataset ETF point-in-time (fatto)

Il panel su cui WP3 addestrerà le baseline. `SPY` nel registry (benchmark D2);
`src/features/etf_dataset.py` (funzioni pure: 19 feature causali, target excess
return 20/60 sedute vs SPY, regime 4-stati per data); CLI `build_etf_dataset`
(panel gitignored perché ricostruibile); `etf-dataset.yml`; 24 test offline. Il
test che conta è quello di **causalità** — panel ricostruito su storia troncata a
`t`, ogni feature fino a `t` identica — più il controllo inverso sul target, così
il primo non passa per un errore di confronto. Narrativa completa in
[`docs/STATUS_ARCHIVIO.md`](./docs/STATUS_ARCHIVIO.md) e nella PR #56; le
semplificazioni (`auto_adjust` ⇒ total return; universo = ETF esistenti oggi ⇒
survivorship residuo; storie corte tenute con NaN) sono nel docstring del modulo.

**Validazione live** (run `etf-dataset` del 2026-08-24 post-merge, l'attività #1
di questa milestone — ora **chiusa**):

- **21/21 ticker scaricati**, nessun feed mancante o congelato. Panel: **93 517
  righe × 27 colonne**, 2005-01-03 → 2026-08-24.
- **Le date di quotazione cadono dove attese** — la verifica vera: XLC 2018-06-19,
  BOTZ 2016-09-13, CIBR 2015-07-07, XLRE 2015-10-08, URA 2010-11-05, ICLN
  2008-06-25, ITA 2006-05-05; gli 11 SPDR originali dal 2005-01-03, 5 444 righe.
- **Le feature mancanti sono solo warm-up**, non buchi: 1,5% sulle storie lunghe,
  3,9% su XLC — stesse ~1 500 celle NaN in assoluto (la somma delle finestre),
  cambia solo il denominatore. Un feed rotto avrebbe dato un profilo diverso.

**Da sapere**: `pyright: strict` puro non è raggiungibile su un modulo
pandas-heavy (`pandas` non ha `py.typed` → ogni membro è unknown; lo stesso vale
per i moduli strict esistenti). Il modulo è strict **meno le quattro regole** che
nascono da quella mancanza; per lo strict pieno servirebbe `pandas-stubs` come
dip. dev — da ADR, non da WP. D4 resta da confermare, ma il dataset espone
entrambe le forme del target (regressiva e binaria) a 20 e 60 sedute → **WP3 non
è bloccato**. Fuori perimetro, annotato e non toccato (§0.2): `combine_regimes`
perde la prima barra (il classificatore di vol non ha un rendimento lì);
`assemble` la etichetta `unknown` — corretto, ma è un'asimmetria da conoscere.
## Crescita del repository (risolta in WP1)

Un solo file spiegava il 97,5% del peso (misura WP0, tabella in ADR-032 e in
archivio): `news.parquet` riscritto **integralmente** a ogni run del cron (479
volte dal 2026-05-30), ≈ 26 MB a copia, con costo per run **crescente con la
storia**. **Risolto in WP1** (ADR-033, D8 confermata): storia partizionata per
mese (`news_YYYY-MM.parquet`), il cron riscrive **solo le partizioni toccate**, i
mesi passati diventano blob immutabili. Migrazione one-shot verificata: 50 129
righe, schema/hash per colonna e indice identici, 92 partizioni. La storia git
**non** è stata riscritta: l'1,17 GiB già speso resta, la decisione vale sul futuro.

| Blob riscritto per run del cron | Prima | Dopo | Δ |
|---|---:|---:|---:|
| oggi (24 ago, partizione quasi piena) | 26,66 MB | 6,14 MB | −77,0% |
| media sui prossimi 30 giorni | ~31,4 MB | ~4,0 MB | −87,2% |
| proiezione a 12 mesi (~8 MB/mese) | ~119 MB | ~4 MB | −96,6% |

Il punto non è la percentuale ma la forma: il costo del monolite cresce senza
limite, quello della partizione è **limitato a un mese e si azzera il primo**.

## Blocchi e attese

- **U2 — conferma utente su D4 e D7** (`docs/PIANO_SVILUPPO.md` §2): D8 **risolta**
  (ADR-033 `Accepted`, WP1 chiuso). D4 (target primario) e D7 (soglia di confidenza)
  servono a WP3/WP4 e restano da confermare.
- **U3 — D9 (provider/budget LLM)**: WP6 resta **gated**.
- **U5 — allowlist `api.llama.fi`**: senza, il tab DCA misura *se* esiste un
  meccanismo di cattura del valore, non *quanto* valga. Il client DefiLlama non è
  stato scritto di proposito: codice verso un host irraggiungibile non è
  verificabile e si romperebbe nel cron.
- **U4 — `holdings_units` reali in `config/dca_plan.yaml`**: finché è `{}` la
  posizione è **stimata**; report e JSON lo dichiarano.
- **Sandbox con egress-allowlist**: `fc.yahoo.com`, `api.llama.fi`,
  `api.tokenterminal.com`, `api.dune.com` **bloccati in locale**, funzionanti in CI
  → ogni nuovo modulo di fetch si sviluppa **fixture-first**, validazione live
  delegata al workflow (WP2 ne è il caso: panel validato solo post-merge).
- **WP7 (azioni)** gated su prerequisiti misurabili (piano §5).
- **`category_history` NON partizionato** (annotato da WP1, fuori perimetro): stessa
  dinamica ma 0,3% del totale, e passa dal `write_snapshot` generico di ADR-022,
  condiviso con altri cinque call site. Partizionarlo significa cambiare l'API
  comune: serve una ADR dedicata, non è il "se banale" previsto dal piano.
- **Verifica live di WP1** rinviata al primo run del cron post-merge (osservabile
  solo in Actions; offline è coperta da 14 test).

## Prossime attività

1. **Osservare il primo run del cron `news-history`**: deve riscrivere solo
   `news_2026-08.parquet` (il `git status --porcelain` delle partizioni è ora
   stampato nel log del workflow). È l'unica verifica di WP1 non fattibile offline.
2. **WP3** — walk-forward **con embargo/purging** (`src/backtest/splits.py` oggi
   non ce l'ha), baseline di ranking, calibrazione, risposta onesta a H1–H3.
   Parte dal panel di WP2: `build_etf_dataset` è il suo input riproducibile.
3. **WP4/WP5** — paper portfolio settimanale + prediction ledger, poi le viste
   "Opportunità" e "Modello" in dashboard.
4. **Filler non bloccanti**: WP-T (debito typing su `src/execution/`, poi
   ingestion) e WP-N (lint dei notebook).

## Come far girare tutto

```bash
uv sync --frozen
uv run pytest -q                      # 517 test
uv run ruff check src tests
uv run pyright src/backtest src/features src/models
uv run python -m src.ingestion.tier1.build_etf_dataset   # WP2 (richiede Yahoo: in CI)
```

I notebook richiedono prima `fetch_tier1` (dati gitignored) e si eseguono con
`cd notebooks && PYTHONPATH=.. uv run jupyter nbconvert --execute --inplace <nb>`.

## Dove sta il resto

- **Cronaca 2026-05-28 → oggi**: [`docs/STATUS_ARCHIVIO.md`](./docs/STATUS_ARCHIVIO.md)
  · **Piano dei WP**: [`docs/PIANO_SVILUPPO.md`](./docs/PIANO_SVILUPPO.md)
- **Decisioni**: `DECISIONS.md` (ADR-001 → ADR-033) — **ADR-034/035 riservate** a
  WP3/WP6, non usarle per altro
- **Domande aperte**: `OPEN_QUESTIONS.md` · **Fasi**: `ROADMAP.md`
