# L1.02 — Tipi di ordine: market, limit, stop

> Quando vuoi comprare o vendere un asset, non esiste "il pulsante BUY".
> Esistono diversi modi di chiedere al mercato di eseguire la tua
> operazione, ciascuno con un compromesso tra **velocità**, **prezzo**
> e **certezza di esecuzione**. Capirli è la prima cosa che separa chi
> sa cosa sta facendo da chi clicca e basta.

## Un ordine, cos'è

Un **ordine** è un'istruzione che mandi all'exchange (o al broker) per
fare un'operazione. Ogni ordine contiene almeno:

- **Direzione**: stai comprando (buy) o vendendo (sell)?
- **Quantità**: quante unità dell'asset?
- **Tipo**: market, limit, stop, ecc. — è quello che vediamo qui
- **Time in force** (opzionale): per quanto tempo l'ordine resta attivo
  se non viene eseguito subito?

Il tipo di ordine cambia drasticamente cosa succede dopo che lo invii.

## 1. Market order — "lo voglio adesso, qualunque sia il prezzo"

Il **market order** è il più semplice: dici all'exchange "compra (o
vendi) X unità *al miglior prezzo disponibile, subito*".

**Esempio concreto**. BTC è scambiato in questo momento con miglior bid
75.000 e miglior ask 75.020 (spread di 20 USD). Mandi un market buy
order di 1 BTC. L'exchange prende il miglior ask disponibile, e ti
assegna 1 BTC a (circa) 75.020 USD.

### Pro

- **Esecuzione garantita** (in mercati liquidi)
- Velocissimo, non devi pensare al prezzo

### Contro

- **Non sai esattamente il prezzo finale**. Se la tua quantità è grande
  o l'order book è poco profondo, il tuo ordine "mangia" più livelli del
  book e finisci per pagare un prezzo medio peggiore di quello visto
  un secondo prima. Questo si chiama **slippage**.
- Sui mercati illiquidi (es. altcoin di nicchia) il market order può
  diventare un disastro: 5%-10% di slippage è plausibile.
- Pagando con un market order sei sempre tu a "incassare lo spread",
  non a guadagnarlo. È il prezzo della comodità.

### Quando usarlo

- Devi entrare/uscire **subito** e non ti importa pagare un po' di più
- L'asset è **molto liquido** (BTC, ETH, top-cap equity) → lo spread è
  minimo
- Per **piccoli importi**, lo slippage è trascurabile

## 2. Limit order — "lo voglio solo a questo prezzo (o migliore)"

Il **limit order** dice all'exchange: "compra a un prezzo *massimo* di
Y" oppure "vendi a un prezzo *minimo* di Y". Se nessuno è disposto a
incrociare la tua proposta, l'ordine resta nel book in attesa.

**Esempio**. BTC è a 75.000 USD. Pensi che possa scendere a 73.000 prima
di risalire. Mandi un **limit buy a 73.000**. L'ordine entra nel book.
Tre possibilità:

