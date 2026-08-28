# Report — Ranking ETF probabilistico (WP3)

> Esito della validazione **pre-registrata** in ADR-034. Le ipotesi e le
> soglie sono state committate *prima* di questo run: il timestamp git lo
> dimostra. Nessuna soglia è stata spostata dopo aver visto i numeri.

**Generato**: 2026-08-28T01:02:51.998480+00:00 · **Panel**: 93577 righe · **Feature**: 19 · **Orizzonte primario**: 20 sedute

## Verdetto

- **H1** (IC Spearman del momentum 60g > 0 a 20 sedute): ✅ **vera** — IC = `0.0010` (t = `0.08`)
- **H2** (la logistica batte il momentum in Brier): ❌ **falsa** — logistica `0.2638` vs momentum `0.2510`
- **H3** (spread top-bottom netto costi > 0 in *entrambe* le metà OOS): ❌ **falsa** — modello migliore: `ridge`

> ⚠️ **H1 passa come scritta, ma il numero è rumore.** L'ipotesi
> pre-registrata chiedeva solo `IC > 0`, senza magnitudine: `0.0010`
> con t = `0.08` non è distinguibile da zero. La soglia non viene
> spostata a posteriori — si registra che era formulata debolmente. È la
> barra di adozione, che una magnitudine ce l'ha, a fare il lavoro vero.

### Barra di adozione: ❌ **NON superata**

Richiede IC ≥ 0.03 **e** H3 vera **e** Brier ≤ climatologia. Misurato: IC `0.0308`, Brier `0.2558` vs climatologia `0.2501`.

**Conseguenza operativa** (già scritta in ADR-034 prima del run): WP4
procede con il **momentum semplice** come regola dichiaratamente
*non predittiva*. Il ledger delle previsioni e l'infrastruttura di
portafoglio valgono comunque — servono a misurare, non a guadagnare.

## Orizzonte 20 sedute

| Modello | n | IC Spearman | IC t | Brier | Skill vs clim. | ECE | Hit rate | TMB lordo | TMB netto | TMB > 0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `momentum` | 14950 | 0.0010 | 0.08 | 0.2510 | -0.0049 | 0.0251 | 0.498 | -0.0028 | -0.0052 | 0.46 |
| `logistic` | 14950 | 0.0299 | 2.50 | 0.2638 | -0.0561 | 0.0771 | 0.509 | 0.0032 | 0.0008 | 0.49 |
| `ridge` | 14950 | 0.0308 | 2.57 | 0.2558 | -0.0241 | 0.0511 | 0.516 | 0.0038 | 0.0014 | 0.49 |
| `random` | 14950 | 0.0022 | 0.26 | 0.2506 | -0.0033 | 0.0164 | 0.504 | -0.0000 | -0.0024 | 0.47 |
| `climatology` | 14950 | n/d | n/d | 0.2501 | -0.0011 | 0.0086 | 0.507 | -0.0009 | -0.0033 | 0.45 |

### Le due metà OOS (H3 richiede il segno in entrambe)

| Modello | IC 1ª metà | IC 2ª metà | TMB netto 1ª | TMB netto 2ª |
|---|---:|---:|---:|---:|
| `momentum` | -0.0099 | 0.0119 | -0.0078 | -0.0025 |
| `logistic` | 0.0450 | 0.0148 | 0.0043 | -0.0027 |
| `ridge` | 0.0459 | 0.0157 | 0.0051 | -0.0022 |
| `random` | 0.0070 | -0.0026 | -0.0014 | -0.0034 |
| `climatology` | n/d | n/d | -0.0060 | -0.0006 |

## Orizzonte 60 sedute

| Modello | n | IC Spearman | IC t | Brier | Skill vs clim. | ECE | Hit rate | TMB lordo | TMB netto | TMB > 0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `momentum` | 14950 | -0.0078 | -0.67 | 0.2527 | -0.0123 | 0.0259 | 0.505 | -0.0055 | -0.0079 | 0.48 |
| `logistic` | 14950 | 0.0061 | 0.50 | 0.2794 | -0.1192 | 0.1196 | 0.507 | -0.0014 | -0.0038 | 0.51 |
| `ridge` | 14950 | 0.0050 | 0.41 | 0.2628 | -0.0528 | 0.0877 | 0.506 | -0.0034 | -0.0058 | 0.50 |
| `random` | 14950 | -0.0015 | -0.17 | 0.2516 | -0.0080 | 0.0188 | 0.509 | 0.0004 | -0.0020 | 0.49 |
| `climatology` | 14950 | n/d | n/d | 0.2505 | -0.0037 | 0.0099 | 0.519 | -0.0048 | -0.0072 | 0.45 |

