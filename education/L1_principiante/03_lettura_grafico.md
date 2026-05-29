# L1.03 — Come si legge un grafico di prezzo

> Un grafico di prezzo è il modo standard di guardare la storia di un
> asset. Sembra ovvio — c'è il tempo sull'asse x e il prezzo sull'asse
> y — ma dentro ci sono diverse convenzioni che cambiano *cosa* leggi.
> E ci sono cose che la gente "legge" nei grafici che onestamente non
> ci sono. Capitolo per distinguere.

## 1. Il grafico più semplice: linea sul tempo

Una **linea** che congiunge il prezzo di chiusura di ciascuna giornata
(o ora, o minuto). Esempio: prendendo il file `BTC_1d.parquet` che
abbiamo scaricato, la colonna `close` plottata contro la colonna
`timestamp` ti dà un grafico **a linea** dal 2018 a oggi.

**Pro**: pulito, leggibile, mostra il trend di fondo.
**Contro**: butta via informazione. Non sai quanto il prezzo è oscillato
*dentro* la giornata. Una giornata con close stabile ma intraday folle
viene confusa con una giornata calma.

## 2. La candela giapponese (candlestick)

Per ogni periodo (1 giornata, 1 ora, ecc.) la candela riassume **quattro
numeri**:

- **Open**: il primo prezzo del periodo
- **High**: il massimo toccato
- **Low**: il minimo toccato
- **Close**: l'ultimo prezzo del periodo

Sono gli stessi quattro numeri (più il volume) che hai nei parquet
`data/raw/yahoo/crypto/*.parquet`. Una candela li disegna così:

```
    │      ← high
   ╱╲
  │██│     ← corpo (open ↔ close)
   ╲╱
    │      ← low
```

Il **corpo** rettangolare va da `open` a `close`. Le linee verticali
sopra e sotto (le **ombre** o "wick") raggiungono `high` e `low`.

### Colore

Convenzione classica:

- **Verde** (o bianco) = candela "bullish": `close > open`, il prezzo è
  salito durante il periodo. Il corpo va dal basso (open) all'alto
  (close).
- **Rosso** (o nero) = candela "bearish": `close < open`, il prezzo è
  sceso. Il corpo va dall'alto (open) al basso (close).

