# STATUS.md

> **Fotografia dello stato corrente.** Non è un diario: la cronaca delle
> sessioni passate vive in [`docs/STATUS_ARCHIVIO.md`](./docs/STATUS_ARCHIVIO.md).
> Chi riprende il lavoro (umano o agente) legge questo file per primo, e tiene
> questo file **sotto le 200 righe**: se cresce, la cronaca si sposta in archivio.

**Ultimo aggiornamento**: 2026-08-28 — piano di accumulo: NEAR quarta gamba fissa (ADR-037); verificato il fix byte-stability del cron news (#59)

---

## Dove siamo

- **Branch di lavoro**: `claude/wp5-dashboard-9vll2i` — base `main` con PR #52,
  WP0, **WP1** (#55/#59), **WP2** (#56), **WP3** (#58) e **WP4** (#60) mergiati.
- **Test**: 661 passati (`uv run pytest -q`), ruff pulito, pyright pulito sui
  moduli core, su `src/execution` e su `src/ingestion/news`.
- **Milestone corrente**: **Fase 9 — Ranking ETF probabilistico**; WP0→WP4
  chiusi, **WP5 implementato** (sotto). Restano solo i WP gated (WP6 su D9, WP7
  sui prerequisiti) e i filler WP-T/WP-N. Il piano operativo è
  [`docs/PIANO_SVILUPPO.md`](./docs/PIANO_SVILUPPO.md): è il riferimento per tutti
  i WP successivi, con decisioni pre-registrate D1–D12 e ipotesi H1–H3 scritte
  **prima** di qualunque backtest.
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
| `etf-dataset.yml` | solo manuale | 🟢 **primo run verde** (21/21 ticker, 93 517 righe) |
| `ranking-backtest.yml` | su push ai modelli | 🟢 attivo (WP3): ricostruisce il panel e rigenera il report |
| `etf-ranking.yml` | lunedì 07:00 UTC | ⏳ **nuovo (WP4)**: primo run da lanciare a mano (`workflow_dispatch`) |

I cron committano con `[skip ci]`. GitHub schedula con **ritardo variabile** (un
cron delle 07:00 può girare alle 12:36 UTC): fidarsi del timestamp nel report.

## Risultati empirici consolidati

Elenco di ciò che è stato **misurato**, non di ciò che si spera. Gli esiti
negativi contano quanto i positivi e restano qui apposta.

- **Nessun edge di ranking cross-sectional sugli ETF settoriali** (WP3, ADR-034,
  validazione **pre-registrata**: ipotesi committate prima del codice che le
  misura). Walk-forward con embargo, 14 950 previsioni OOS per modello.
  **Barra di adozione NON superata.** In breve — dettaglio in ADR-034 e in
  [`docs/REPORT_RANKING.md`](./docs/REPORT_RANKING.md):
  - il **momentum relativo 60g è indistinguibile dal caso**: IC Spearman `0,0010`
    (t = 0,08) contro `0,0022` del ranker casuale. H1 passa solo perché scritta
    come `IC > 0` senza magnitudine — *un'ipotesi senza magnitudine è quasi
    gratis da superare*, lezione registrata;
  - logistica e ridge mostrano IC ≈ `0,03` (t ≈ 2,5), l'unica cosa non-casuale del
    run, ma **positiva nella prima metà OOS e svanita o invertita nella seconda**;
  - **le probabilità sono peggio di una costante**: il Brier di *tutti* i modelli
    supera la climatologia (0,2501); dove la logistica predice **0,974** si
    realizza **0,461**. La calibrazione isotonic non trasferisce OOS;
  - **i costi mangiano il resto**: TMB lordo `ridge` +0,0038 → netto +0,0014;
  - conferma su base probabilistica del risultato descrittivo già noto: **non
    inseguire i settori più forti**. **Conseguenza**: WP4 procede col momentum
    semplice dichiarato non-predittivo, come §2.1 prescriveva.
- **Battere SPY è più difficile di quanto sembri.** Sul panel WP2 (2005→2026)
  l'outperformance **incondizionata** vs SPY è **0,489 a 20 sedute** (n=93 117) e
  **0,482 a 60**: il settore mediano batte SPY meno di una volta su due — nel
  periodo l'S&P cap-weighted è stato trainato dalle mega-cap. È la **baseline
  climatologica** che H2 doveva battere, piantata *prima* di modellare.

- **Nessun edge direzionale daily.** Modelli tecnici e tecnico+macro su BTC in
  walk-forward OOS: accuracy 0.5007 → 0.5060 (n=2249) — dentro il rumore. La
  macro **non** aggiunge potere predittivo a frequenza daily (il segnale CPI vive
  a frequenza mensile). Nessun leakage: un bug avrebbe gonfiato il delta.
- **Il sentiment news (VADER, Layer 1) non anticipa nulla** con i dati attuali:
  `corr(news_count, |return|) = +0.32` su n=23 è **svanito a n=143** (≈ −0.07 a
  lag 1). Artefatto di piccolo campione, e caso di studio permanente su quanto
  costa concludere presto.
- **È il regime a condizionare, non il momentum.** Forward più alti dopo
  `bear_high_vol` (21g +3%, 63g +7%); il pericolo è `bear_low_vol`. Il rendimento
  BTC è fortemente regime-dipendente (Sharpe `bull_high_vol` **+2.97** vs
  `bear_high_vol` **−1.20**): **la media full-sample mescola mondi opposti**.
  Conoscere il regime però **non** predice: accuracy 0.498 → 0.510, nel rumore.
- **La fase di ciclo crypto (halving) condiziona forte** — forward 126g: early
  mediana +23% (hit 0.64), late +18% (hit 0.66), **mid −29% (hit 0.21)**; "mid =
  zona pericolo" è OOS-stabile in direzione. ⚠️ **Descrittivo, non un edge
  provato**: ~1,5–2 cicli = essenzialmente 2 bear (2018, 2022).
- **Piano di accumulo (ADR-030)**: "compra ciò che è più sotto peso" non ha edge
  di **rendimento** (54,5° percentile su 200 semi casuali) ma ha un effetto
  **reale e OOS-stabile sull'allocazione** (distanza dal target 5,3 pp vs 30,5 pp
  nella metà OOS). Il momentum come regola di scelta è la peggiore (40,5°,
  *sotto* il caso); "buy-the-dip" era 96° in-sample e **ultima OOS** → rimossa.
- **Piano reale (ADR-037, 2026-08-28)**: budget a **110€/mese** — NEAR aggiunto
  come quarta gamba fissa da 10€ (prima tra le candidate dello screener
  fondamentale, tutti i criteri verdi). Non entra nella rotazione satellite;
  `holdings_units.NEAR` resta 0 fino al primo acquisto reale.
- **Fondamentali dei progetti (ADR-031)**: descrivono, non predicono; nessun
  backtest onesto è possibile (storia corta, piena di sopravvissuti). Tre trappole
  codificate: sconosciuto ≠ zero; la tesi monetaria (BTC) è esente dall'asse
  "cattura del valore"; zero commit ≠ progetto morto.
- **Lo screen delle candidate è survivorship-biased per costruzione**, non
  risolvibile con questi dati: la classifica di oggi contiene solo i sopravvissuti.
  Dichiarato nel modulo, nel report e nel tab.

## Fase 9 — WP2: dataset ETF point-in-time (fatto)

Il panel su cui WP3 ha addestrato le baseline e su cui WP4 decide ogni settimana:
`SPY` nel registry (benchmark D2), `src/features/etf_dataset.py` (19 feature
causali, target excess return 20/60 sedute vs SPY, regime 4-stati), CLI
`build_etf_dataset`, 24 test offline — il più importante è quello di **causalità**.
Validato live: 21/21 ticker, **93 517 righe × 27 colonne**, 2005-01-03 →
2026-08-24, date di quotazione dove attese, missing solo da warm-up. Dettaglio in
[`docs/STATUS_ARCHIVIO.md`](./docs/STATUS_ARCHIVIO.md).

**Da sapere**: `pyright: strict` puro non è raggiungibile su un modulo
pandas-heavy (`pandas` non ha `py.typed`); i moduli nuovi sono strict **meno le
quattro regole** che ne derivano. Per lo strict pieno servirebbe `pandas-stubs`
come dip. dev — da ADR, non da WP.

## Fase 9 — WP4: paper portfolio settimanale + prediction ledger (fatto)

Il primo pezzo di infrastruttura che produce un **track record forward**, su una
regola dichiarata non predittiva — quella che la barra di WP3 ha lasciato in piedi.

- **Ledger** (`src/execution/prediction_ledger.py`): JSONL append-only in
  `data/predictions/etf_ranking.jsonl` (versionato, una riga per previsione).
  Scritta **prima** che l'esito esista; l'unico campo che può cambiare dopo è
  `outcome`, una volta sola, quando l'orizzonte è maturato su *entrambe* le gambe
  (asset e benchmark). Il backfill riscrive dai dict grezzi e un test verifica che
  nulla tranne `outcome` sia cambiato. Identità rafforzata rispetto al piano: un
  duplicato è rifiutato anche su `(data_cutoff, asset, horizon)`, così un retry
  del cron non lascia due righe sulla stessa barra fra cui scegliere.
- **Niente probabilità non calibrate** (ADR-036): i tre campi di previsione
  restano nel contratto ma un validatore pydantic **rifiuta** un valore non nullo
  quando `predictive` è `false`, e `confidence` vale `not_applicable`. Al loro
  posto: `selection_score`, `selection_rank`, `realized_vol_60` — stato osservato,
  con nomi che lo dicono.
- **Regola** (`etf_rotation.py`): top 5 per `rel_ret_60`, equal weight, cap 20%.
  **Soglia D7 disattivata** (ADR-036): gatta su una probabilità calibrata, che non
  esiste; sul rank percentile non scatterebbe mai (il 5° di 20 sta a 0,80 ogni
  settimana), sarebbe un filtro finto. Il meccanismo resta testato per il giorno in
  cui un modello passerà la barra.
- **Payload + workflow**: `ranking_report.json` e `ranking_model.json` dichiarano
  `predictive: false`, la regola per esteso e il verdetto ADR-034; i campi di
  previsione escono `null`. Fail-safe: feed stale o validazione più vecchia di
  6 mesi ⇒ `status: "stale"`, nessuna riga di ledger e **nessun ribilanciamento**.

**Da sapere**: il portafoglio è **sempre investito** quando ci sono 5 storie
utilizzabili — è una rotazione *relativa* contro SPY, non un market-timer. Se
batterà SPY, **la prima ipotesi da falsificare è la fortuna**: la regola è già
stata misurata come indistinguibile dal caso.

**Validazione live: ancora da fare.** In sandbox Yahoo è bloccato, quindi il
percorso felice è coperto solo dai test end-to-end offline (feed stub); il
fail-safe invece è stato eseguito davvero (fetch fallito ⇒ payload `stale`, zero
righe, zero ordini). **Il primo run vero va lanciato a mano** su `etf-ranking`.

## Fase 9 — WP5: viste "Opportunità" e "Modello" (fatto)

La dashboard ora dice, in italiano e senza scorciatoie, ciò che WP3 ha misurato.

- **"Opportunità"** (nuovo tab, `public/index.html` + `app.js` + `styles.css`):
  tabella ordinabile su tutte le colonne, righe espandibili. **Nessuna colonna di
  probabilità** — i campi sono `null` per contratto (ADR-036), quindi la
  classifica è per `selection_score`/`selection_rank` (momentum relativo a 60
  sedute) ed è etichettata **classifica descrittiva** ovunque. Il banner di
  non-predittività (`non_predictive_notice` + `non_predictive_reason`) sta nel
  flusso della pagina sopra la tabella, **non** in un tooltip: un test lo verifica.
- **Riga espansa**: "probabilità stimata / rendimento atteso / volatilità attesa =
  non disponibile" *dichiarato*, non omesso, con il perché; stato osservato
  (momentum, percentile, vol 60g, prezzo, regime, età del dato, peso), fattori,
  esiti già risolti di quell'ETF dal ledger, tre caveat.
- **"Modello"** (stessa vista, sotto la tabella): verdetto ADR-034 **testuale**
  (requisito vs esito), calibrazione non disponibile con la ragione, periodo e
  finestra di addestramento, metriche OOS per modello con IC per metà, Brier e Δ
  vs climatologia, e la **reliability table + grafico SVG**: la banda in cui la
  logistica stimava **0,97** e l'evento si verificava **0,46** è evidenziata ed è
  il motivo, scritto, per cui la dashboard non pubblica probabilità.
- **Stati**: `status: "stale"` ⇒ banner "dati non aggiornati, nessun nuovo ranking
  emesso" con la ragione; payload assente ⇒ empty state, **nessun crash**
  (verificato con i payload intercettati a 404: zero errori JS).
- **Verifica visiva**: Playwright/Chromium in tema chiaro, scuro e mobile 390px;
  screenshot in `docs/screenshots/wp5/` e nella PR. Ordinamento, espansione da
  tastiera e i selettori orizzonte/modello provati in un run interattivo.

**Bug reale trovato dalla dashboard (fuori perimetro, ma bloccante)**:
`public/data/ranking_backtest.json` conteneva **18 token `NaN`** — l'IC di
Spearman della climatologia è indefinito (un ranker costante non ha varianza).
`json.dumps` li scrive come `NaN`, che Python rilegge ma **non è JSON valido**:
`JSON.parse` lanciava e l'intera vista "Modello" restava vuota, senza errore
visibile. Corretto alla sorgente in `src/features/report_json.py` (`json_safe` +
`allow_nan=False`, cioè la regola che il docstring del modulo prometteva già:
«un campo NaN è `null`»), artefatto riscritto col writer corretto (18 righe
`NaN` → `null`, nient'altro) e due test: uno sul writer, uno che rifiuta
costanti non finite in *tutti* i payload committati.

**Fuori perimetro, annotato e non fatto**: il piano chiedeva anche la
"distribuzione storica in condizioni simili" da `conditional_outcomes` nella riga
espansa. Quel dato **non esiste nel contratto di WP4** (`rotation_report.py` non
lo produce) e aggiungerlo significherebbe estendere il payload e rigenerarlo:
sarebbe un WP4-bis. La riga espansa mostra quindi lo stato osservato e gli esiti
del ledger; la frequenza di base storica (0,489 a 20 sedute) resta scritta nei
caveat come numero, non come distribuzione.

## Crescita del repository (risolta in WP1)

`news.parquet` era riscritto **integralmente** a ogni run del cron (≈ 26 MB a
copia, 479 volte): costo per run crescente, cioè crescita quadratica. Risolto in
WP1 (ADR-033): partizionamento mensile + **ordine di scrittura deterministico**
`(published, item_id)` — senza il secondo, il primo non risparmiava nulla
(−0,4% misurato). Oggi: −76,6% per run con volume di news reale, e soprattutto un
costo **limitato a un mese** che si azzera ogni primo del mese. La storia git non
è stata riscritta: l'1,17 GiB già speso resta. Misure e tabella completa in
[`docs/STATUS_ARCHIVIO.md`](./docs/STATUS_ARCHIVIO.md).

> Lezione trasferibile: un'ottimizzazione che si appoggia alla deduplicazione dei
> contenuti richiede una **serializzazione deterministica**, e non si vede dal
> codice — i 14 test iniziali confrontavano i byte solo su input identici.

## Blocchi e attese

- **U2 — D4 resta da confermare** (`docs/PIANO_SVILUPPO.md` §2): D8 **risolta**
  (ADR-033), **D7 risolta** (ADR-036: disattivata, non è applicabile senza una
  probabilità calibrata). **D4** (target primario) è servita a WP3 ed è rilevante
  solo per una futura ri-validazione, non per il fallback di WP4.
- **U3 — D9 (provider/budget LLM)**: WP6 resta **gated**.
- **U5 — allowlist `api.llama.fi`**: senza, il tab DCA misura *se* esiste un
  meccanismo di cattura del valore, non *quanto* valga. Il client DefiLlama non è
  stato scritto di proposito: codice verso un host irraggiungibile si romperebbe
  nel cron.
- **U4 — `holdings_units` reali in `config/dca_plan.yaml`**: finché è `{}` la
  posizione è **stimata**; report e JSON lo dichiarano.
- **Sandbox con egress-allowlist**: `fc.yahoo.com`, `api.llama.fi`,
  `api.tokenterminal.com`, `api.dune.com` **bloccati in locale**, funzionanti in CI
  → ogni nuovo modulo di fetch si sviluppa **fixture-first**, validazione live
  delegata al workflow. WP2, WP3 e WP4 ne sono i casi.
- **WP7 (azioni)** gated su prerequisiti misurabili (piano §5).
- **Questo file è sopra il tetto di 200 righe** che si è dato in WP0 (WP5 ne ha
  aggiunte ~45). In WP4 sono già state spostate in archivio la narrativa della
  crescita repo e la validazione live di WP2 (−50 righe), ma WP3, WP4 e WP5
  hanno aggiunto risultati veri.
  Il prossimo giro di compressione tocca a "Risultati empirici consolidati": le
  voci pre-Fase 9 (sentiment, cicli, DCA, fondamentali) sono tutte già in ADR e
  report, e possono diventare una riga con link. **Non** si comprimono cancellando
  esiti negativi: restano qui apposta.
- **`category_history` NON partizionato** (annotato da WP1, fuori perimetro):
  stessa dinamica ma 0,3% del totale, e passa dal `write_snapshot` generico di
  ADR-022, condiviso con altri cinque call site: serve una ADR dedicata.

## Prossime attività

1. **Primo run di `etf-ranking`** a mano (`workflow_dispatch`): è l'unica verifica
   di WP4 non fattibile offline (Yahoo bloccato in sandbox). Attese: 20 righe ×2
   orizzonti nel ledger, 5 ordini pendenti nello scenario `etf_top5`, payload con
   `status: "ok"`. Un `status: "stale"` al primo colpo va letto come guasto del
   feed, non come bug della regola.
2. **Rivedere le viste WP5 con dati veri**: oggi la classifica gira sul payload
   del primo run e il ledger non ha ancora esiti risolti, quindi "Esiti delle
   classifiche già emesse" e lo scoreboard forward sono vuoti per costruzione.
   Vanno riguardati dopo ~4 settimane di run, quando le prime righe a 20 sedute
   si chiudono.
3. **Osservare il primo run del cron `news-history`**: deve riscrivere solo
   `news_2026-08.parquet`. È l'unica verifica di WP1 non fattibile offline.
4. **Filler non bloccanti**: WP-T (debito typing su `src/ingestion/`) e WP-N
   (lint dei notebook).

## Come far girare tutto

```bash
uv sync --frozen
uv run pytest -q                      # 661 test
uv run ruff check src tests
uv run pyright src/backtest src/features src/models src/execution
uv run python -m src.ingestion.tier1.build_etf_dataset     # panel WP2 (Yahoo: gira in CI)
uv run python -m src.ingestion.tier1.ranking_backtest_cli  # validazione WP3
uv run python -m src.ingestion.tier1.etf_ranking_cli       # rotazione WP4 (Yahoo: gira in CI)
```

I notebook richiedono prima `fetch_tier1` (dati gitignored) e si eseguono con
`cd notebooks && PYTHONPATH=.. uv run jupyter nbconvert --execute --inplace <nb>`.

## Dove sta il resto

- **Cronaca 2026-05-28 → oggi**: [`docs/STATUS_ARCHIVIO.md`](./docs/STATUS_ARCHIVIO.md)
  · **Piano dei WP**: [`docs/PIANO_SVILUPPO.md`](./docs/PIANO_SVILUPPO.md)
- **Decisioni**: `DECISIONS.md` (ADR-001 → **ADR-036**) — **ADR-035 resta
  riservata** a WP6, non usarla per altro: WP4 ha preso il numero successivo
- **Domande aperte**: `OPEN_QUESTIONS.md` · **Fasi**: `ROADMAP.md`
