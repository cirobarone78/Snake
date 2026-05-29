# L1.05 — Portafoglio e diversificazione

> "Non mettere tutte le uova nello stesso paniere" è uno dei pochissimi
> proverbi finanziari sostenuti da matematica solida. Ma "diversificare"
> non significa "comprare cose a caso". Significa qualcosa di preciso,
> con un meccanismo preciso, e con limiti precisi che la pubblicità
> tende a dimenticare.

## 1. Cosa significa "portafoglio"

Un **portafoglio** è semplicemente l'insieme degli asset che possiedi
in un dato momento, ciascuno con un certo peso. Esempio:

| Asset | Valore (USD) | Peso |
|---|---|---|
| BTC | 4.500 | 45% |
| ETH | 3.000 | 30% |
| SOL | 1.500 | 15% |
| Cash USD | 1.000 | 10% |
| **Totale** | **10.000** | **100%** |

Il portafoglio cambia per due motivi:
- **Operazioni attive**: compri, vendi, ribilanci
- **Movimento del mercato**: se BTC raddoppia mentre ETH è fermo, il
  peso di BTC sale anche senza che tu abbia toccato nulla

## 2. Il rischio di un singolo asset

Un singolo asset ha **due tipi di rischio**:

1. **Rischio sistematico**: muove tutto il mercato (es. recessione,
   crisi globale, shock dei tassi). Non lo puoi eliminare diversificando
   *dentro* la stessa classe (es. comprando 20 crypto): se crolla il
   mercato crypto, crollano tutte.
2. **Rischio specifico (idiosincratico)**: legato a quel singolo asset
   (es. exploit di un protocollo, scandalo aziendale, perdita di
   adoption). Lo puoi ridurre, in teoria fino quasi a zero, con
   abbastanza diversificazione.

La diversificazione attacca **solo** il rischio specifico. Non quello
sistematico. Capire questa distinzione è fondamentale.

## 3. Cosa fa la diversificazione, concretamente

Considera due asset A e B con rendimenti che oscillano. Se compri 50%
di A e 50% di B:

- Se A e B sono **perfettamente correlati** (si muovono identici): il
  tuo portafoglio oscilla esattamente come ciascuno dei due. Non hai
  guadagnato niente in stabilità.
