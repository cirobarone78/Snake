# L2.01 — Indicatori tecnici: medie mobili, MACD, RSI, Bollinger

> Capitolo della Fase 2 (baseline tecnica). Ogni indicatore descritto qui
> **esiste come codice testato in questo progetto**
> (`src/features/indicators.py`) ed è stato messo alla prova su dati reali
> nei notebook 04 e 05. Per questo il capitolo può permettersi una cosa che
> i manuali di trading di solito evitano: dirti **quanto funzionano
> davvero**. Spoiler: meno di quanto promettono, ma non zero — e capire
> *dove* sta il valore residuo è l'intera lezione.

## 1. Cosa è (e cosa non è) un indicatore tecnico

Un indicatore tecnico è una **trasformazione matematica del prezzo** (e a
volte del volume). Niente di più: non ha accesso a informazioni che il
grafico non contenga già. Media, differenza, normalizzazione — tutto quello
che un indicatore "sa" è già nel prezzo.

Da qui la prima regola, che vale per tutto il capitolo:

> **Dieci indicatori sul grafico non sono dieci opinioni indipendenti.**
> Sono la stessa informazione (il prezzo) cucinata in dieci modi diversi.
> Se RSI, MACD e stocastico "confermano" tutti lo stesso segnale, non hai
> tre conferme: hai una sola informazione ripetuta tre volte.

## 2. Medie mobili: SMA ed EMA

La **media mobile semplice (SMA)** a N giorni è la media degli ultimi N
prezzi di chiusura. La **media mobile esponenziale (EMA)** pesa di più i
giorni recenti, quindi reagisce prima.

- **A cosa servono**: *lisciare* il rumore per vedere la tendenza. Il
  prezzo sopra la SMA200 è la definizione operativa più comune di "trend
  rialzista di lungo periodo" — è esattamente la soglia che questo progetto
  usa per classificare i **regimi bull/bear** nella dashboard.
- **Il difetto strutturale**: il **ritardo (lag)**. Una media di 200 giorni
  "vede" il crollo di oggi con il peso di 1/200. Le medie confermano i
  trend, non li anticipano — per costruzione.
- **Crossover**: il classico segnale "media veloce incrocia la lenta"
  (golden cross / death cross). Funziona magnificamente *nei trend lunghi*
  e ti massacra di falsi segnali *nei mercati laterali* (il famigerato
  **whipsaw**: entri, gira, esci in perdita, rigira, rientri più su).

## 3. MACD: la distanza tra due medie

Il **MACD** (Moving Average Convergence Divergence) è costruito così:

1. `linea MACD` = EMA a 12 giorni − EMA a 26 giorni
2. `signal` = EMA a 9 giorni della linea MACD
3. `istogramma` = MACD − signal

In italiano: misura **quanto la media veloce si sta allontanando dalla
lenta** (il momentum del trend) e se questa distanza sta crescendo o
calando. MACD sopra lo zero = la veloce è sopra la lenta = trend su.
L'istogramma che si contrae = il trend sta perdendo spinta.

È un indicatore *di momentum derivato dalle medie*: eredita il loro lag e
il loro comportamento (bene nei trend, male nel laterale).

## 4. RSI: il termometro dell'eccesso

L'**RSI** (Relative Strength Index, formulazione di Wilder, 14 giorni)
confronta la grandezza media delle salite recenti con quella delle discese
recenti, e la schiaccia in una scala 0–100:

- **> 70** = "ipercomprato": il rialzo recente è stato inusualmente
  unilaterale
- **< 30** = "ipervenduto": idem per il ribasso

Due cose da capire assolutamente:

1. **Ipercomprato non significa "sta per scendere".** Nei trend forti
   l'RSI può restare sopra 70 per settimane mentre il prezzo continua a
   salire. Significa solo: *il movimento è esteso, la probabilità di una
   pausa/consolidamento è più alta del solito*.
2. L'RSI è più informativo **nei mercati laterali** (dove gli estremi
   tendono a rientrare) che nei trend (dove gli estremi persistono).
   È l'immagine speculare delle medie mobili.

