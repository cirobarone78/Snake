# L2.04 — Risk management: position sizing, stop loss, take profit

> Il capitolo più importante di L2. La ricerca di questo progetto non ha
> trovato un modo affidabile di *prevedere* i mercati (L2.01) — ma ha
> trovato, misurato sui dati, che **gestire il rischio funziona**. Il
> codice di questo capitolo esiste nel repo (`src/risk/trailing_stop.py`)
> ed è stato applicato a un caso reale che raccontiamo in fondo, numeri
> veri inclusi.

## 1. L'idea che cambia tutto: si parte dalla perdita, non dal guadagno

Il dilettante chiede: "quanto posso guadagnare?". Il professionista
chiede: "**quanto sono disposto a perdere se ho torto?**" — e da lì deriva
tutto il resto. Il risk management è l'insieme di regole, decise **a
freddo e prima**, che rispondono a tre domande:

1. **Quanto compro?** → position sizing
2. **Dove esco se ho torto?** → stop loss
3. **Dove/come esco se ho ragione?** → take profit o trailing stop

Il motivo per cui le regole vanno decise prima è la loss aversion
(L2.06): nel momento caldo il tuo cervello è l'ultimo consigliere di cui
fidarsi.

## 2. Position sizing: la formula che viene prima di tutto

La regola classica: **rischia una frazione fissa e piccola del capitale
per ogni operazione** — tipicamente l'1-2%.

La formula, in tre righe:

```
rischio_per_trade = capitale × 1%              (es. 10.000 € × 1% = 100 €)
distanza_stop     = prezzo_entrata − prezzo_stop   (es. 100 € − 94 € = 6 €)
size              = rischio_per_trade / distanza_stop  (es. 100/6 ≈ 16 azioni)
```

Leggila al contrario, perché è lì la lezione: **la dimensione della
posizione è una conseguenza dello stop**, non viceversa. Prima decidi dove
il tuo scenario è invalidato (lo stop), poi la matematica ti dice quanto
puoi comprare. Chi compra "10.000 € di X" e *poi* si chiede dove mettere
lo stop sta facendo il procedimento alla rovescia.

Con l'1% per trade, servono ~70 perdite consecutive per dimezzare il
capitale. Con il 10% ne bastano 7. La differenza tra sopravvivere a una
serie negativa (che arriverà: è statistica, non sfortuna) e saltare è
tutta qui.

## 3. Stop loss: fisso, percentuale, o basato sulla volatilità

Uno stop a "−5% fisso" tratta allo stesso modo un titolo tranquillo e una
crypto che oscilla del 5% *al giorno*. È un errore di calibrazione: sullo
strumento volatile verrai buttato fuori dal **rumore normale**, non da un
vero cambio di scenario.

La soluzione è ancorare lo stop alla **volatilità dello strumento**,
misurata dall'**ATR** (Average True Range: l'escursione giornaliera
tipica, implementata in `src/features/indicators.py`):

- **Stop a 2×ATR** sotto il prezzo: stretto, protegge presto, rischia
  qualche falsa uscita
- **Stop a 3×ATR**: largo, dà respiro al titolo, cede di più se gira

Se l'ATR di un titolo è il 2,5% del prezzo, uno stop a 2×ATR sta a −5%:
fuori dal respiro quotidiano, dentro la portata di un vero deterioramento.

## 4. Trailing stop: lo stop che sale con te

Lo stop fisso protegge il capitale iniziale. Il **trailing stop** protegge
anche il *profitto maturato*: insegue il massimo raggiunto dal prezzo, a
distanza di N×ATR, e **sale soltanto, mai scende** (a cricchetto). La
variante classica si chiama *chandelier exit* ed è implementata e testata
nel repo (`src/risk/trailing_stop.py`).

**Caso reale del progetto** (estate 2026): posizione su un titolo
healthcare USA, entrata 397 $, prezzo salito a 412 $ (+3,8%), ATR ≈ 10 $.
Le opzioni calcolate dal codice:

| Stop | Livello | Cosa significa |
|---|---|---|
| Break-even | 397 $ | rischio zero, ma è a solo 1,5 ATR: il rumore può colpirlo |
| 2×ATR | 392 $ | fuori dal rumore, perdita max −1,3% |
| 3×ATR | 382 $ | più respiro, cede di più se gira |

