# L2.06 — Bias cognitivi: FOMO, loss aversion, e perché il tuo cervello rema contro

> Capitolo della Fase 3 (sentiment & notizie). I capitoli tecnici di L2
> parlano di **cosa** guardare; questo parla del **chi guarda**: tu. Il
> nemico numero uno di un investitore non è il mercato, è il proprio
> cervello — un organo ottimizzato per sopravvivere nella savana, non per
> prendere decisioni di portafoglio.
>
> Questo capitolo è anche la chiusura onesta di un esperimento che abbiamo
> **davvero fatto** in questo progetto: misurare se il sentiment delle
> notizie anticipa i prezzi. Spoiler: no — e il *perché* è metà psicologia
> di massa, metà statistica. Lo raccontiamo in fondo (sezione 8).

## 1. Premessa: i bias non sono "errori da stupidi"

Un **bias cognitivo** è una scorciatoia mentale sistematica. Non è
ignoranza: è un meccanismo che funzionava benissimo per evitare i leoni e
funziona malissimo per comprare e vendere asset volatili. Tre cose da
tenere a mente:

1. **Sono universali**. Premi Nobel, gestori di hedge fund, ingegneri:
   tutti li hanno. Sapere che esistono li riduce solo in parte.
2. **Sono asimmetrici verso la perdita** (vedi loss aversion). Il dolore
   di perdere è il driver dominante, e i mercati lo sfruttano.
3. **Il rimedio non è "essere più intelligenti"**, è **avere un processo**
   (regole scritte prima, DCA, ribilanciamento automatico) che toglie la
   decisione al cervello nel momento caldo.

## 2. FOMO — Fear Of Missing Out

La **paura di restare fuori**. BTC fa +40% in due settimane, ne parlano
tutti, il tuo collega si vanta del suo X profitto, e tu compri **al
massimo locale** perché "sta scappando il treno".

- **Meccanismo**: il prezzo che sale *è esso stesso* la notizia che attira
  compratori. La FOMO è procyclica — amplifica i top.
- **Dove la vedi nei nostri dati**: nei notebook EDA (L1.07, capitolo
  volatilità) abbiamo misurato **skewness negativa** su BTC/ETH: i crolli
  sono più bruschi delle salite. Chi entra in FOMO entra spesso poco prima
  della coda sinistra.
- **Antidoto**: il **DCA** (L1.06). Comprare a importo fisso a cadenza
  fissa rende la FOMO irrilevante per costruzione: non decidi *quando*,
  quindi non puoi sbagliare il timing per emozione.

## 3. Loss aversion — il dolore conta doppio

Kahneman & Tversky: **perdere 100 fa male circa il doppio del piacere di
guadagnare 100**. Conseguenze pratiche micidiali:

- **Disposition effect**: vendi troppo presto i vincitori (per "bloccare"
  il piccolo guadagno e calmare l'ansia) e tieni troppo a lungo i
  perdenti (per non "realizzare" la perdita e ammettere l'errore). È
  l'esatto opposto di "taglia le perdite, lascia correre i profitti".
- **Panic selling**: nel bear, il dolore cumulato del drawdown (L1.07)
  diventa insopportabile e vendi **sul minimo**, trasformando una perdita
  temporanea in permanente.
- **Antidoto**: regole di uscita decise **a freddo, prima**, e un orizzonte
  temporale onesto. Se un -50% ti farebbe vendere, avevi una position size
  sbagliata in partenza (torna a L2.04, risk management).

## 4. Anchoring — l'ancora del prezzo che ricordi

Ti **ancori** a un numero di riferimento, di solito il prezzo a cui hai
comprato o un massimo storico.

- "Aspetto che torni a quanto l'ho pagato per vendere" — al mercato non
  importa quanto hai pagato tu. Il prezzo di carico è informazione su di
  te, non sull'asset.
- "BTC era a 69k, a 30k è un affare" — l'ancora al massimo precedente fa
  sembrare "economico" qualcosa che potrebbe essere ancora caro.
- **Antidoto**: valuta sempre in avanti ("date queste informazioni, cosa
  mi aspetto *da qui*?"), mai all'indietro rispetto a un'ancora.

## 5. Recency bias — l'ultimo dato pesa troppo

Sovrappesi ciò che è successo **di recente** e lo proietti nel futuro.

- In un bull lungo, "sale sempre" diventa la tua convinzione proprio
  mentre il rischio di reversal cresce.
- **Dove la vedi nei nostri dati**: in Fase 1 abbiamo misurato che le
  **correlazioni cross-asset sono regime-dependent** (rolling std
  0.12-0.17): la correlazione "di adesso" non è quella "di sempre". Il
  recency bias ti fa scambiare il regime corrente per legge eterna.
- **Antidoto**: guardare **sample lunghi** e ragionare per *regimi*, non
  per estrapolazione lineare dell'ultimo mese.

## 6. Confirmation bias — cerchi solo ciò che ti dà ragione

Una volta che hai una posizione, il cervello **filtra le informazioni**:
dai peso alle news che confermano la tua tesi e scarti quelle contrarie.

- Su crypto-Twitter questo è industrializzato: segui gli account che la
  pensano come te, e ti convinci che "tutti" sono bullish/bearish.
- **Antidoto metodologico** (è il cuore del nostro progetto): **scrivi
  l'ipotesi prima di vedere i risultati**. Lo facciamo in ogni notebook
  (H1, H2, H3 scritte sopra il codice). Se l'ipotesi resta scritta, non
  puoi riscriverla a posteriori per darti ragione.

## 7. Herding — il gregge e la riflessività

Gli esseri umani copiano. Nei mercati il gregge crea **bolle** (tutti
comprano perché tutti comprano) e **panico** (tutti vendono perché tutti
vendono). George Soros lo chiamava **riflessività**: le credenze dei
partecipanti cambiano la realtà che credono di osservare.

- Il sentiment delle news è in larga parte **espressione del gregge**: i
  titoli sono entusiasti *dopo* che il prezzo è salito e cupi *dopo* che è
  sceso. Questo ci porta dritti alla sezione 8.

## 8. Caso di studio del progetto: il sentiment non anticipa (e il numero che ci ha quasi ingannato)

In Fase 3 abbiamo costruito una pipeline per misurare, **senza
look-ahead**, se il sentiment delle notizie (e il *volume* di notizie)
anticipa i rendimenti e la volatilità di BTC. Due lezioni, una su ciascun
fronte — psicologica e statistica.

### 8a. Il sentiment è (per lo più) già scontato

Abbiamo trovato che la correlazione tra sentiment giornaliero e
rendimento del giorno dopo è **rumore** (vicina a zero, segno
incoerente). Non è un bug: è **mercato semi-efficiente**. Quando una
notizia diventa titolo di giornale, è già **pubblica** — e il prezzo l'ha
già incorporata. Il sentiment dei titoli è più spesso **concomitante o
lagging** (il gregge della sezione 7 che reagisce) che *leading*. Morale
per l'investitore retail: leggere le news per "anticipare" il mercato è,
in media, inseguire qualcosa che è già successo.

### 8b. Il numero che ci ha quasi ingannato — small-sample bias

In una prima misura, su **23 giorni** di dati, avevamo trovato un segnale
apparentemente interessante: il *volume* di notizie sembrava anticipare la
volatilità con una correlazione di **+0.32**. Promettente, no?

Lo abbiamo segnalato come **"indicativo, da verificare"** — non come
scoperta. E abbiamo fatto bene: quando la storia è cresciuta a **143
giorni**, quella correlazione **è svanita** (≈ −0.07). Il +0.32 era un
**artefatto del piccolo campione**: con pochi punti, *qualche*
correlazione spuria emerge sempre, per puro caso.

Questo è lo **small-sample bias**, ed è il cugino quantitativo del recency
bias (sezione 5): scambiare poco rumore per un segnale. È esattamente il
meccanismo con cui funziona il marketing dei "guru":

- "Il mio segnale ha azzeccato 8 trade su 10!" — su 10 trade, è quasi
  irrilevante. Serve un campione grande e **out-of-sample** (L1.10).
- Un backtest brillante su 6 mesi è marketing; uno onesto su 8 anni con
  walk-forward è ricerca.

**La difesa è procedurale**, non intellettuale:
1. **Riporta sempre `n`** (la dimensione del campione) accanto a ogni
   correlazione. Nel nostro codice (`lead_lag_table`) `n` è una colonna
   obbligatoria, di proposito.
2. **Diffida dei numeri belli su pochi dati.** La domanda giusta non è
   "quanto è forte?" ma "su quanti punti, e regge out-of-sample?".
3. **Scrivi l'ipotesi prima** (sezione 6) e accetta l'esito, anche
   "nessun segnale". Documentare ciò che **non** funziona vale quanto
   documentare ciò che funziona — spesso di più.

## 9. La tabella di sopravvivenza

| Bias | Come ti frega | Antidoto procedurale |
|---|---|---|
| FOMO | Compri sul massimo | DCA (non decidi il timing) |
| Loss aversion | Vendi i vincitori, tieni i perdenti | Regole di uscita scritte a freddo |
| Anchoring | Ti aggrappi al prezzo di carico | Ragiona in avanti, non all'indietro |
| Recency | Proietti l'ultimo mese all'infinito | Sample lunghi, ragiona per regimi |
| Confirmation | Leggi solo chi ti dà ragione | Ipotesi scritta *prima* dei dati |
| Herding | Segui il gregge dentro bolle/panico | Processo automatico, non discrezione |
| Small-sample | Scambi rumore per segnale | Riporta `n`, pretendi out-of-sample |

## 10. Il punto

Non puoi spegnere questi bias: sono cablati. Ma puoi **costruire un
processo che li rende irrilevanti** nei momenti in cui contano. Tutto il
nostro progetto è, in fondo, un esercizio di questo tipo: ipotesi scritte
prima, walk-forward, niente look-ahead, `n` sempre in vista, e
l'onestà di pubblicare anche gli esperimenti falliti. Il sentiment delle
news che non anticipa il prezzo non è un fallimento del progetto: è il
progetto che **funziona** — perché ci ha impedito di crederci.

> **Collegamenti**: L1.07 (volatilità/drawdown, il dolore reale), L1.10
> (cosa NON è il trading), L2.04 (risk management), L2.08 (cicli e
> regimi). Sul lato codice: `src/ai/lexicon/` (sentiment Layer 1),
> `src/features/news_features.py` (`lead_lag_table` con `n`),
> `notebooks/06_news_sentiment_leadlag.ipynb` (l'esperimento di questa
> sezione). Decisioni: ADR-023 (Layer 1 lessico), ADR-024 (anti-look-ahead).