### Le due metà OOS (H3 richiede il segno in entrambe)

| Modello | IC 1ª metà | IC 2ª metà | TMB netto 1ª | TMB netto 2ª |
|---|---:|---:|---:|---:|
| `momentum` | -0.0295 | 0.0139 | -0.0104 | -0.0055 |
| `logistic` | 0.0606 | -0.0485 | 0.0149 | -0.0225 |
| `ridge` | 0.0572 | -0.0471 | 0.0119 | -0.0236 |
| `random` | -0.0072 | 0.0042 | -0.0013 | -0.0026 |
| `climatology` | n/d | n/d | -0.0161 | 0.0018 |

## Reliability table — logistica, 20 sedute

Se le probabilità fossero calibrate, `osservata` ≈ `predetta` in ogni banda.

| Banda | n | Predetta | Osservata | Scarto |
|---|---:|---:|---:|---:|
| 0.00-0.10 | 221 | 0.009 | 0.448 | 0.439 |
| 0.10-0.20 | 110 | 0.130 | 0.591 | 0.461 |
| 0.20-0.30 | 562 | 0.261 | 0.468 | 0.207 |
| 0.30-0.40 | 2316 | 0.364 | 0.462 | 0.098 |
| 0.40-0.50 | 4845 | 0.462 | 0.488 | 0.027 |
| 0.50-0.60 | 5318 | 0.543 | 0.497 | -0.046 |
| 0.60-0.70 | 917 | 0.630 | 0.491 | -0.139 |
| 0.70-0.80 | 116 | 0.719 | 0.491 | -0.228 |
| 0.80-0.90 | 147 | 0.828 | 0.476 | -0.351 |
| 0.90-1.00 | 115 | 0.974 | 0.461 | -0.514 |

## Cosa NON ha funzionato

Sezione obbligatoria (`CLAUDE.md`: gli esperimenti falliti vanno tracciati).

- **20g — logistica sulle feature WP2**: Brier `0.2638` contro `0.2510` del momentum: non lo batte. 19 feature causali non aggiungono potere predittivo rispetto a una regola a costo zero.
- **20g — spread top-bottom**: non positivo in entrambe le metà OOS al netto dei costi. Un segno che regge solo in una metà è un regime, non un edge.
- **60g — momentum relativo 60g**: IC OOS `-0.0078`, non positivo. Coerente con il risultato già noto sui 20 ETF settoriali (STATUS.md): inseguire i settori forti non paga.
- **60g — logistica sulle feature WP2**: Brier `0.2794` contro `0.2527` del momentum: non lo batte. 19 feature causali non aggiungono potere predittivo rispetto a una regola a costo zero.
- **60g — spread top-bottom**: non positivo in entrambe le metà OOS al netto dei costi. Un segno che regge solo in una metà è un regime, non un edge.

### Varianti provate e scartate

- **Ridge sull'excess return** invece della logistica sul segno: stessa famiglia
  di feature, target continuo anziché binario. In tabella come `ridge`.
- **Senza calibrazione isotonic**: la calibrazione non cambia l'ordinamento
  (è monotona), quindi non cambia l'IC; l'effetto è solo sul Brier.
- Nessun tuning iterativo degli iperparametri sullo stesso test set: vietato dal
  piano (§WP3 «non fare»), ed è il modo classico di fabbricare un edge inesistente.

## Protocollo

- Walk-forward su **date** (mai una cross-section spezzata a metà): train 156 settimane, test 52, campionamento **settimanale al lunedì** (D5).
- **Embargo** = orizzonte: le ultime righe di train, il cui target si realizza dentro
  il test, vengono scartate. Senza, il fold è contaminato.
- **Calibrazione isotonic fit solo sul train** di ogni fold.
- **Costi**: `default_cost_model()`, round trip pieno su entrambe le gambe — carico
  pessimistico di proposito, rende H3 più difficile da passare, non più facile.
- **Controlli negativi**: `random` (seed fisso) e `climatology` (frequenza del train).

> ⚠️ Le date consecutive condividono finestre forward sovrapposte: le statistiche t
> riportate sono indicative, non inferenziali — il campione effettivo è più piccolo
> di `n_dates`.