Nessuna previsione: solo la geometria del rischio, resa esplicita. La
scelta resta di chi ha la posizione — ma è una scelta *informata*, fatta
prima che l'emozione entri in scena.

## 5. La verità scomoda: lo stop è un'assicurazione, non un profitto

Sul titolo dell'esempio abbiamo fatto anche il backtest storico della
regola (173 finestre di un anno, 16 anni di dati):

| | Con trailing stop 2,5×ATR | Comprare e tenere |
|---|---|---|
| Rendimento medio | **+0,5%** | **+18,9%** |
| Peggior 10% dei casi | **−3,2%** | **−32,6%** |

Leggilo bene, perché è controintuitivo e fondamentale:

- In media, lo stop **costa** rendimento (ti butta fuori dai rialzi,
  spesso troppo presto).
- Nei disastri, lo stop **ti salva** (−3% invece di −33%).

È esattamente il profilo di un'**assicurazione**: paghi un premio (il
rendimento medio perso) per tagliare la coda catastrofica. Se qualcuno ti
vende lo stop loss come tecnica per *guadagnare di più*, i nostri dati
dicono altro. Lo compri per **dormire**, e per sopravvivere abbastanza a
lungo da lasciare lavorare l'interesse composto.

Due caveat onesti:

1. **Il gap risk esiste**: lo stop è un ordine, non una garanzia di
   prezzo. Nel dataset del nostro esempio c'è un giorno da **−22%**: uno
   stop a −5% sarebbe stato eseguito molto più in basso. Sugli strumenti
   che possono gappare, lo stop riduce il rischio, non lo azzera.
2. **Dipende dallo strumento**: su asset "da cassettista" con trend
   secolare, il costo dell'assicurazione è alto. Su asset volatili e
   ciclici, il taglio delle code vale molto di più (vedi il momentum
   difensivo di L2.01: stessa logica, dati crypto).

## 6. Take profit: target fisso o lasciar correre?

Il **take profit** fisso ("esco a +20%") ha un difetto statistico: i
rendimenti dei trend sono *asimmetrici*, pochi movimenti molto grandi
pagano per tanti piccoli. Tagliare i vincitori a +20% ti amputa proprio
la coda destra che finanzia tutto il resto.

L'alternativa coerente con i dati è il **trailing stop come uscita**:
non fissi un tetto, lasci correre, e l'uscita avviene quando il trend
si inverte *di fatto* (il prezzo ritraccia di N×ATR dal massimo). Nel
nostro backtest crypto è l'unica versione del momentum che ha battuto il
buy-and-hold — non prevedendo, ma *non restando* nei crolli.

Compromesso pratico usato da molti: **uscita parziale** (metà posizione a
un target, metà in trailing). Matematicamente sub-ottimale,
psicologicamente sostenibile — e una regola che riesci a seguire vale più
di una perfetta che abbandoni.

## 7. Gli errori che il processo deve impedire

1. **Spostare lo stop "solo per questa volta"** quando il prezzo si
   avvicina → hai appena cancellato l'intero sistema.
2. **Size da lotteria su un'idea "sicura"** → non esistono idee sicure;
   esiste la formula del §2.
3. **Stop dentro il rumore** (più stretto di ~1,5-2 ATR) → uscite
   continue, morte per mille tagli, e i costi (L1.04) fanno il resto.
4. **Nessuno stop "perché tanto è di lungo periodo"** → legittimo *solo*
   se la size è tale che un −80% non ti costringe a vendere (torna al §2:
   è sempre un problema di sizing).

## 8. Collegamenti

- **L1.04** — Fee, spread, slippage: i costi che ogni uscita/entrata paga
- **L1.07** — Volatilità e drawdown: il "perché" psicologico di tutto questo
- **L2.01** — Indicatori: l'ATR nasce lì
- **L2.05** — Drawdown massimo: la metrica che il risk management protegge
- **L2.06** — Bias cognitivi: il nemico che le regole scritte neutralizzano
- Nel codice: `src/risk/trailing_stop.py` (chandelier exit testato),
  `src/backtest/costs.py` (il conto spese di ogni regola di uscita)