- Se A e B sono **perfettamente anti-correlati** (uno sale quando
  l'altro scende): il tuo portafoglio è quasi piatto. Hai eliminato
  quasi tutto il rischio (ma anche tutto il rendimento atteso, se
  sono simmetrici).
- Caso realistico — **correlazione intermedia**: il portafoglio oscilla
  meno della media dei due. Questa è "diversification benefit".

Più gli asset sono **decorrelati**, più la diversificazione funziona.

### Esempio numerico (senza formule)

Dai notebook EDA del nostro progetto sappiamo:
- BTC vs ETH = 0.81 (molto correlati: sono entrambi crypto, vanno
  insieme)
- BTC vs SPX = 0.39 (positivi ma decorrelati: equity e crypto si
  muovono spesso nella stessa direzione ma non sempre)
- BTC vs GOLD = 0.08 (vicino a zero: oro è quasi indipendente dal
  prezzo BTC)
- BTC vs DXY = -0.21 (correlazione negativa: dollaro forte = crypto
  debole)

Conclusioni operative pratiche:
- **BTC + ETH** insieme: poco beneficio di diversificazione, si muovono
  in tandem
- **BTC + SPX**: beneficio moderato, dirsi parzialmente "risk-on"
  insieme
- **BTC + GOLD**: beneficio reale, sono quasi indipendenti
- **BTC + DXY (long)**: matematicamente è un buon hedge, ma è raro
  vedere portafogli retail con DXY come asset; il concetto si applica
  più a USD cash come "anti-crypto" implicito

## 4. Diversificazione **dentro** una classe vs **tra** classi

### Dentro la stessa asset class

Comprare 10 azioni diverse del S&P 500 invece di 1: stai abbattendo il
rischio specifico (il fatto che una singola azienda fallisca) ma resti
completamente esposto al rischio sistematico (il mercato USA crolla).

Comprare 10 crypto diverse invece di solo BTC: stessa cosa. Una
altcoin individuale può andare a zero (capita), ma se "crolla il
mercato crypto" tutte e 10 crollano insieme.

### Tra asset class diverse

Comprare un mix di azioni + obbligazioni + oro + cash: ognuna risponde
in modo diverso allo stesso evento macro. Una recessione tipica fa:
- azioni → giù (rischio sistematico equity)
- obbligazioni di alta qualità → spesso su (fly to safety)
- oro → spesso su (hedge inflazione/incertezza)
- cash → fermo in valore nominale (perde solo per inflazione, ma è
  liquido)

Questo è il principio del **portafoglio classico 60/40** (60% azioni,
40% obbligazioni) che ha governato il retail USA per decenni. Negli
ultimi anni la sua efficacia è stata messa in discussione perché in
periodi specifici azioni e obbligazioni si sono mosse insieme
(soprattutto 2022). Ma il principio di mescolare asset class diverse
resta valido.

## 5. Quante posizioni bastano davvero?

Una intuizione comune sbagliata: "più asset metto, meglio è". La
matematica dice altro:

- Comprare il **primo** asset elimina il caso "metto tutto su una cosa
  che va a zero"
- Comprare il **secondo** asset, se decorrelato, elimina ancora un
  bel pezzo di rischio
- Dal **decimo asset diversificato** in poi, il beneficio aggiuntivo è
  marginale
- Dal **trentesimo** in poi, stai sostanzialmente ricreando il mercato:
  tanto vale comprare un ETF che lo fa per te

### Per crypto, in pratica

Il nostro Tier 1 (ADR-005) è BTC, ETH, SOL, LINK, POL. Cinque asset.
Dai dati EDA sappiamo che sono correlati 0.5-0.8 tra loro. Il
beneficio di diversificazione dentro questi 5 è **moderato**.

Se vuoi davvero diversificazione, devi uscire dalla classe crypto:
- aggiungere equity (SPX, NDX) → correlazioni 0.30-0.40 con BTC
- aggiungere oro → correlazione vicina a zero
- aggiungere cash USD → diversificazione in senso "tenere polvere asciutta"

## 6. Il peso di ciascun asset: position sizing

Una volta scelti gli asset, **quanto** mettere in ciascuno?

### Pesi uguali (equal weight)

Esempio: 5 asset, 20% ciascuno. Pro: semplice, robusto, non richiede
opinioni. Contro: tratta BTC (market cap $1.5T) e una micro-cap allo
stesso modo, il che è esposto al rischio della micro-cap molto più di
quanto una persona ragionevole vorrebbe.

### Pesi per market cap

Esempio: BTC è il 60% del market cap crypto → BTC pesa 60% nel
portafoglio. È quello che fa un ETF. Pro: rifletta "il mercato
medio". Contro: sei pieno di asset perché sono già grossi, non perché
sono migliori.

### Pesi per convinzione

Esempio: pensi che SOL sia sottovalutato → SOL al 30% anche se è solo
il 2% del market cap crypto. Pro: rispecchia la tua tesi. Contro: ti
esponi al rischio specifico più di quanto la diversificazione
permetterebbe.

### Pesi risk-parity (avanzato)

Ogni asset contribuisce **lo stesso rischio** al portafoglio: più
volatile è l'asset, meno peso gli dai. Concettualmente elegante,
operativamente più complesso. Lo accenniamo perché è dove si va
quando si esce da L1.

## 7. Ribilanciare

Col tempo, i pesi del portafoglio si spostano dai target perché il
mercato si muove. **Ribilanciare** = vendere ciò che è cresciuto troppo
e ricomprare ciò che si è ridotto, per tornare ai pesi target.

### Frequenza

- Mensilmente: aggressivo, può generare costi di transazione e tax
  events frequenti
- Trimestralmente: middle ground
- Annualmente: tradizionale per portafogli "lazy"
- "Threshold-based": ribilanci solo quando un asset si discosta di
  più di X% dal target. Più razionale, ma richiede di monitorare

### Effetto contrarian

Ribilanciare = vendere quello che è salito tanto, comprare quello che è
sceso. Questo è **strutturalmente contrarian** e nei mercati che fanno
mean-reversion porta un piccolo vantaggio. In mercati molto trend
(crypto bull market) può "tagliarti le ali": vendi BTC che continua a
salire per comprare LINK che continua a scendere. Trade-off vero, non
neutralizzabile.

## 8. Errori classici di chi inizia

- **"Diversifico" comprando 10 altcoin diverse**. No: stai aumentando
  l'esposizione alla stessa cosa (mercato crypto), non diversificando
- **Mettere tutto sul "next BTC"**. La probabilità che un singolo
  outlier replichi i +1000% di BTC del passato è altissima per
  qualcuno (statisticamente, alcuni progetti lo faranno) e bassissima
  per **te** (è una scommessa con expected value modesto e varianza
  catastrofica)
- **Pesi che riflettono solo il "ti piace il progetto"**. La simpatia
  per una technology non è una variabile predittiva del prezzo
- **Ribilanciare costantemente** "perché ho letto un articolo": costi
  di transazione mangiano il beneficio del rebalance
- **Non considerare il cash come asset**. Il cash è l'unica posizione
  che ti dà **opzione**: poter comprare cose buone quando il mercato
  crolla. Andare al 100% investiti in ogni momento ti toglie quella
  opzione

## 9. Collegamento al nostro progetto

Il sistema che stiamo costruendo non è un consulente di portafoglio: è
un **generatore di segnali probabilistici** (VISION.md). Ma:

- Il **Tier 1** (ADR-005) è già un mini-portafoglio: 5 crypto scelte
  per ragioni indipendenti dal market cap (POL è ad esempio fuori dal
  top-20 come abbiamo visto dai dati CoinGecko di sessione 2)
- Le **correlazioni cross-asset** che abbiamo misurato nei notebook
  ($\rho_{BTC,ETH}=0.81$, ecc.) sono l'input naturale per decidere
  pesi futuri se il sistema producesse raccomandazioni
- Il **paper trading** (Fase 6) avrà un modulo `Portfolio` con position
  sizing configurabile. Il default sarà "pesi uguali" sui segnali
  positivi, perché è il più robusto e meno opinionato. Da lì si potrà
  evolvere verso risk-parity o convinzione

## Glossario rapido

- **Portafoglio**: insieme di asset posseduti con i rispettivi pesi
- **Rischio sistematico**: rischio comune a tutti gli asset di una
  classe; non eliminabile con diversificazione
- **Rischio specifico (idiosincratico)**: rischio del singolo asset;
  eliminabile con diversificazione sufficiente
- **Correlazione**: misura statistica di quanto due asset si muovono
  insieme. +1 = identici, 0 = indipendenti, −1 = opposti
- **Diversification benefit**: la riduzione di volatilità del
  portafoglio rispetto alla media degli asset che lo compongono
- **Asset class**: famiglia di asset con caratteristiche simili (azioni,
  obbligazioni, crypto, materie prime, cash)
- **Position sizing**: scelta di quanto allocare a ciascuna posizione
- **Equal weight**: pesi uguali a tutti gli asset selezionati
- **Market-cap weight**: pesi proporzionali al market cap (default
  degli ETF indicizzati)
- **Risk parity**: pesi calcolati affinché ogni asset contribuisca lo
  stesso rischio al portafoglio
- **Ribilanciare**: riportare i pesi del portafoglio ai target dopo
  che il mercato li ha spostati
- **Cash drag**: la "tassa" implicita di tenere cash (non rende quasi
  nulla in nominale, **se non c'è inflazione**)

## Cosa portare via

- **La diversificazione attacca il rischio specifico, non quello
  sistematico**. Comprare 20 crypto invece di 1 non ti salva dal
  prossimo bear market di mercato
- **Più gli asset sono decorrelati, più la diversificazione funziona**.
  BTC + ETH sono troppo correlati (0.81) per dare un beneficio grosso;
  BTC + GOLD (0.08) sì
- **Diversificare TRA classi è più potente che diversificare DENTRO
  una classe**. Crypto + equity + oro > 20 crypto diverse
- Dal **decimo asset diversificato** in poi, il beneficio aggiuntivo
  per riduzione del rischio è marginale. Trenta asset = tanto vale un
  ETF
- **Equal weight** è un default robusto se non hai opinioni forti. **Market
  cap** è il default "passivo" del settore. **Convinzione** richiede
  che tu sappia davvero cosa stai facendo
- Ribilanciare è strutturalmente **contrarian** — utile in mean-reversion,
  costoso in trend forte. Non c'è risposta giusta universale
- Il **cash** è un asset. È l'unico che ti dà **opzione** quando il
  mercato crolla

---

*Prossimo capitolo*: L1.06 — DCA (Dollar Cost Averaging), pro e contro.
