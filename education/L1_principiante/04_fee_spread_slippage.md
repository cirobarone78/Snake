# L1.04 — Fee, spread, slippage spiegati senza matematica

> Ogni volta che compri o vendi un asset, paghi **tre costi diversi**.
> Uno te lo dichiarano apertamente, gli altri due sono nascosti e
> tipicamente più grossi del primo. Capire i tre separatamente è la
> differenza tra "credere di pagare 0.10%" e pagare in realtà 0.5%
> ogni round-trip.

Nessuna formula. Solo esempi concreti.

## I tre costi

1. **Fee (commissione)** — quello che l'exchange/broker ti addebita
   esplicitamente. È sulla schermata di conferma.
2. **Spread (differenza bid-ask)** — quello che paghi perché compri al
   prezzo "alto" e vendi al prezzo "basso". Mai dichiarato come
   "costo".
3. **Slippage (scivolamento)** — quello che paghi perché tra il momento
   in cui clicchi e il momento in cui l'ordine viene davvero eseguito,
   il prezzo si è mosso (in tuo sfavore, statisticamente).

Tutti e tre si sommano. Il **costo totale** di un'operazione è la somma
dei tre, e va calcolato sia all'andata (compri) sia al ritorno (vendi).

## 1. Fee: il costo dichiarato

### Su exchange crypto

Esempi tipici 2026 (puoi controllare le fee reali su ogni sito):

- **Binance.com**: 0.10% maker, 0.10% taker (più basso se paghi in BNB
  o se hai volumi alti)
- **Coinbase**: ~0.40% taker per retail (era molto peggio fino al 2024)
- **Kraken**: 0.16% maker, 0.26% taker
- **Bitfinex**: 0.10% maker, 0.20% taker

(maker = il tuo ordine resta nel book; taker = il tuo ordine prende
liquidità dal book, vedi L1.02)

Su un'operazione di **1.000 USD** in BTC con fee 0.10% paghi **1 USD**
di fee. Su 10.000 USD ne paghi 10. Lineare con il size.

### Su broker tradizionali

Molto più variabile, in particolare in Europa:

- **Degiro**, **Trade Republic**: spesso 0 commissioni o flat ~1 EUR
  per trade (per ETF e alcune azioni)
- **Fineco**: ~3-19 EUR per eseguito su azioni italiane (a seconda del
  size)
- **Interactive Brokers**: tipicamente <1 USD per trade su grandi
  volumi, con piano "Tiered" che premia chi opera molto

### Il trucco "fee 0%"

Alcuni broker (Robinhood per primo) vendono "commissioni zero". Come si
ripagano? **Allargando lo spread** o vendendo i dati del tuo order flow
a market maker professionali (PFOF — payment for order flow). Risultato
netto per te: paghi meno fee dichiarata, paghi più spread/slippage. Il
totale spesso non cambia, o cambia poco.

**Lezione**: la fee dichiarata da sola non basta a confrontare due
piattaforme. Devi guardare anche le altre due voci.

## 2. Spread: il costo dell'incrocio

In ogni momento il mercato ha:
- un **best bid**: il prezzo più alto a cui qualcuno è disposto a
  comprare
- un **best ask**: il prezzo più basso a cui qualcuno è disposto a
  vendere

Per definizione **ask > bid**. La differenza si chiama **spread**.

### Esempio su BTC

In un momento normale:
- BTC bid: 75.000 USD
- BTC ask: 75.020 USD
- Spread: 20 USD (0.027%)

Se compri **subito** (market order) prendi a 75.020. Se vendi subito,
ricevi 75.000. Il round-trip immediato — compri e rivendi nello stesso
istante senza che il prezzo si muova — ti costa **20 USD su 75.000**
(0.027%). Apparentemente piccolo, ma è puro costo.

### Esempio su un'altcoin illiquida

Asset poco scambiato, market cap 30 milioni USD:
- bid: 0.485
- ask: 0.512
- Spread: 0.027 (5.5%!)

