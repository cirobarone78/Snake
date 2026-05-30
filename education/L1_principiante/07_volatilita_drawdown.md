# L1.07 — Volatilità e drawdown: cosa significano davvero

> "Volatilità" e "drawdown" sono parole che senti dire ovunque, spesso
> in contesti dove "rischio" andrebbe altrettanto bene. Ma sono cose
> diverse, misurate diversamente, e ti fanno male in modi diversi.
> Distinguerle è uno dei salti concettuali più utili di L1.

## 1. Volatilità: definizione operativa

La **volatilità** misura **quanto** un prezzo oscilla, indipendentemente
dalla direzione. Un asset che sale ogni giorno dell'1% è poco volatile.
Un asset che fa +5%, −3%, +7%, −4% è molto volatile, anche se a fine
settimana è praticamente fermo.

Misura standard: la **deviazione standard** dei rendimenti su una
finestra temporale. In pratica:
- Prendi i rendimenti giornalieri (es. log-return)
- Calcoli la deviazione standard

Più ampia è la "fascia" tipica in cui oscillano i rendimenti, più alta
è la volatilità.

### Annualizzazione

I rendimenti giornalieri hanno una loro std. Ma chi ti dice "vol
annualizzata del 65%" non sta usando i rendimenti annuali — sta
**estrapolando** la std giornaliera assumendo un fattore tempo. La
formula classica: std_daily × √365 (per asset 24/7 come crypto) o
× √252 (per asset con calendari di trading limitati come azioni).

Esempio dai nostri dati EDA (notebook 01, per i 5 Tier 1):

| Asset | std giornaliera (log-return) | Vol annualizzata |
|---|---|---|
| BTC | 3.4% | **65%** |
| ETH | 4.5% | 85% |
| LINK | 6.0% | 115% |
| SOL | 6.3% | 119% |
| POL | 7.1% | **136%** |

Per confronto, i mercati equity tradizionali (S&P 500) hanno vol
annualizzata storicamente del 15-20%. **BTC è ~4x più volatile delle
azioni; POL è ~7x.**

### Cosa la vol NON ti dice

Cose che la gente confonde con "volatilità", ma sono diverse:

- **Direzione**: vol è simmetrica, non distingue tra "su" e "giù". Un
  asset che oscilla violentemente in salita ha alta vol e ti rende
  felice. Uno che oscilla in discesa ha alta vol e ti rende infelice.
  La vol non ti dice quale dei due
- **Rischio di rovina**: avere vol alta NON significa "perderai i
  soldi". Un asset volatile in trend positivo (BTC 2020-2021) ti dà
  rendimenti positivi enormi *grazie* alla vol
- **Probabilità di "vita o morte"**: la vol misura il *centro* della
  distribuzione (la dispersione standard), non i tail extremi. Per i
  tail c'è la kurtosis (notebook 01 EDA: BTC kurtosis ~15, molto più
  fat-tailed di una normale)

### Vol come "energia"

Metafora utile: la volatilità è come l'**energia cinetica** dell'asset.
Tanta energia = tanto movimento. Il movimento può essere produttivo
(salire) o distruttivo (scendere), ma l'energia in sé è neutra. È il
contesto (trend, drawdown, posizione tua) che decide se quell'energia
ti aiuta o ti danneggia.

## 2. Drawdown: il dolore vero

Il **drawdown** misura una cosa molto specifica: **quanto sei sotto
rispetto al massimo precedente**.

### Definizione precisa

