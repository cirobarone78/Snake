# VISION.md

> Il "perché" del progetto. Cambia raramente. Riallineare qui quando ci si perde.

## Obiettivo

Costruire un sistema sperimentale in grado di **analizzare in modo integrato e
multifattoriale** i mercati finanziari per identificare **segnali probabilistici**
sul possibile andamento di asset selezionati e di indici/aggregati di mercato,
e validare questi segnali tramite **paper trading realistico** prima di
qualsiasi considerazione di uso reale.

**Ambito iniziale**: criptovalute (focus su BTC, ETH, SOL, LINK, POL + top 20).
**Ambito esteso (futuro)**: mercato azionario tradizionale (equity, ETF, indici).
L'architettura è già pensata asset-class-agnostic — vedi ADR-014.

Le fonti di analisi spaziano oltre i puri dati di prezzo:

- Dati di mercato e on-chain
- Indicatori tecnici e cicli (es. halving Bitcoin, stagionalità)
- Contesto macroeconomico (tassi, inflazione, dollaro, yield)
- Sentiment estratto da notizie di **economia/finanza, tecnologia, politica,
  affari esteri** e dai social
- Identificazione di **regimi di mercato** (bull/bear/sideways) e cambi di regime

In parallelo, il progetto include un **modulo didattico multi-livello**
(principiante → intermedio → avanzato → esperto) per costruire e mantenere
la padronanza dei concetti su cui il sistema si basa. Vedi ADR-015.

## Mission

> *Trovare segnali deboli ma reali nell'intersezione di dati eterogenei,
> rifiutando il rumore travestito da pattern.*

## Obiettivi misurabili (criteri di successo)

Il progetto si considera **un successo metodologico** (indipendentemente dalla
profittabilità) se a fine ricerca avremo:

1. Un dataset multifattoriale pulito, riproducibile, documentato
2. Un framework di backtesting **rigoroso** (walk-forward, no look-ahead, costi inclusi)
3. Almeno un modello baseline e uno multifattoriale, con metriche out-of-sample
   onestamente riportate
4. Documentazione di **cosa funziona** e **cosa non funziona** (entrambi preziosi)
5. Capacità di rispondere alla domanda: *"data una settimana di notizie e dati
   di mercato, quali segnali emergono e con quale confidenza?"*

Il progetto è un **successo predittivo** se, in test out-of-sample su periodo
significativo, batte un benchmark passivo (buy-and-hold) o un benchmark naïve
(random walk / momentum semplice) con Sharpe ratio aggiustato per i costi.

## Non-goals (cosa il progetto NON è)

- **Non** è un trading bot automatizzato (almeno non nelle prime fasi)
- **Non** è un servizio commerciale o financial advice
- **Non** è high-frequency trading
- **Non** è un sistema che promette profitti
- **Non** è arbitraggio o market making
- **Non** sostituisce il giudizio umano: produce input, non decisioni

## Principi guida

1. **Rigore prima di tutto**: meglio nessun segnale che un segnale falso convincente
2. **Riproducibilità**: ogni risultato deve essere ricreabile da chi legge il codice
3. **Documenta i fallimenti**: gli approcci che non funzionano sono dati preziosi
4. **Diffida dei backtest brillanti**: di solito è overfitting
5. **Honest reporting**: metriche out-of-sample, non in-sample
6. **Costo zero finché possibile**: API gratuite prima di pagare per dati premium
7. **Scope incrementale**: 1 asset, 1 timeframe, 1 fonte → poi espandere
8. **Selettività e qualità prima del volume**: acquisiamo poche fonti ben
   integrate, non molte mal correlate. L'80% del segnale viene dal 20% delle
   fonti. Ogni nuova fonte deve giustificare il proprio inserimento con
   un'analisi di **potere incrementale**: riduce il rumore? aggiunge segnale
   ortogonale? o duplica qualcosa che già abbiamo? Vedi ADR-017
9. **L'AI è filtro e sintetizzatore, non oracolo**: l'AI (LLM, modelli NLP)
   serve a classificare, estrarre, riassumere informazione testuale.
   Non genera segnali predittivi: quelli vengono dai modelli quantitativi
   sui dati strutturati. Vedi ADR-016

## Stato finale immaginato

Idealmente, alla fine del progetto, esiste:

- Un repository di codice riproducibile
- Una pipeline che ingerisce dati eterogenei (mercato, on-chain, macro, news)
  e li allinea temporalmente
- Un set di modelli predittivi per asset × orizzonte (breve/medio/lungo),
  dal più semplice al più complesso, con report comparativi out-of-sample
- Un **paper trading engine** che simula con realismo guadagni e perdite su
  scenari multipli (capitali diversi, broker diversi: Binance e Kraken),
  con storico auditabile e possibilità di reset
- Una **dashboard** o report periodico che, dato lo stato attuale dei mercati,
  riassume i segnali emersi, la loro confidenza storica e lo stato del paper
  portfolio
- Un **modulo didattico** in italiano, su 4 livelli, che spiega il mercato e
  i concetti usati dal sistema con esempi sui dati reali del progetto
- Un diario delle ipotesi testate, riuscite e fallite
- (Estensione futura) Stesso sistema esteso al mercato azionario tradizionale
