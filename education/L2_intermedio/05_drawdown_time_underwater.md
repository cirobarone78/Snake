# L2.05 — Drawdown massimo e tempo sott'acqua: le metriche che contano davvero

> Capitolo della Fase 2. Tutte le metriche descritte qui sono implementate
> e testate nel repo (`src/backtest/metrics.py`) e i numeri d'esempio
> vengono dai backtest reali del progetto sui dati 2019-2026 — non da
> tabelle di manuale. È il capitolo gemello di L1.07 (volatilità): là i
> concetti, qui le misure con cui si giudica *qualsiasi* strategia.

## 1. Perché il rendimento medio è una metrica bugiarda

"BTC ha reso il +49% annuo composto dal 2019." Vero (è il numero del
nostro backtest out-of-sample). Ma quel numero da solo nasconde
l'esperienza reale di chi lo ha tenuto: **crolli del 77%** e anni interi
passati sotto i massimi precedenti. Due investimenti con lo stesso
rendimento medio possono essere uno tollerabile e l'altro devastante.

Le metriche di questo capitolo esistono per misurare **la strada, non solo
la destinazione**.

## 2. Drawdown: la distanza dal massimo

Il **drawdown** in un dato giorno è la distanza percentuale dal massimo
storico toccato fino a quel momento:

```
drawdown(t) = valore(t) / massimo_fino_a(t) − 1
```

È sempre ≤ 0. Il **massimo drawdown (MaxDD)** è il peggior valore mai
toccato: la peggior discesa "dal picco alla valle" che avresti vissuto
entrando nel momento più sfortunato.

Numeri reali dal nostro backtest (2019-2026, out-of-sample):

| Asset (buy & hold) | MaxDD |
|---|---|
| BTC | **−77%** |
| ETH | **−79%** |
| LINK | **−90%** |

Non sono scenari teorici da stress test: sono successi, dentro il periodo
che abbiamo misurato, a chiunque tenesse quegli asset.

## 3. La matematica crudele del recupero

Il motivo per cui il drawdown è LA metrica di sopravvivenza è
un'asimmetria aritmetica che il cervello sottovaluta sistematicamente:

| Perdita | Guadagno necessario per tornare pari |
|---|---|
| −10% | +11% |
| −25% | +33% |
| −50% | **+100%** |
| −77% (BTC) | **+335%** |
| −90% (LINK) | **+900%** |

La discesa è lineare nel sentirla, ma il recupero è **convesso**: ogni
punto perso in più costa sproporzionatamente di più da riguadagnare. È
per questo che il risk management (L2.04) è ossessionato dal taglio delle
code: evitare il −50% vale molto più che catturare un +50%.

## 4. Time underwater: la metrica psicologica

Il **tempo sott'acqua** è la frazione di giorni passati sotto un massimo
precedente — cioè i giorni in cui, guardando il conto, vedi meno del tuo
punto migliore.

Il numero reale più istruttivo dell'intero progetto:

> Nel nostro periodo di test, BTC buy-and-hold ha reso ~+49% annuo
> **passando il 95% dei giorni sott'acqua**.

Rifletti su cosa significa: anche nell'asset che "ha reso tantissimo",
l'esperienza quotidiana per 19 giorni su 20 è stata *"sono sotto il mio
massimo"*. Chi immagina l'investimento vincente come una serie di nuovi
record si sta preparando ad abbandonare quello vero, che è fatto
soprattutto di attesa in perdita apparente. Il time underwater misura
esattamente la quantità di disciplina che una strategia ti chiederà.

C'è anche la **durata del drawdown massimo**: quanti giorni consecutivi
tra un picco e il ritorno a quel picco. Anni, non settimane, per i grandi
bear market — un'informazione da conoscere *prima* di entrare, non da
scoprire durante.

## 5. Le metriche composte: Sharpe, Sortino, Calmar

Per confrontare strategie servono rapporti rendimento/rischio. I tre che
il progetto calcola su ogni backtest:

- **Sharpe** = rendimento extra / volatilità totale. Lo standard, ma
  "punisce" anche la volatilità al rialzo (che a nessuno dispiace).
- **Sortino** = rendimento extra / volatilità *solo al ribasso*. Più
  fedele a come un umano vive il rischio.
- **Calmar** = rendimento annuo / |MaxDD|. Il più brutale: quanto
  rendimento ottieni per ogni punto di peggior catastrofe. Per chi non
  può permettersi il drawdown (quasi tutti), spesso è il più informativo.

Nessuno dei tre è "quello giusto": sono lenti diverse. Una strategia con
Sharpe alto e Calmar basso guadagna spesso ma può farti malissimo una
volta; il contrario è una strategia noiosa che non ti uccide mai.

## 6. Il caso studio del progetto: comprare il drawdown migliore

Il risultato più interessante dei nostri backtest (notebook 04) collega
tutto questo capitolo: la strategia momentum non prevede la direzione
(accuratezza ~50%, L2.01), eppure su BTC ed ETH batte il buy-and-hold.
Come? **Comprando un drawdown migliore:**

| BTC out-of-sample | Buy & hold | Momentum (netto costi) |
|---|---|---|
| Rendimento annuo | +49% | +61% |
| **MaxDD** | **−77%** | **−50%** |
| Sharpe | 0,96 | 1,29 |

E la decomposizione per regime mostra *dove* avviene la magia: nei bear
market il momentum sta fuori e il suo drawdown si ferma a −64% contro
−92% del buy-and-hold. Non è chiaroveggenza: è **gestione del drawdown
travestita da strategia**. (Con l'eccezione onesta di LINK, dove il
filtro peggiora le cose — la robustezza si verifica asset per asset,
sempre.)

## 7. Come usare queste metriche, in pratica

1. **Prima di entrare** in qualsiasi asset/strategia, cerca (o calcola) il
   suo MaxDD storico e chiediti: *"reggerei un altro così, con la size che
   ho in mente?"* Se la risposta è no, il problema è la size (L2.04 §2).
2. **Diffida dei rendimenti senza drawdown accanto**: chi mostra solo il
   CAGR sta nascondendo la strada.
3. **Time underwater per calibrare le aspettative**: se una strategia
   storicamente passa il 90%+ dei giorni sotto i massimi, la tua pazienza
   è parte del capitale richiesto.
4. **Nei confronti usa Calmar oltre a Sharpe**: due numeri diversi che
   raccontano rischi diversi.

## 8. Collegamenti

- **L1.07** — Volatilità e drawdown: l'introduzione concettuale
- **L2.04** — Risk management: gli strumenti che il drawdown lo *limitano*
- **L2.06** — Bias cognitivi: perché il drawdown fa vendere sul minimo
- **L2.08** — Cicli e regimi: i bear market, l'habitat naturale del drawdown
- Nel codice: `src/backtest/metrics.py` (`max_drawdown`,
  `max_drawdown_duration`, `time_underwater`, `calmar_ratio`), notebook 04
  (i numeri citati, riproducibili)