In ogni momento `t`:
- Trova il massimo storico del prezzo (o dell'equity di portafoglio)
  fino a `t`
- Calcola: (prezzo al tempo `t` / massimo) − 1

È quasi sempre negativo (al massimo è zero, quando sei sopra il
precedente massimo). Quel valore è il drawdown corrente.

### Massimo drawdown (max DD)

Il **max drawdown** è il valore più negativo del drawdown nella tua
finestra temporale. È **la peggior perdita "non realizzata" che hai
sopportato** dall'inizio del trade.

### Esempi storici BTC

| Periodo | Max DD | Note |
|---|---|---|
| 2018-2019 | **−84%** | Da $20k a $3.2k post bull run 2017 |
| Mar 2020 (COVID) | −52% | Crash repentino, recuperato in 2 mesi |
| 2022 (Terra/FTX) | **−77%** | Da $69k a $15.5k, 14 mesi di sofferenza |
| 2024-2025 | −34% (sample) | Più contenuto, fase post-ETF |

Significato pratico: chi ha comprato BTC al picco del 2017 ha **sopportato
84% di perdita non realizzata** prima di rivedere lo zero. Sopravvivere
psicologicamente a un drawdown dell'80% è molto più difficile di quanto
le persone si aspettano.

### Tempo di recupero (recovery time)

Una metrica spesso ignorata ma cruciale: **quanto tempo passa dal
massimo al recupero del massimo**.

- BTC 2017 picco → recupero: ~3 anni (2020 fine)
- BTC 2021 picco $69k → recupero: ~3 anni (2024 fine via ETF)
- S&P 500 2007 picco → recupero: ~5 anni (2013, includendo dividendi)

Più lungo è il recupero, più cresce la tentazione di vendere "alla
fine" del drawdown — proprio prima del recupero. È il modo statistico
più frequente per chi perde soldi nel lungo periodo.

### Time underwater

Generalizzazione del recovery time: **la frazione del tempo totale in
cui sei sotto al massimo precedente**. Per un asset con drawdown
frequenti e lenti, time underwater può essere 70-80% — passi più
tempo "in rosso rispetto al picco" che in nuovi massimi.

## 3. Volatilità ≠ drawdown

Sono **misure diverse di rischio diverse**.

### Differenze pratiche

- **Vol** è una statistica *aggregata*: dice "in media oscilla così
  tanto". Non dice quando, non dice in che direzione, non dice cosa
  succede negli estremi
- **Max DD** è un *evento storico singolo*: il peggior momento. Risponde
  a "quanto male può andare?"

### Casi che illustrano la differenza

**Asset A** (alta vol, basso DD): asset che oscilla violentemente ma è
in trend positivo costante. La vol è alta perché ogni giorno il prezzo
si muove molto. Ma il drawdown rimane piccolo perché ogni dip viene
rapidamente recuperato e sorpassato.

**Asset B** (bassa vol, alto DD): asset che si muove poco ogni giorno
ma in un solo trend lento di discesa per anni. Vol moderata (deviazione
standard giornaliera contenuta), drawdown enorme (perdita cumulativa
del 50%).

Esempi reali: gli **stablecoin algoritmici** prima del de-peg avevano
vol bassissima... fino al de-peg di UST (Terra) nel maggio 2022, dove
in pochi giorni hanno perso il 99%. Il rischio non era nella vol
giornaliera, era nei tail e nei drawdown latenti.

### Quale guardare quando

- **Vol annualizzata** è utile per:
  - Confrontare asset (BTC vs ETH vs SOL: chi è più "agitato"?)
  - Position sizing (più alto vol → meno peso a parità di tolleranza
    al rischio)
  - Risk parity weighting
- **Max DD** è utile per:
  - Capire il "worst case" sopportato storicamente
  - Stress test della tua tolleranza emotiva ("sopravviverei a
    −80%?")
  - Confronto strategie: due strategie possono avere lo stesso
    rendimento e la stessa vol, ma drawdown molto diversi
- **Time underwater** è utile per:
  - Capire la "stress chronique": passare 3 anni sotto il massimo
    erode la motivazione anche se alla fine recuperi

## 4. Misure derivate che vedrai

Senza formule, solo per familiarità:

- **Sharpe ratio**: rendimento medio per unità di vol. Più alto =
  meglio (a parità di vol fai più rendimento). 0.5-1 è "decente",
  1+ è "buono", 2+ è "raro/sospetto" out-of-sample
- **Sortino ratio**: come Sharpe ma usa solo la vol **downside**.
  Premia chi non oscilla violentemente nelle perdite. Più "umano"
  come metrica
- **Calmar ratio**: rendimento annuale / max drawdown. Risponde a
  "quanto rendi rispetto al peggior dolore?"
- **Profit factor**: somma profitti / somma perdite. Sopra 1 sei
  in attivo

Tutte queste sono concetti L3 in profondità ma le menzioniamo perché
appariranno nel sistema in Fase 2.

## 5. Volatility clustering: la vol non è costante

Una cosa che i nostri notebook EDA hanno reso visibile: la volatilità
**non è uniforme nel tempo**. Periodi di calma alternati a periodi di
agitazione, e questi pattern hanno **memoria**.

ACF(|r|) dei nostri dati (notebook 01):
- BTC: 0.16 al lag 1, 0.14 al lag 5
- POL: 0.26 al lag 1, 0.22 al lag 5

Significa: se ieri la vol era alta, anche oggi è probabile sia alta.
Se ieri era calma, anche oggi è probabile sia calma. Questa **memoria
della vol** si chiama **volatility clustering** ed è una proprietà
universale dei mercati finanziari.

Implicazione: i modelli di vol non sono "media costante", sono
**GARCH-like** — stimano una vol condizionale che cambia nel tempo. Lo
vedremo concretamente in Fase 2.

## 6. Collegamento al nostro progetto

In Fase 2 (baseline tecnica & backtest, vedi ROADMAP) la suite di
metriche includerà:
- Sharpe, Sortino, Calmar
- Max drawdown e time underwater
- Vol annualizzata (rolling e full-sample)
- Profit factor

L'obiettivo non è "massimizzare la vol" né "minimizzarla". È capire
quanto vol stiamo prendendo per quanto rendimento, e confrontarlo con
i benchmark (buy-and-hold e DCA, vedi L1.06).

I dati Fase 1 (notebook 01) sono già un'analisi descrittiva di vol e
distribuzioni per i 5 Tier 1. In Fase 2 li trasformeremo in:
- Modello di vol condizionale (GARCH baseline)
- Curva drawdown del portafoglio paper trade vs benchmark
- Reporting onesto di "underwater periods"

ADR-007 nei nostri output del modello include esplicitamente
"volatilità attesa" come una delle dimensioni. Vol non è una
preoccupazione, è una **dimensione di output** del sistema, perché
sapere se domani il movimento atteso è in un range stretto o ampio è
informazione utile separata dalla direzione.

## Glossario rapido

- **Volatilità**: misura della dispersione tipica dei rendimenti di
  un asset. Solitamente std dei log-return, annualizzata
- **Vol annualizzata**: std giornaliera × √(giorni nel anno). 365 per
  crypto, 252 per equity
- **Drawdown**: differenza percentuale tra il valore corrente e il
  massimo storico precedente. Sempre ≤ 0
- **Max drawdown (max DD)**: il drawdown peggiore in una finestra
  temporale. La "peggior perdita non realizzata sopportata"
- **Recovery time**: tempo che passa dal massimo precedente al
  ritorno a quel livello
- **Time underwater**: frazione del tempo in cui sei sotto al
  massimo precedente
- **Sharpe ratio**: rendimento per unità di vol
- **Sortino ratio**: come Sharpe ma solo vol al ribasso
- **Calmar ratio**: rendimento annuale / max DD
- **Volatility clustering**: la vol ha "memoria" (periodi calmi
  seguiti da periodi calmi, periodi agitati da periodi agitati).
  Proprietà universale dei mercati
- **GARCH**: famiglia di modelli che stimano vol come funzione della
  vol passata. Lo standard de facto per modellare vol condizionata
- **Fat tails**: la distribuzione dei rendimenti ha "code spesse",
  cioè eventi estremi più frequenti di quanto predirebbe una
  distribuzione normale

## Cosa portare via

- **Vol e drawdown misurano cose diverse**. La vol è la "energia
  cinetica" del prezzo, simmetrica e senza memoria della direzione.
  Il drawdown è il dolore reale: quanto sei sotto al massimo
- **BTC ha vol ~65% annua, POL ~136%**. Significa che le altcoin
  small/mid cap sono 2x più "agitati" di BTC. Position sizing dovrebbe
  riflettere questo
- **Max drawdown di BTC è stato −84% (2018)**. La domanda "sopravvivo
  emotivamente?" va fatta a freddo, non quando già sei dentro
- **Time underwater conta** quanto il max DD. Stare anni "in rosso
  rispetto al picco" erode la disciplina più di un crash veloce
- **Vol bassa NON significa "sicuro"**. UST (Terra) aveva vol
  giornaliera vicina a zero finché non è collassata del 99%. Il vero
  rischio sono i tail, non il centro della distribuzione
- **Volatility clustering** è una proprietà reale: la vol di oggi è
  correlata a quella di ieri. Modelli GARCH catturano questo. Vol
  costante è una semplificazione comoda ma sbagliata
- Nel nostro progetto, **vol è una dimensione di output** (ADR-007),
  non solo una metrica di valutazione

---

*Prossimo capitolo*: L1.08 — Custodia: cold/hot wallet vs custodia su
exchange.
