# L2.07 — DCA vs lump sum: i numeri reali, non le opinioni

> Ci sono pochi dibattiti più inquinati dalle opinioni di "meglio entrare
> tutto subito o un po' alla volta?". Questo capitolo lo tratta come il
> progetto tratta tutto: **un esperimento**. I numeri qui sotto sono stati
> calcolati sui prezzi reali di BTC 2018-2026 col codice del repo
> (`dca_equity` in `src/backtest/benchmark.py`), su 68 finestre di 3 anni
> con ingressi mensili. Riproducibile, come sempre.

## 1. Le due strategie, definite bene

- **Lump sum (LS)**: hai un capitale, lo investi **tutto oggi**.
- **DCA** (Dollar-Cost Averaging, L1.06): lo stesso capitale, investito
  **a rate fisse a cadenza fissa** (es. 100 al mese per 3 anni),
  qualunque cosa faccia il prezzo.

Il confronto onesto richiede **stesso capitale totale e stessa finestra**:
LS mette tutto al giorno zero, DCA lo distribuisce. Ogni altro confronto
(capitali diversi, orizzonti diversi) è propaganda per l'una o l'altra.

## 2. I numeri, misurati su BTC (68 finestre di 3 anni, 2018-2026)

| Metrica | Lump sum | DCA |
|---|---|---|
| Vince il confronto | **71% delle finestre** | 29% |
| Rendimento mediano | **+161%** | +102% |
| Caso migliore | +1399% | +665% |
| Caso peggiore | +1% | −6% |
| Finestre chiuse in perdita | 0% | 4% |

E i due casi estremi, che sono la vera lezione:

- **Peggior ingresso per il LS** (aprile 2021, comprare il massimo del
  ciclo): LS **+1%** in tre anni... contro DCA **+103%**. È lo scenario
  da incubo che il DCA esiste per neutralizzare.
- **Miglior ingresso per il LS** (novembre 2018, comprare il minimo):
  LS **+1399%** contro +498%. Quando il timing è perfetto, diluirlo costa
  caro.

## 3. Perché il lump sum vince "di solito"

Non è un mistero, è aritmetica: se un asset **sale più spesso di quanto
scende** (e sul lungo periodo i mercati che sopravvivono lo fanno), ogni
euro tenuto fuori dal mercato in attesa della prossima rata perde, in
media, rendimento. Il DCA è strutturalmente "in ritardo" su un trend
rialzista: il 71% misurato su BTC è la stessa proporzione (~2/3) che studi
analoghi trovano sull'azionario da decenni. Su questo i dati sono
concordi e non vale la pena discuterli.

## 4. Ma allora perché il DCA? Le due cose che i numeri medi nascondono

**Primo: il DCA è un'assicurazione sul timing.** Guarda di nuovo il caso
aprile 2021: chi entrò tutto insieme sul massimo passò *tre anni* per
tornare in pari. Il DCA comprime drasticamente la differenza tra entrare
"nel momento giusto" e "nel momento sbagliato" — e tu **non sai mai** in
quale dei due sei. Come lo stop loss (L2.04 §5), il DCA in media *costa*
(la differenza mediana +161% vs +102% è il premio) e nei casi peggiori
*salva*. Stessa struttura: assicurazione.

**Secondo — e controintuitivo: il DCA non è "più sicuro" sempre.** Nota
la riga strana della tabella: nelle nostre finestre il LS non ha *mai*
chiuso in perdita, il DCA sì (4% dei casi). Come è possibile? Se il prezzo
sale a lungo e crolla **alla fine della finestra**, il DCA ha comprato
per anni a prezzi crescenti (prezzo medio di carico alto) e il crollo
finale lo porta sotto — mentre il LS, entrato in basso all'inizio, resta
in attivo. Il DCA sposta il rischio: dal *giorno di ingresso* al *profilo
dell'intero percorso*. Non lo elimina.

*(Onestà sul campione: 2018-2026 è un periodo con forte crescita
complessiva di BTC, il che favorisce il LS nel conteggio delle vittorie.
Ma le due lezioni strutturali — assicurazione sul timing, rischio
spostato non eliminato — non dipendono dal periodo.)*

## 5. Il fattore decisivo che nessuna tabella cattura: tu

Il confronto matematico presuppone che tu *rimanga investito*. Ma L2.06
(bias cognitivi) ha mostrato il vero anello debole: un LS che va subito
−30% attiva panic selling con una probabilità molto più alta di un piano
DCA in corso — che anzi, nel ribasso, "compra a sconto" e dà una
struttura psicologica per continuare.

La strategia ottima sulla carta che abbandoni al primo drawdown rende
**meno** della strategia subottimale che riesci a seguire per dieci anni.
Su questo, il DCA non ha rivali: trasforma la decisione più difficile
(quando entrare) in nessuna decisione.

## 6. In pratica: quale scegliere

- **Capitale già disponibile + stomaco testato** (hai già vissuto un
  drawdown vero senza vendere) → il LS è statisticamente superiore, e i
  nostri numeri lo confermano.
- **Capitale già disponibile + primo rodeo** → DCA su 6-18 mesi: paghi un
  premio mediano misurabile in cambio dell'azzeramento del rischio
  "entrato sul massimo" e di una probabilità molto più alta di *restare*
  investito.
- **Reddito mensile da investire** → il dilemma non esiste: il DCA è
  l'unica opzione, e ha pure il pregio di essere quella che ti protegge
  dai tuoi bias. (È il caso previsto dal progetto stesso: il paper
  trading di Fase 6 usa proprio contributi mensili come benchmark.)
- In ogni caso: la scelta LS/DCA conta **meno** di size corretta (L2.04),
  costi bassi (L1.04) e capacità di non vendere nel panico (L2.06). Non
  perdere il sonno sul 2° decimale avendo sbagliato l'ordine di grandezza.

## 7. Collegamenti

- **L1.06** — DCA: il come; qui il *se* e il *quanto costa*
- **L2.04** — Risk management: la stessa logica assicurativa dello stop
- **L2.05** — Drawdown: cosa il DCA cambia (e non cambia) del percorso
- **L2.06** — Bias: il motivo per cui la risposta "razionale" può essere sbagliata *per te*
- Nel codice: `src/backtest/benchmark.py` (`dca_equity`, nessun
  look-ahead), lo studio di questo capitolo è rifacibile in poche righe
