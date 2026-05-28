# VISION.md

> Il "perché" del progetto. Cambia raramente. Riallineare qui quando ci si perde.

## Obiettivo

Costruire un sistema sperimentale in grado di **analizzare in modo integrato e
multifattoriale** i mercati finanziari (con focus particolare sulle criptovalute)
per identificare **segnali probabilistici** sul possibile andamento di asset
selezionati e di indici/aggregati di mercato.

Le fonti di analisi spaziano oltre i puri dati di prezzo:

- Dati di mercato e on-chain
- Indicatori tecnici e cicli (es. halving Bitcoin, stagionalità)
- Contesto macroeconomico (tassi, inflazione, dollaro, yield)
- Sentiment estratto da notizie di **economia/finanza, tecnologia, politica,
  affari esteri** e dai social
- Identificazione di **regimi di mercato** (bull/bear/sideways) e cambi di regime

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

## Stato finale immaginato

Idealmente, alla fine del progetto, esiste:

- Un repository di codice riproducibile
- Una pipeline che ingerisce dati eterogenei e li allinea temporalmente
- Un set di modelli, dal più semplice al più complesso, con report comparativi
- Una **dashboard** o report periodico che, dato lo stato attuale dei mercati e
  delle notizie, riassume i segnali emersi e la loro confidenza storica
- Un diario delle ipotesi testate, riuscite e fallite
