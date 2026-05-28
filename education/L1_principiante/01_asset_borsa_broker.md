# L1.01 — Cos'è un asset, una borsa, un broker

> Tre parole che si usano spesso senza capirsi. Le sciogliamo una alla volta,
> e mostriamo come si combinano.

## 1. Asset

Un **asset** è qualcosa che ha valore e che può essere posseduto, comprato
o venduto. Esempi:

- **Azione** di un'azienda (es. Apple): rappresenta una piccola frazione di
  proprietà dell'azienda. Se Apple guadagna, parte di quei guadagni può
  essere distribuita agli azionisti (dividendi).
- **Obbligazione**: un prestito che fai a uno Stato o a un'azienda, che in
  cambio ti restituisce capitale + interessi a scadenza.
- **Criptovaluta**: un'unità digitale gestita da una blockchain. Bitcoin
  ed Ethereum sono criptovalute. Funzionano senza una banca centrale che
  le emetta.
- **ETF**: un "contenitore" che a sua volta contiene molti asset (es. un
  ETF sull'S&P 500 contiene azioni delle 500 maggiori aziende USA).
- **Materie prime**: oro, petrolio, grano. Tipicamente si scambiano via
  futures (contratti) più che fisicamente.
- **Valuta**: euro, dollaro, yen. Il **forex** è il mercato dove le valute
  si scambiano tra loro.

Per il nostro progetto gli asset principali sono criptovalute (BTC, ETH, SOL,
LINK, POL), con qualche indice tradizionale come **contesto** (S&P 500,
NASDAQ, DXY, oro).

### Cosa hanno in comune

Tutti gli asset hanno un **prezzo** che cambia nel tempo. Il prezzo riflette
quello che, in quel preciso istante, qualcuno è disposto a pagare per averlo
e qualcun altro è disposto ad accettare per cederlo. Non c'è un "prezzo
giusto" oggettivo: c'è solo l'incontro tra domanda e offerta.

### Cosa li distingue

- **Liquidità**: quanto è facile comprarlo/venderlo senza spostare il prezzo.
  Bitcoin è molto liquido, una microcap altcoin no.
- **Volatilità**: quanto oscilla il prezzo. Le crypto sono **molto** più
  volatili delle azioni blue-chip.
- **Orari**: le borse tradizionali aprono e chiudono (9:00–17:30 a Milano,
  9:30–16:00 a New York); il mercato crypto è aperto 24/7.
- **Regolamentazione**: le azioni sono regolate da autorità (Consob in
  Italia, SEC negli USA); le crypto in molte giurisdizioni sono ancora un
  far-west normativo.

## 2. Borsa (exchange)

La **borsa**, o **exchange**, è il luogo (oggi quasi sempre virtuale) dove
gli asset si scambiano.

Esempi:

- **Borsa Italiana** (Milano): scambia azioni e altri strumenti italiani
- **NYSE** e **NASDAQ** (New York): le due principali borse americane
- **Binance**, **Coinbase**, **Kraken**: exchange crypto
- **CME** (Chicago Mercantile Exchange): futures e derivati

### Cosa fa una borsa, concretamente

Una borsa tiene un **order book** (libro degli ordini). In ogni momento, il
book contiene:

- **Ordini di acquisto** (bid): "compro X unità a un prezzo massimo di Y"
- **Ordini di vendita** (ask): "vendo X unità a un prezzo minimo di Y"

Il prezzo "corrente" di un asset è l'incontro tra il miglior bid e il
miglior ask. La differenza tra i due si chiama **spread** ed è uno dei costi
nascosti di ogni transazione.

### Le crypto e gli exchange centralizzati

Su un exchange come Binance o Kraken (CEX, "centralized exchange") il tuo
denaro e i tuoi asset sono **custoditi dall'exchange** finché non li ritiri.
Vantaggio: comodità. Svantaggio: il celebre motto "**not your keys, not your
coins**". Se l'exchange fallisce o viene hackerato, potresti perdere tutto.
È successo davvero, più volte (Mt. Gox, FTX).

Esistono anche **DEX** (decentralized exchanges) dove gli scambi avvengono
direttamente da wallet a wallet via smart contract. Più complicati, ma
nessuno custodisce i tuoi asset per te.

## 3. Broker

Un **broker** è un intermediario che ti permette di accedere a una borsa.

In Italia, esempi tipici:

- **Fineco**, **Directa**, **IWBank** per azioni e ETF su borse italiane,
  europee e USA
- **Degiro**, **Trade Republic** per accesso semplificato a borse multiple
- **Interactive Brokers** per accesso professionale e fee competitive
- **Kraken**, **Binance**, **Coinbase** per crypto (sono exchange e
  broker allo stesso tempo)

### Cosa fa il broker

- Ti dà un'interfaccia per piazzare ordini
- Trasmette i tuoi ordini alla borsa
- Mantiene il tuo conto (denaro e asset, salvo che non siano custoditi da
  un terzo come una banca o un custode)
- Gestisce il **regolamento** delle operazioni (T+2 per le azioni: l'ordine
  si chiude oggi ma il denaro/asset cambia mano dopo 2 giorni lavorativi)
- Calcola e trattiene tasse, fee, commissioni
- Ti fornisce documentazione fiscale a fine anno

### Differenze concrete

Le **fee** dei broker variano enormemente. Per dare un'idea:

- Comprare 100€ di un'azione USA su Fineco: ~3€ di commissione (3%!)
- La stessa operazione su Degiro: ~1€
- Comprare 100€ di BTC su Kraken: 0.16€-0.26€ di fee + spread (~0.5€ totali)

Su importi piccoli (DCA), le fee fisse mangiano molto. Quando si scelgono
i broker, le fee contano più di quanto sembri.

## Come si combinano

Quando vuoi comprare 100€ di Bitcoin su Kraken:

1. **Tu** apri l'app del broker (Kraken)
2. **Kraken** è sia broker che exchange: ha il proprio order book
3. Piazzi un ordine "compra 100€ di BTC al prezzo di mercato"
4. Kraken cerca nel suo order book il **miglior ask** disponibile
5. L'ordine viene eseguito: il tuo conto in euro scende di 100€, il tuo
   saldo in BTC sale (al netto di una piccola fee)
6. I tuoi BTC sono custoditi nel wallet che Kraken gestisce per te. Per
   averli "davvero in mano" devi trasferirli su un wallet che controlli tu

Quando vuoi comprare 100€ di un'azione Apple su Fineco:

1. **Tu** apri l'app del broker (Fineco)
2. **Fineco** è un broker, **non** una borsa. Ha bisogno di accedere a una
   borsa (NASDAQ, dove Apple è quotata)
3. Piazzi un ordine "compra X azioni di AAPL al prezzo di mercato"
4. Fineco gira l'ordine al NASDAQ tramite un canale internazionale
5. L'ordine viene eseguito: il tuo conto scende, il saldo in azioni AAPL
   sale
6. Le azioni sono custodite da Fineco (in realtà da un custode istituzionale
   per conto di Fineco)

## Cosa non ti ho detto

- Non ho parlato di **tipi di ordini** (market, limit, stop) — capitolo
  successivo
- Non ho parlato di come la **fiscalità** colpisce ognuno di questi passaggi —
  capitolo dedicato
- Non ho parlato di **derivati** (futures, opzioni, perpetuals): asset
  "secondari" che derivano il loro prezzo da altri asset
- Non ho parlato di **leverage** (leva finanziaria) e dei suoi rischi
- Non ho parlato di **market maker** e di come influenzano prezzo e spread

Tutto questo arriva in capitoli successivi di L1 e L2.

## Riassumendo in una frase

> Un **asset** è qualcosa con valore che si compra e si vende; la **borsa**
> è dove gli scambi avvengono incontrando domanda e offerta; il **broker**
> è chi ti porta in borsa e gestisce il tuo conto.

## Per approfondire

- Borsa Italiana, *Glossario finanziario*: voci "Asset", "Borsa valori",
  "Order book"
- Investopedia (in inglese): voci "Asset", "Stock Exchange", "Brokerage"
- Documentazione ufficiale del broker che usi (Fineco, Kraken, etc.): leggi
  le **fee** e i **termini** prima di iniziare. Non saltare questo passaggio.
