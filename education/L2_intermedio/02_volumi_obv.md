# L2.02 — Volume, OBV e "volume di attenzione": cosa raccontano gli scambi

> Il prezzo dice *cosa* è successo; il volume dice **con quanta
> convinzione**. Questo capitolo copre il volume di scambio classico e
> l'OBV (implementato in `src/features/indicators.py`), più due lezioni
> che questo progetto ha imparato sul campo: una trappola reale dei dati
> di volume (documentata nel nostro registro delle domande aperte) e un
> "volume" non convenzionale — il volume di **copertura mediatica** — che
> usiamo nella dashboard Eventi.

## 1. Il volume come qualità del movimento

Il **volume** è la quantità scambiata in un intervallo. La sua lettura
base è come *qualificatore* del prezzo:

- **Movimento + volume alto** = tanti partecipanti coinvolti: il
  movimento "ha benzina", più probabile che rifletta un vero cambio di
  valutazione.
- **Movimento + volume basso** = pochi scambi lo hanno prodotto: più
  fragile, più facilmente rumore o manipolazione (soprattutto su asset
  piccoli).
- **Breakout su volume anemico** = il classico falso segnale da manuale.

Attenzione però a non farne una legge: è una *regola di plausibilità*,
non un teorema. Anche il volume, come tutti gli indicatori (L2.01 §1),
descrive — non prevede.

## 2. OBV: il volume con la firma

L'**On-Balance Volume** somma il volume dei giorni di rialzo e sottrae
quello dei giorni di ribasso: una corsa cumulativa che chiede *"gli
scambi grossi stanno avvenendo in salita o in discesa?"*.

L'uso interessante è la **divergenza**: prezzo che fa nuovi massimi con
OBV che non li fa = i rialzi recenti avvengono su volumi sempre più
magri; la spinta si sta esaurendo. Il contrario (OBV che sale col prezzo
fermo) suggerisce accumulo silenzioso.

Nel repo l'OBV è implementato con una convenzione precisa (giorni piatti
= volume ignorato, prima osservazione = zero) — perché anche per un
indicatore "semplice" le scelte di dettaglio cambiano i numeri, e vanno
dichiarate.

**VWAP** (prezzo medio ponderato per il volume) merita una menzione:
è il riferimento degli istituzionali per giudicare l'esecuzione ("ho
comprato sopra o sotto il prezzo medio del giorno?"). Non è implementato
nel progetto — lavoriamo a candele giornaliere, e il VWAP dà il meglio
intraday — quindi ne parliamo solo per onestà di panorama.

## 3. La trappola vera: "quale volume stai guardando?"

Lezione imparata sul campo in questo progetto (registrata come domanda
aperta Q23): per un asset scambiato su più mercati, **il volume dipende
da chi lo conta**:

- Yahoo Finance riporta per le crypto un volume **aggregato
  cross-exchange** (stimato);
- l'API di un singolo exchange riporta **solo il proprio** venue.

Gli stessi giorni, per lo stesso asset, possono mostrare volumi che
differiscono di **ordini di grandezza** tra fonti. Conseguenze pratiche:

1. Mai confrontare livelli assoluti di volume tra fonti diverse.
2. Le feature di volume sensate sono **relative alla propria storia**
   (z-score sulla stessa serie, ratio col proprio rolling), mai al
   volume "grezzo" di un'altra fonte.
3. Un "picco di volume" su una fonte nuova può essere solo l'inizio della
   copertura di quella fonte, non un evento di mercato.

È il motivo per cui questo progetto, per le feature di anomalia, usa
z-score *within-source* — la stessa disciplina che applichiamo ai
rendimenti.

## 4. Il volume non convenzionale: la copertura mediatica

Idea del progetto (implementata in `src/features/news_volume.py`): oltre
al volume di *scambi*, misuriamo il volume di **attenzione** — quanti
titoli di giornale escono ogni giorno su un asset, contro la sua baseline
storica. Un picco di copertura dice "qui sta succedendo qualcosa" anche
quando il tono delle notizie è neutro.

Il caso reale che mostra perché servono *entrambi* i volumi (luglio
2026, dashboard Eventi):

- **Crollo del settore tech (−6,7%)**: picco di copertura enorme (43
  titoli in un giorno, ~8 deviazioni sopra la norma) → evento *pubblico*,
  con catalizzatore mediatico riconoscibile.
- **Crollo di POL (−10,5%), stesso giorno**: **2 titoli**, nessun picco →
  un crollo *senza notizie* (tipico delle liquidazioni a leva), con la
  stampa arrivata il giorno **dopo**.

Prezzo e attenzione insieme distinguono "evento con causa pubblica" da
"meccanica interna di mercato" — nessuno dei due, da solo, ci riesce.
Nella dashboard questo è il badge **"Picco copertura"** sulle card dei
movimenti.

Un dettaglio tecnico che è anche una lezione statistica: i conteggi di
titoli sono numeri piccoli e "granulosi" (alla Poisson). Un feed che fa
4 titoli al giorno, sempre, ha deviazione standard ~zero: il primo giorno
da 30 titoli farebbe esplodere uno z-score ingenuo (divisione per ~0). Il
codice usa un pavimento di rumore (√media) proprio per gestire questo
caso — scoperto, come si deve, da un test che falliva.

## 5. Come usare il volume, in sintesi

1. **Qualificatore, non oracolo**: usa il volume per pesare la
   credibilità di un movimento, non per prevederne il prossimo.
2. **Sempre relativo alla propria storia**: "3× il suo volume mediano a
   30 giorni" è informativo; "volume = 12 miliardi" da solo non lo è.
3. **Occhio alla fonte** (§3): la trappola cross-venue è reale e
   silenziosa.
4. **Due volumi sono meglio di uno**: scambi + attenzione mediatica
   raccontano insieme una storia che separatamente non raccontano.

## 6. Collegamenti

- **L1.03** — Lettura del grafico: dove il volume compare per la prima volta
- **L2.01** — Indicatori: le regole generali valgono anche qui
- **L2.08** — Regimi: il volume si comporta diversamente per regime
- Nel codice: `src/features/indicators.py` (`obv`),
  `src/features/news_volume.py` (volume di copertura, floor di Poisson),
  Q23 nel registro delle domande aperte (la trappola cross-venue)