*Esempio reale dal progetto*: nell'analisi di un titolo healthcare USA al
nuovo massimo annuale, l'RSI a 71 con prezzo +24% sopra la SMA200 non
diceva "vendi": diceva "il rialzo è esteso, se hai un profitto proteggilo
con una regola" (vedi L2.04, risk management). Lo storico di quel titolo
mostrava rendimenti *mediamente negativi* nei 5-10 giorni successivi ai
nuovi massimi — un'informazione statistica, non una profezia.

## 5. Bande di Bollinger: la volatilità disegnata

Le **Bollinger Bands** sono tre linee: una SMA a 20 giorni (banda
centrale), più/meno 2 deviazioni standard *mobili* (bande esterne).

- Quando la volatilità sale, le bande **si allargano**; quando il mercato
  si calma, **si stringono** (squeeze).
- Il prezzo che tocca la banda esterna **non è un segnale di inversione**:
  è la definizione statistica di "movimento da 2 sigma". Nei trend forti
  il prezzo *cammina sulla banda* per giorni.
- L'uso più sensato è come **misura di contesto**: bande strette = energia
  compressa, spesso prima di un movimento direzionale; bande larghe =
  regime agitato, i segnali di momentum sono meno affidabili.

Nel progetto le bande usano la deviazione standard di popolazione
(convenzione dei charting tool) — dettaglio implementativo che trovi
documentato nel codice, perché anche i dettagli contano quando confronti i
tuoi numeri con quelli di una piattaforma.

## 6. La prova sul campo: cosa dicono i NOSTRI dati

Qui il capitolo si separa dai manuali. Questo progetto ha fatto il
backtest onesto (walk-forward, out-of-sample, costi inclusi) di una
strategia basata su medie/momentum, su BTC, ETH, SOL, LINK, POL — anni di
dati reali. Risultati, senza trucco:

| Domanda | Risposta empirica |
|---|---|
| Il momentum indovina la direzione di domani? | **No.** Accuratezza direzionale ~50% (moneta) su tutti gli asset |
| Allora è inutile? | **No.** Batte comprare-e-tenere su 4 asset su 5 — ma per un motivo diverso |
| Quale motivo? | **Difensivo**: sta fuori dal mercato nei crolli. Nei bear dimezza il drawdown (BTC: −50% vs −77%) |
| Il risultato dipende dal parametro scelto? | Poco: regge su lookback da 20 a 100 giorni (una "collina", non un picco fortunato) |
| Funziona su tutto? | **No.** Su LINK il filtro fa più danni che benefici — la robustezza va verificata asset per asset, mai assunta |

La sintesi da portare a casa:

> Gli indicatori tecnici **descrivono lo stato presente** del mercato
> (trend, momentum, estensione, volatilità). Il loro valore misurato, in
> questo progetto, non è la previsione — è la **gestione del rischio**:
> sapere in che regime sei e stare fuori dai periodi peggiori. Chi te li
> vende come macchine da profitto ti sta vendendo il pezzo che i nostri
> dati non hanno mai trovato.

## 7. Errori tipici (visti anche nei nostri esperimenti)

1. **Ottimizzare i parametri sul passato** ("RSI a 13,5 giorni rendeva di
   più!") → overfitting. Se il risultato cambia radicalmente spostando il
   parametro, non era un segnale: era rumore memorizzato.
2. **Ignorare i costi**: nel nostro backtest, fee+slippage mangiano il
   25-30% del rendimento lordo di una strategia di momentum. Un segnale
   che tradea spesso deve battere il mercato *e* il proprio conto spese.
3. **Confondere descrizione e previsione**: "RSI 75, quindi domani
   scende". No: "RSI 75, quindi il movimento è esteso". Sono frasi
   diverse, e la seconda non ti dice cosa fare domani.
4. **Indicatore giusto, mercato sbagliato**: momentum nel laterale e RSI
   nel trend producono entrambi segnali sistematicamente cattivi. Prima il
   regime (L2.08), poi l'indicatore.

## 8. Collegamenti

- **L1.03** — Lettura del grafico (candele, volumi: i mattoni)
- **L2.04** — Risk management: cosa fare *davvero* con questi segnali
- **L2.05** — Drawdown: la metrica che il momentum difensivo migliora
- **L2.08** — Cicli e regimi: il contesto che decide quale indicatore ha senso
- Nel codice: `src/features/indicators.py` (implementazioni testate, con
  test di non-look-ahead), notebook `04` e `05` (i backtest citati)
