# L2.08 — Cicli e regimi di mercato: bull, bear, sideways

> Capitolo della Fase 5. Se questo progetto ha una scoperta centrale, è
> questa: **la variabile che conta non è "dove va il prezzo domani" ma "in
> che tipo di mercato sei oggi"**. Il codice dei regimi
> (`src/features/regime.py`) alimenta la dashboard che consulti, e i numeri
> di questo capitolo escono dai notebook 09 e dal layer probabilistico su
> 14 anni di dati — inclusa la parte scomoda: cosa i regimi *non* sanno fare.

## 1. Cos'è un regime

Un **regime** è uno stato persistente del mercato in cui le regole del
gioco cambiano: media dei rendimenti, volatilità, correlazioni — tutto si
sposta. I nomi classici:

- **Bull**: tendenza al rialzo, ribassi comprati in fretta
- **Bear**: tendenza al ribasso, rimbalzi venduti in fretta
- **Sideways/laterale**: nessuna tendenza, oscillazione in un intervallo

La prova che i regimi esistono l'abbiamo misurata già in Fase 1: le
correlazioni mobili tra asset **non sono stabili** (deviazioni standard
0,12-0,17 su finestre rolling) — il mercato non è un processo unico, è
una sequenza di processi diversi.

## 2. Come li classifichiamo (in modo trasparente)

Questo progetto usa regole **semplici, dichiarate e causali** (niente
modelli-scatola-nera; ogni etichetta al giorno *t* usa solo dati fino a
*t*):

- **Trend**: prezzo sopra la sua media a 200 giorni → *bull*; sotto →
  *bear*. Grezzo? Sì. Ma trasparente, non ottimizzato, e chiunque può
  verificarlo.
- **Volatilità**: volatilità recente sopra/sotto la propria baseline
  storica → *alta/bassa*.
- **Combinazione**: 2×2 = quattro stati: `bull_low_vol`, `bull_high_vol`,
  `bear_low_vol`, `bear_high_vol`.

## 3. Il risultato che giustifica tutto il capitolo

Decomposizione del rendimento di BTC per i quattro stati (dati reali,
out-of-sample, notebook 09):

| Stato | Sharpe |
|---|---|
| bull + alta volatilità | **+2,97** |
| bull + bassa volatilità | +1,55 |
| bear + bassa volatilità | −0,81 |
| bear + alta volatilità | **−1,20** |
| *Media di tutto il periodo* | *+0,64* |

Guarda l'ultima riga: lo Sharpe "medio" di BTC (+0,64) **non esiste in
nessun regime reale**. È la media tra un mercato meraviglioso e uno
terribile — un artefatto statistico, come la temperatura media tra il
forno e il congelatore. Chi ragiona sulla media si prepara per un mercato
che non incontrerà mai.

E il pattern non è solo crypto: sul layer probabilistico costruito su
**20 ETF settoriali, 2012-2026**, i rendimenti forward migliori arrivano
storicamente **dopo** le fasi `bear_high_vol` (il rimbalzo post-panico:
+7% medio a 3 mesi), mentre lo stato più insidioso è `bear_low_vol` — il
mercato che scivola in silenzio, senza il panico che di solito precede i
minimi. L'asse informativo, nei nostri dati, è **il regime — non il
momentum**: inseguire i settori più forti, da solo, non ha dato edge (a 3
mesi ha fatto *peggio* della media, confermato out-of-sample).

## 4. La parte onesta: cosa i regimi NON sanno fare

Qui il capitolo si guadagna la fiducia. Abbiamo testato anche l'uso
"da manuale" dei regimi: dare al modello predittivo l'informazione sul
regime per migliorare le previsioni direzionali giornaliere. Risultato
(notebook 09, n=2430 giorni out-of-sample):

> Accuratezza direzionale: 49,8% senza regime → 51,0% con regime.
> Differenza dentro il rumore statistico. **Nessun edge predittivo.**

Quindi il regime **non ti dice cosa farà il prezzo domani**. Ti dice cosa
aspettarti *mentre ci sei dentro*: che distribuzione di rendimenti, che
volatilità, che drawdown è normale in questo stato. È **contesto**, non
profezia — e il contesto, come mostra la tabella del §3, vale moltissimo.

È anche il meccanismo dietro il risultato del momentum (L2.01, L2.05): il
suo valore misurato non è prevedere, è **essere fuori durante i
bear** — cioè usare il regime come filtro di rischio.

## 5. Il laterale: il regime dimenticato

Il sideways merita una nota perché è il regime in cui muoiono più
strategie. Nel laterale:

- i segnali di **trend** (medie, momentum) producono whipsaw a
  ripetizione — entri e vieni stoppato, in loop, pagando costi ogni volta;
- i segnali di **mean reversion** (RSI agli estremi) funzionano meglio;
- la cosa spesso più redditizia è **non fare nulla**.

Il nostro caso LINK (L2.01 §6) è la versione crypto di questa lezione: il
filtro di trend che protegge BTC ed ETH, su un asset che alterna strappi
e lunghi range, fa più danni che benefici.

## 6. Come usarli in pratica

1. **Prima il regime, poi lo strumento**: chiediti "sono in trend o in
   range? La volatilità è calma o agitata?" *prima* di leggere qualsiasi
   indicatore (L2.01 §7).
2. **Calibra le aspettative sul regime, non sulla media storica**: il
   drawdown "normale" di un bear non è quello medio del decennio.
3. **Nei bear ad alta volatilità, la storia dice: non è il momento di
   scappare** — è lo stato *dopo* il quale i rimbalzi sono stati
   storicamente migliori. (Statistica, non garanzia.)
4. **Diffida di chi annuncia i cambi di regime in anticipo**: le nostre
   etichette, come tutte, sono **retrospettive di qualche settimana** (la
   SMA200 conferma tardi). Il regime si riconosce, non si prevede.

## 7. Collegamenti

- **L1.07** — Volatilità: il mattone della classificazione
- **L2.01** — Indicatori: quale funziona in quale regime
- **L2.05** — Drawdown: vive quasi tutto nei bear
- **L2.09** — Halving: il "ciclo dei cicli" specifico di Bitcoin
- Nel codice: `src/features/regime.py` (`classify_regime`,
  `classify_vol_regime`, `combine_regimes`), notebook 09 (i numeri del §3-4)