1. **Il prezzo scende a 73.000** → il tuo ordine viene **eseguito** a
   quel prezzo (o anche meglio se c'è un venditore a 72.950).
2. **Il prezzo non scende mai a 73.000** → l'ordine **non viene mai
   eseguito**. Resti senza posizione.
3. **Il prezzo scende a 73.000 ma il book ha solo metà della tua
   quantità** → fill parziale: ne compri metà, l'altra metà resta in
   attesa.

### Pro

- **Controllo del prezzo**: paghi esattamente quello che vuoi, mai peggio
- Niente slippage (per definizione, il limit è il tuo prezzo massimo)
- Su molti exchange, gli ordini che restano nel book (**maker orders**)
  pagano fee minori, o addirittura ricevono un piccolo rebate

### Contro

- **Esecuzione non garantita**: se il prezzo non tocca il tuo livello,
  resti fuori. Puoi perdere "the move" perché aspettavi 73.000 e il
  prezzo è risalito a 80.000.
- Richiede di avere un'opinione sul prezzo (non sempre giustificata)

### Quando usarlo

- Sai che il prezzo attuale è "troppo alto" o "troppo basso" rispetto al
  tuo livello target
- Stai entrando/uscendo con un **size grosso** e vuoi evitare slippage
- Sei disposto a **rinunciare all'esecuzione** se il prezzo non gioca

## 3. Stop order — "scattalo solo se il prezzo si rompe"

Il **stop order** è un ordine "armato": non è attivo fin quando il
prezzo non tocca un livello che tu fissi (**stop price** o **trigger**).
A quel punto si trasforma in un altro ordine (di solito un market).

Le due varianti più comuni:

### Stop-loss (vendita protettiva)

Hai comprato BTC a 75.000. Vuoi accettare al massimo una perdita del
~7%, quindi metti uno **stop-loss sell a 70.000**. Finché BTC sta sopra
70.000, l'ordine non fa nulla. Se il prezzo tocca 70.000, l'ordine
scatta e diventa un market sell → vendi a ~70.000 (o leggermente meno,
per via dello slippage).

### Stop-buy (acquisto su rottura)

Pensi che se BTC supera 80.000 partirà un rally. Metti uno **stop-buy a
80.000**. Finché il prezzo è sotto, niente. Appena tocca 80.000, scatta
un market buy.

### Stop-limit: il fratello prudente

Il **stop-limit** è uno stop che, invece di diventare un market, diventa
un **limit**. Esempio: "stop-loss a 70.000 limit 69.800" → quando il
prezzo tocca 70.000, viene piazzato un limit sell a 69.800. Se il
mercato crolla velocemente sotto 69.800, il tuo ordine **non viene
eseguito** e potresti restare con la posizione aperta in piena rotta.
Compromesso: protezione dal cattivo slippage, rischio di non vendere
mai in un crash forte.

### Pro

- Automatizza la disciplina: il rischio di perdita è cappato a un
  livello deciso a freddo
- Non devi guardare lo schermo h24

### Contro

- **Triggering su un wick**: in crypto i prezzi oscillano spesso in
  pochi minuti di -5% +5% (manipolazione, news, low liquidity). Il tuo
  stop può scattare su un movimento momentaneo e venderti al peggio,
  poco prima che il prezzo recuperi.
- Se l'asset è poco liquido, lo stop diventa un market che mangia il
  book → forte slippage.

## 4. Time in force — per quanto tempo l'ordine "vive"

I limit e gli stop possono avere flag che indicano la durata:

- **GTC** (good 'til cancelled): resta attivo finché non lo cancelli o
  viene eseguito. Default su molti exchange.
- **DAY**: cancellato a fine giornata se non eseguito
- **IOC** (immediate or cancel): cerca di eseguire subito quanto
  possibile, cancella il resto
- **FOK** (fill or kill): o esegue tutto subito, o niente

## 5. Considerazioni pratiche

### Maker vs taker

- **Maker**: il tuo ordine entra nel book e ci resta. **Aggiunge
  liquidità** al mercato. Tipicamente paga fee minori.
- **Taker**: il tuo ordine **prende** liquidità esistente (market order
  o limit che incrocia subito). Paga fee piene.

Esempio Kraken 2026: maker fee 0.16%, taker 0.26%. Su 1000 USD di
operazione, sono 1.60 vs 2.60 USD. Per attività frequente la differenza
si accumula.

### Slippage = costo nascosto

Quando confronti due exchange, non guardare solo le fee. Uno con fee
basse ma liquidità scarsa può costarti più di uno con fee alte e
mercato profondo, perché paghi slippage su ogni operazione.

### Crypto è 24/7 → stop più rischiosi

Sulle azioni, il mercato chiude la sera. Se metti uno stop-loss su un
titolo italiano, scatta solo nelle ore di apertura di Borsa Italiana.
Sui crypto, il tuo stop può scattare alle 4 di notte su un movimento di
flash crash e ritrovarti svegliato dalla notifica.

## 6. Collegamento al nostro progetto

Il sistema che stiamo costruendo (vedi `VISION.md`) **non esegue ordini
reali** — è uno strumento di ricerca, segnali probabilistici, non
trading bot (ADR-004). Però i tipi di ordine restano rilevanti per:

- **Modellare correttamente i costi** quando faremo paper trading
  (ADR-013 — modello di slippage). Un segnale che funziona "in teoria"
  ma richiede market order su altcoin poco liquide può perdere il 2-3%
  per esecuzione, abbastanza da farlo diventare negativo.
- **Capire i dati che scarichiamo**: il volume Binance che vediamo nel
  parquet `data/raw/binance/crypto/BTC_1d.parquet` aggrega tutti questi
  tipi di ordine eseguiti su quel venue. Quando guarderemo "volume
  spikes" stiamo guardando picchi di market + limit incrociati, non
  intenzioni isolate.
- **Decidere come simulare l'esecuzione** se mai facessimo paper
  trading: tutto a market (worst case di slippage), tutto a limit
  (rischio di non essere mai pieni), o un mix con regole esplicite.

## Glossario rapido

- **Bid**: prezzo a cui qualcuno è disposto a comprare
- **Ask**: prezzo a cui qualcuno è disposto a vendere
- **Spread**: ask − bid. Costo implicito di una transazione round-trip
- **Slippage**: differenza tra prezzo previsto e prezzo effettivo
  eseguito, dovuta al movimento del book mentre il tuo ordine viene
  riempito
- **Fill**: esecuzione di un ordine. Può essere totale o parziale
- **Order book**: la lista ordinata di tutti i bid e ask attivi su un
  asset, in un dato exchange
- **Liquidità**: quanto book c'è ai prezzi vicini al mid. Più alta è la
  liquidità, meno slippage paghi

## Cosa portare via

- Un **market order** è veloce ma cieco sul prezzo finale. Tienilo per
  i mercati liquidi o le quantità piccole.
- Un **limit order** ti dà il controllo del prezzo a costo
  dell'incertezza sull'esecuzione. È il default per chi opera con
  metodo.
- Uno **stop-loss** è la più semplice forma di disciplina automatica,
  ma non ti salva da tutto: in crypto può triggerare su un wick e
  venderti al peggio.
- La domanda "**qual è la fee?**" è incompleta. La vera domanda è "fee
  + spread + slippage atteso = costo totale". Solo allora puoi
  confrontare due venue.

---

*Prossimo capitolo*: L1.03 — Come si legge un grafico di prezzo (candele,
volume, e cosa non significano).
