# L2.09 — Il ciclo halving di Bitcoin: cosa è e cosa non promette

> Capitolo della Fase 5. L'halving è il ciclo più citato (e più
> mitizzato) del mondo crypto. Questo progetto lo tratta come tratta
> tutto: un'ipotesi da misurare. Il "calendario del ciclo" è implementato
> in `src/features/cycles.py` e l'analisi completa — con la posizione del
> ciclo *attuale* — è nel notebook 11. Qui trovi entrambi, più il caveat
> che quasi tutti omettono.

## 1. Cos'è l'halving, meccanicamente

Bitcoin emette nuova moneta come ricompensa ai miner per ogni blocco.
Ogni ~210.000 blocchi (circa **4 anni**), questa ricompensa **si dimezza**
— da qui "halving". Date reali: novembre 2012, luglio 2016, maggio 2020,
aprile 2024; il prossimo è schedulato dal protocollo per **aprile 2028**.

L'effetto economico diretto: il flusso di nuova offerta si dimezza da un
giorno all'altro. La **tesi rialzista classica**: domanda invariata +
offerta dimezzata = pressione al rialzo nei mesi successivi. La
**controtesi**: l'halving è noto a tutti con anni di anticipo, quindi un
mercato anche solo decentemente efficiente lo ha già **prezzato**.

Chi ha ragione? Con onestà: **non è dimostrabile** — vedi §4. Ma il
pattern storico, quello sì, si può misurare.

## 2. Il "4-year cycle": il pattern misurato

Trattando l'halving come un orologio (giorni trascorsi dall'ultimo,
giorni al prossimo, fase del ciclo da 0 a 1 — tutte feature causali, solo
calendario, mai prezzi futuri), la storia di BTC mostra un ritmo
sorprendentemente regolare:

| Fase (giorni dall'halving) | Cosa è successo, in tutti i cicli finora |
|---|---|
| 0 → ~520 | Espansione: il grosso del bull market |
| **~520-550** | **Il picco del ciclo** (~17-18 mesi post-halving, ogni volta) |
| ~550 → ~880 | Contrazione: il "crypto winter" |
| **~880-920** | La zona dove si sono formati i **minimi** |
| poi → halving successivo | Riaccumulo verso il ciclo seguente |

È il pattern dietro gli slogan "il bull arriva l'anno dopo l'halving" e
"il bear di metà ciclo". Nei dati, finora, il ritmo ha tenuto.

## 3. Il ciclo attuale, letto con questo orologio

L'analisi del notebook 11 (metà 2026, ~775 giorni dall'halving 2024)
colloca il presente con precisione:

- il massimo del ciclo si è formato **nella stessa finestra dei
  precedenti** (~520-550 giorni post-halving);
- alla fase attuale, i cicli 2016 e 2020 erano a **−66%/−68%** dal picco;
  il ciclo attuale segna circa **−49%** — doloroso, ma *meno* estremo dei
  precedenti alla stessa fase;
- se lo schema si ripetesse, la zona storica dei minimi cadrebbe verso
  **fine 2026** (~880-920 giorni post-halving);
- una **differenza rilevante e dichiarata**: il winter 2022 avvenne con la
  Fed in stretta monetaria; oggi il contesto macro segna risk-on. Il
  ribasso attuale sembra guidato dal ciclo *interno* del crypto più che da
  un macro avverso — storicamente un'attenuante, non una garanzia.

In una frase (dal notebook, testualmente): *non è "qualcosa di strano" —
è il respiro tipico del ciclo dell'halving, nella sua fase di
contrazione.*

## 4. Il caveat che vale metà capitolo

Quanti cicli completi abbiamo per "validare" tutto questo? **Tre.**
Tre osservazioni non validano statisticamente nulla — con n=3, anche una
moneta può fare tre teste di fila. In più:

- ogni ciclo ha avuto **fattori unici e non ripetibili**: il 2020 lo
  stimolo monetario post-pandemia, il 2024 gli **ETF spot** (una novità
  strutturale nella domanda che nessun ciclo precedente aveva);
- il pattern è noto a tutti → se funzionasse in modo affidabile, i
  partecipanti lo anticiperebbero, spostandolo o annullandolo (è la
  versione ciclica dell'efficienza dei mercati);
- la coincidenza col ciclo macro globale (~4 anni anche quello) rende
  impossibile separare "effetto halving" da "effetto liquidità mondiale".

Per questo il progetto tratta l'halving come **feature di contesto** — un
orologio che dice *in che stagione sei* — e non come segnale operativo.
La domanda "l'halving è ancora predittivo nel 2026+ o è prezzato?" resta
**aperta** nel nostro registro delle domande di ricerca, ed è lì che deve
stare finché i dati non bastano.

## 5. Cosa può dirti e cosa no

- ✅ **Può**: "sei nella fase di contrazione post-picco, territorio già
  visto due volte, drawdown finora meno profondo dei precedenti alla
  stessa fase". Contesto, aspettative, preparazione psicologica (L2.05:
  sai *che tipo* di tempo sott'acqua aspettarti).
- ❌ **Non può**: dirti se il minimo è passato, quando arriva, o se il
  prossimo ciclo somiglierà ai precedenti. "Finora 2 volte su 2" è un
  pattern da osservare, **non una promessa**.

L'errore tipico da evitare: usare il ciclo come *timer di acquisto
preciso* ("compro esattamente a 900 giorni dall'halving"). La bussola ti
dice la direzione del nord, non il sentiero: con n=3, i margini di errore
sono di **mesi**, e un solo ciclo diverso rompe lo schema.

## 6. Collegamenti

- **L2.05** — Drawdown: il winter di metà ciclo è dove vive il MaxDD di BTC
- **L2.06** — Bias: la narrativa dell'halving è terreno fertile per FOMO e
  recency bias ("stavolta è uguale/diverso")
- **L2.08** — Regimi: l'halving è il livello "ciclo lungo" sopra i regimi
- Nel codice: `src/features/cycles.py` (halving clock causale, date come
  costanti), notebook 11 (l'analisi del ciclo attuale, riproducibile)