Compri a 0.512, rivendi a 0.485 → **perdi il 5.5%** solo per
attraversare lo spread. Su asset illiquidi lo spread può facilmente
diventare il costo dominante, molto più grosso di qualsiasi fee.

### Cosa lo influenza

- **Liquidità**: più ordini ci sono nel book vicino al mid, più stretto
  è lo spread
- **Orario**: di notte (per gli orari del mercato di riferimento) lo
  spread si allarga
- **Volatilità**: durante shock o annunci, lo spread esplode (i market
  maker si proteggono)
- **Evento**: pochi minuti prima/dopo un evento (release CPI, decisione
  Fed) gli spread si allargano

### Lo spread è "fee invisibile"

Quando il tuo broker pubblicizza "zero commissioni", spesso recupera
allargando lo spread sul prezzo che ti mostra. Non lo vedi nella
ricevuta: vedi solo il prezzo di esecuzione, che sembra "il prezzo di
mercato". Per controllare, confronta il prezzo che ti propongono con
quello di un altro venue indipendente nello stesso secondo.

## 3. Slippage: il costo del movimento del prezzo

Lo **slippage** è la differenza tra il prezzo che vedi quando clicchi
e il prezzo a cui sei effettivamente eseguito.

### Perché esiste

Tra il click e l'esecuzione passano millisecondi (a volte secondi).
Il book si muove. Anche solo l'arrivo del tuo ordine sposta il book:
se ordini grosso, "mangi" più livelli, e finisci per pagare un prezzo
medio peggiore.

### Esempio su BTC, ordine piccolo

Ordini un **market buy di 1 BTC**. Best ask al momento del click:
75.020. Il book ha 5 BTC disponibili a 75.020. Il tuo ordine prende 1
BTC a 75.020. Slippage: praticamente zero.

### Esempio su BTC, ordine grosso

Ordini un **market buy di 100 BTC**. Il book sopra il mid ha:
- 5 BTC a 75.020
- 8 BTC a 75.025
- 12 BTC a 75.030
- ... e così via, salendo

Il tuo ordine consuma il book a partire dal livello più basso e
"risale" finché non ha riempito 100 BTC. Prezzo medio finale: magari
75.080 invece di 75.020. **Slippage: 60 USD per BTC**, ~0.08% del
trade.

### Esempio su un'altcoin illiquida, ordine medio

Stesso ordine di 5.000 USD su una small-cap col book sottile:
- 200 unità a 0.512
- 100 unità a 0.520
- 50 unità a 0.535
- 1.000 unità a 0.580

Il tuo ordine da 5.000 USD compra "scalando" il book e arriva fino a
0.580. Prezzo medio pagato: magari 0.555 contro un mid di 0.500.
**Slippage: 11%** solo per entrare. E quando vorrai uscire, il problema
si ripete in senso opposto.

### Slippage diventa "tassa nascosta" su strategie attive

Una strategia che entra/esce dal mercato 100 volte all'anno con
slippage medio di 0.1% paga **10% all'anno** solo di slippage. Una
strategia con segnale che sulla carta rende 8% all'anno, in realtà
**perde 2%** dopo i costi.

## Round-trip: il costo che conta davvero

Quasi sempre quello che conta non è "quanto paghi per comprare", ma
quanto paghi **per entrare e uscire** (round-trip), perché è quello che
mangia il tuo P&L.

Esempio realistico su BTC, exchange Binance:

| Voce | Andata | Ritorno | Totale |
|---|---|---|---|
| Fee (taker 0.10%) | 0.10% | 0.10% | **0.20%** |
| Spread (mid → ask all'andata, mid → bid al ritorno) | 0.013% | 0.013% | **0.026%** |
| Slippage (ordine piccolo) | ~0% | ~0% | **~0%** |
| **Totale round-trip** | | | **~0.23%** |

Su BTC con un ordine piccolo, il round-trip costa ~0.23%. Significa che
il tuo segnale deve fare **almeno +0.23%** netto per essere break-even.

Stessa tabella per un'altcoin illiquida, ordine medio:

| Voce | Totale |
|---|---|
| Fee | 0.20% |
| Spread | ~5% |
| Slippage | ~10% |
| **Round-trip** | **~15%** |

Su questa altcoin, qualsiasi segnale che non promette almeno +15% è
una perdita garantita. Per questo, in pratica, le strategie quant
serie evitano gli asset illiquidi: il costo strutturale è troppo alto.

## Collegamento al nostro progetto

Tutto questo capitolo è il **prerequisito mentale** per ADR-013
(modello di slippage) che useremo quando faremo paper trading
(Fase 6+). Nello specifico:

- **Fee**: ADR-012 (exchange di riferimento per fee) fissa i parametri.
  Useremo le fee maker/taker del nostro venue scelto come costanti
  nel modello
- **Spread**: catturato implicitamente dal modello market vs limit del
  paper trader. Un market order "attraversa" il book secondo regole
  esplicite
- **Slippage**: ADR-013 sceglie un modello realistico, probabilmente
  "size-aware" (più grosso è l'ordine in % di volume giornaliero, più
  slippage applichiamo)

Senza modello dei costi, ogni backtest mente di una percentuale che
**spesso decide se la strategia è verde o rossa**. Per questo VISION.md
sottolinea il rigore metodologico.

Per i dati raw che abbiamo già scaricato:
- I parquet Yahoo, Binance, CoinGecko contengono solo `close` (o
  OHLC) e `volume`. **Non** contengono bid/ask, quindi lo spread va
  modellato (es. stimato come % del close per asset class) o assunto
  costante
- Il `volume` ci serve per stimare lo slippage size-aware: ordine
  piccolo rispetto al volume giornaliero → slippage trascurabile;
  ordine grosso → slippage non trascurabile

## Glossario rapido

- **Fee**: commissione dichiarata, % o fissa, applicata dall'exchange
- **Bid**: miglior offerta di acquisto presente nel book
- **Ask**: miglior offerta di vendita presente nel book
- **Spread**: differenza ask − bid. Costo implicito di attraversare il
  book
- **Mid**: (bid + ask) / 2. Il "prezzo intermedio" teorico
- **Slippage**: differenza tra prezzo atteso (al click) e prezzo
  effettivo (esecuzione). Cresce con il size dell'ordine e
  l'illiquidità
- **Liquidità**: quanto book c'è ai prezzi vicini al mid. Più alta è la
  liquidità, meno paghi spread+slippage
- **Round-trip cost**: somma di fee + spread + slippage moltiplicata
  per 2 (entri e esci). La metrica vera del costo
- **PFOF** (payment for order flow): la pratica per cui un broker
  vende i tuoi ordini a market maker, in cambio di poter offrirti
  "fee zero". Spesso paghi comunque, via spread

## Cosa portare via

- **La fee dichiarata è solo il 30-40% del costo vero** per la maggior
  parte delle operazioni retail. Le altre due voci (spread, slippage)
  sono spesso più grosse, ma le vedi solo se ti metti a misurarle
- **Spread esplode su asset illiquidi**: 5%, 10% non sono assurdi. Per
  questo i quant seri non operano su small-cap
- **Slippage cresce non-linearmente col size dell'ordine**. Raddoppiare
  l'ordine non raddoppia lo slippage: lo aumenta più che
  proporzionalmente quando il book è sottile
- **Il break-even di una strategia** non è zero. È **round-trip-cost
  per ogni trade**. Una strategia che fa 50 trade/anno con costo
  round-trip 0.5% deve fare almeno **+25%/anno lordo** solo per non
  perdere
- "Zero commissioni" non significa "zero costi". Significa solo "una
  voce nascosta al posto di una visibile"

---

*Prossimo capitolo*: L1.05 — Portafoglio e diversificazione.