Su exchange e piattaforme i colori si invertono spesso (alcune mettono
rosso/verde all'opposto). Guarda sempre la legenda.

### Cosa ti dice una singola candela

Un esempio concreto su BTC, giornata 2024-04-15:
- open 65.000, high 67.000, low 62.500, close 66.500
- → candela **verde** (close > open), corpo da 65.000 a 66.500, ombra
  superiore corta (fino a 67.000), ombra inferiore **lunga** (giù fino
  a 62.500)
- Lettura: la giornata è stata netta in salita (corpo verde), ma c'è
  stato un momento di forte sell-off (ombra giù a 62.500) prima del
  recupero. Una "wick lunga" indica volatilità intraday.

Una candela con corpo piccolissimo e ombre lunghe in entrambi i lati si
chiama **doji**: i compratori e i venditori si sono "neutralizzati", il
prezzo ha oscillato molto ma chiuso vicino all'apertura. Non vuol dire
niente di magico, vuol dire solo "indecisione" in quel periodo.

## 3. Il timeframe: lo stesso asset, racconti diversi

Lo stesso BTC, visto su timeframe diversi, racconta storie diverse:

- **1-minute** (1m): rumore puro, micro-oscillazioni di pochi dollari,
  utile solo per chi fa scalping
- **1-hour** (1h): si distinguono ondate intraday, utile per
  swing-trading di breve
- **1-day** (1d): il timeframe più usato per analisi e ricerca, ogni
  candela = una giornata di mercato. È il default del nostro progetto
- **1-week** (1w): cancella il rumore quotidiano, fa vedere il trend
  pluri-mensile

Una regola pratica: **più il timeframe è basso, più rumore c'è e meno
segnale**. Su un grafico 1m vedrai mille "swing" che a 1d non esistono.
Non è che sono "informazione nascosta": è solo varianza.

### Stesso asset, scale logaritmica vs lineare

Quando un asset è cresciuto molto (BTC da 1.000 a 70.000 USD nei nostri
dati = ×70), la scala **lineare** schiaccia gli anni iniziali e
gonfia quelli recenti. La scala **logaritmica** (asse y in log) rende
visivamente comparabili variazioni percentuali equivalenti.

Esempio: un movimento da 1.000 a 2.000 USD (+100%) è grafficamente
piccolo in scala lineare se nello stesso grafico c'è anche un movimento
da 50.000 a 60.000 (+20% ma 10x più grande in valore assoluto). In
scala log, il +100% è alto come qualsiasi altro +100%.

**Regola di buon senso**: per asset molto volatili / cresciuti molto
(crypto su periodi lunghi), usa il log. Per orizzonti corti o asset più
stabili, va bene lineare.

## 4. Il volume

Sotto il grafico di prezzo c'è quasi sempre un **secondo grafico** che
mostra il **volume**: quante unità dell'asset sono state scambiate in
quel periodo.

Si visualizza come barre verticali, una per ogni candela. Talvolta sono
colorate verde/rosso in coerenza con la candela corrispondente.

### Cosa il volume aggiunge

- **Movimento con volume alto**: più "confermato", più operatori
  partecipano. Un +5% di BTC con volume 3x la media ha più conferma di
  un +5% con volume bassissimo (che spesso è manipolazione o un solo
  ordine grosso che ha mosso un book vuoto).
- **Divergenza volume / prezzo**: prezzo sale ma volume cala? Può
  voler dire che il movimento sta esaurendosi.

### Caveat importante (collegamento col nostro progetto)

Il volume di una stessa giornata cambia molto a seconda della **fonte**.
Nel nostro progetto abbiamo `data/raw/yahoo/.../BTC_1d.parquet` con il
volume aggregato cross-exchange di Yahoo, e `data/raw/binance/.../BTC_1d.parquet`
con il volume del solo venue Binance.us. Sono numeri diversi, **non
confrontabili in valore assoluto**. Per questo abbiamo registrato Q23
(in `OPEN_QUESTIONS.md`) e per ora non costruiamo feature volume-based:
prima va deciso come riconciliare.

## 5. Cosa un grafico NON ti dice (essere onesti)

Qui serve onestà metodologica, perché tutta l'industria del "trading
education" su YouTube vende fumo proprio su questo.

### "Pattern grafici" e analisi tecnica

L'**analisi tecnica** è quella scuola che cerca pattern visivi
(triangoli, doppio massimo, head and shoulders, ecc.) sul grafico e
sostiene che hanno potere predittivo. La pratica esiste da decenni e ha
milioni di seguaci.

**Cosa dice la ricerca empirica seria**: la maggior parte di questi
pattern, testati out-of-sample con metodologia rigorosa, **non**
sopravvivono ai costi di transazione. Alcuni studi accademici ne hanno
mostrato un piccolo segnale residuo, altri smentito; la conclusione
prudente è che se esiste, è piccolo e instabile.

**Cosa NON significa**: che chartisti non guadagnino. Possono guadagnare
per altri motivi (gestione del rischio, position sizing, fortuna, o un
edge separato dal pattern). Ma il pattern in sé, da solo, non è la
"mappa del tesoro" che viene venduto come.

Per il nostro progetto la posizione è: **non escludere i pattern come
features** (in futuro li possiamo testare quantitativamente), ma **non
trattarli come verità rivelata**. Vedi anche VISION.md sul rigore
metodologico.

### "Supporto" e "resistenza"

Concetti onnipresenti: il "supporto" è un livello sotto il quale il
prezzo "non riesce a scendere", la "resistenza" è il livello sopra il
quale "non riesce a salire". Sono utili come narrazione descrittiva
(il prezzo *si è effettivamente fermato* lì molte volte), ma come
previsione sono pessimi: il prezzo "buca" supporti e resistenze
costantemente, soprattutto in crypto.

### Il grafico "lo vedi solo dopo"

Il pattern più seducente del mondo: guardi un grafico passato, vedi
chiaramente che "lì c'era un triangolo che si è risolto in alto, era
ovvio". Sì, *col senno di poi*. In **tempo reale**, mentre il triangolo
si forma, non sai mai se si "risolverà" in alto o in basso, e nemmeno
se è un triangolo o solo rumore. Questo è il **hindsight bias** ed è
universale, non un difetto tuo.

## 6. Collegamento col nostro progetto

Quando in `notebooks/01_exploration_btc_eth.ipynb` plottiamo `close`
contro `timestamp` di BTC, stiamo facendo un grafico a linea — la
versione più semplice. I dati nei parquet contengono già OHLC: se in
futuro vorremo grafici a candele, basta usare librerie come `mplfinance`
o `plotly` che li disegnano automaticamente da DataFrame con colonne
`open, high, low, close, volume`.

I notebook EDA esistenti producono:
- distribuzioni di rendimenti (istogrammi) → leggono *la varianza*
  intorno alla media, non il trend
- ACF (autocorrelation function) → leggono se i rendimenti hanno
  *memoria* (non ne hanno) o se la volatilità ce l'ha (sì)
- correlazioni cross-asset e cross-macro → leggono come si muovono
  insieme

Queste sono **alternative quantitative** al "guardare il grafico ad
occhio". Il vantaggio: numeri riproducibili, non interpretazione
soggettiva.

## Glossario rapido

- **OHLC**: Open, High, Low, Close — i quattro numeri che descrivono un
  periodo
- **Candela / candlestick**: rappresentazione visuale di OHLC
- **Corpo (body)**: il rettangolo della candela, va da open a close
- **Ombra / wick**: la linea verticale sopra/sotto, raggiunge high e low
- **Doji**: candela con corpo quasi nullo (open ≈ close), spesso letta
  come "indecisione"
- **Timeframe**: la durata di ogni candela (1m, 1h, 1d, 1w)
- **Scala log vs lineare**: l'asse y può misurare prezzi assoluti
  (lineare) o variazioni percentuali (log)
- **Pattern**: configurazione grafica riconoscibile (triangolo, doppio
  massimo, ecc.). Onestà richiesta sul loro reale potere predittivo
- **Supporto / resistenza**: livelli che "trattengono" il prezzo;
  descrizioni utili, previsioni mediocri
- **Hindsight bias**: la tendenza a "vedere chiari" pattern nel passato
  che in tempo reale non erano affatto chiari

## Cosa portare via

- Una **candela** è un OHLC visualizzato. Sapere come leggere corpo e
  ombre ti dice in 1 secondo se la giornata è stata calma, volatile,
  netta in salita o un disastro evitato all'ultimo
- Il **timeframe** non è neutrale. 1m è quasi solo rumore. 1d è il
  default ragionevole. 1w mostra trend, non eventi
- Il **volume** sotto il grafico aggiunge contesto, ma confrontare
  volumi tra venue diversi (Binance vs Yahoo aggregato) è insidioso —
  nel nostro progetto la decisione è rimandata (vedi Q23)
- **Diffida** di chi vende pattern grafici come "il segreto". La
  ricerca seria mostra che il loro potere predittivo netto-costi è
  modesto o nullo. Possono essere parte di un sistema più grande, ma
  non sono la mappa del tesoro
- Il modo onesto di studiare i prezzi è **quantitativo e riproducibile**
  — il che è esattamente quello che facciamo nei notebook EDA del
  progetto

---

*Prossimo capitolo*: L1.04 — Fee, spread, slippage spiegati senza
matematica.
