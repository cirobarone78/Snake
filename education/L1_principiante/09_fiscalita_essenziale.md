# L1.09 — Fiscalità essenziale (concettuale, non consulenza)

> **Disclaimer non-negoziabile**: questo capitolo descrive **concetti
> generali** di fiscalità relativi a crypto e mercati finanziari per
> un investitore residente in Italia, con riferimenti normativi alla
> data di scrittura (2026). **Non è consulenza fiscale.** Le situazioni
> personali variano. Per casi specifici, parla con un commercialista
> esperto in crypto — è una specializzazione che pochi hanno davvero,
> ma alcuni sì.

> Disclaimer ancora più importante: l'**evasione fiscale è reato**.
> Niente in questo capitolo è scritto per aiutare a "non dichiarare".
> Tutto è scritto per aiutare a **dichiarare correttamente** ciò che
> per legge va dichiarato, e per **evitare errori** che costano cari.

## 1. Perché la fiscalità crypto è complicata

Tre ragioni:

1. **Normativa giovane**: la legge italiana ha riconosciuto le crypto
   come "attività finanziarie" solo dal 2023 (Legge di Bilancio 2023,
   art. 1 commi 126-147). Prima era zona grigia. La normativa è
   *recente* e si sta ancora assestando
2. **Eventi tassabili numerosi**: ogni swap crypto-crypto è un evento
   potenzialmente tassabile. Se in un anno fai 50 swap, hai 50
   plusvalenze/minusvalenze da calcolare
3. **Tracking impossibile a mano** se sei attivo. Tool dedicati
   (Koinly, CoinTracker, Cryptotaxcalculator) sono praticamente
   indispensabili sopra una manciata di transazioni l'anno

## 2. Il framework italiano in 4 punti

### A. Tipo di reddito

Plusvalenze e altri redditi da crypto rientrano nella categoria
**"redditi diversi"** (art. 67 TUIR, c. 1 lett. c-sexies). Sono tassati
con **imposta sostitutiva del 26%** sulla plusvalenza realizzata
(stessa aliquota dei dividendi e degli altri capital gain).

### B. Cosa è "realizzato"

Tassabile è la **plusvalenza realizzata**, cioè quando:
- Vendi crypto in cambio di EUR/USD (o altra valuta fiat)
- Scambi una crypto con un'altra crypto (sì, anche BTC → ETH è un
  evento tassabile)
- Usi crypto per pagare beni/servizi
- Conversione di stablecoin in fiat o altra crypto (con eccezioni
  sull'art. 67 modificato)

**Non** è tassabile:
- Comprare crypto con EUR (è acquisto, non vendita)
- Spostare crypto tra due tuoi wallet (non c'è cambio di proprietà
  economica)
- HOLD: hai BTC che è salito del 100%? Finché non lo vendi/scambi,
  niente da dichiarare (sulla plusvalenza; sui saldi vedi punto C)

### C. Obblighi di monitoraggio (quadro RW)

Indipendentemente dalla plusvalenza, se possiedi crypto **detenute al
di fuori del circuito intermediari finanziari italiani** (es. wallet
self-custody, exchange esteri come Binance, Kraken, Coinbase), devi
compilare il **quadro RW** della tua dichiarazione dei redditi per il
**monitoraggio**.

**Soglia esonero**: storicamente c'era una soglia di esonero da RW per
importi piccoli (€15.000 o periodo di detenzione < 7 giorni). Le crypto
**hanno regole diverse**: la dottrina prevalente al 2026 è che vadano
sempre dichiarate, a prescindere dall'importo. Verifica sempre la
versione corrente con un esperto.

Sanzioni per omessa RW: 3-15% del valore non dichiarato (può salire al
6-30% per asset in paesi black-list).

### D. IVAFE

L'**IVAFE** è una tassa patrimoniale dello 0.2% annuo sul **valore al
31/12** delle crypto detenute (dal 2023). Tasso ridotto in certi casi.
È una tassa **sul possesso**, non sulla movimentazione.

## 3. Tracciamento: cosa devi conservare

Per ogni transazione, dovresti idealmente avere:

- **Data e ora** dell'operazione
- **Asset coinvolti** (es. BTC → ETH)
- **Quantità** di entrambi
- **Valore in EUR al momento dell'operazione** (per BTC è il prezzo
  EUR/BTC a quella data/ora)
- **Fee pagata** (riduce la plusvalenza)
- **Exchange/wallet** dove è avvenuta

Per acquisti via DCA mensile su exchange italiano regolamentato è
banale: l'exchange te lo dà in report annuale. Per attività su DeFi,
swap multipli, NFT, ecc., devi affidarti a tool dedicati o documentare
manualmente (sconsigliato sopra le ~20 operazioni l'anno).

### Metodo di calcolo della plusvalenza

Per ogni vendita, serve sapere a **quale prezzo** avevi comprato la
parte che vendi. Convenzioni possibili:

- **FIFO** (first in, first out): vendi prima i coin comprati per
  primi. È il default per legge in Italia
- **LIFO** (last in, first out): vendi prima i coin comprati per
  ultimi
- **Costo medio**: media ponderata di tutti gli acquisti

In Italia per crypto **vale il LIFO** secondo l'attuale prassi
interpretativa (verifica aggiornata, perché alcune fonti dicono
ancora "costo medio" o FIFO). Un tool fiscale serio gestisce tutto
automaticamente, ma è importante capire **che** convenzione viene
applicata e perché.

## 4. Eventi crypto specifici

### Staking e rewards

I **rewards di staking** sono **redditi**: rientrano tipicamente tra
i redditi di capitale (art. 44 TUIR), tassati al 26% al momento della
ricezione, valore in EUR a quella data. Poi quando li vendi, scatta
una **nuova plusvalenza** sulla differenza tra prezzo di vendita e
prezzo al momento della ricezione (che è il tuo nuovo costo base).

### Airdrop

Stessa logica: il valore al momento della ricezione è reddito (alcune
interpretazioni li trattano diversamente — area grigia, chiedi).

### Mining

Se mini in modo professionale (con strutture e continuità),
potrebbe configurarsi come attività di impresa, con tutto il regime
fiscale conseguente. Per il "mining occasionale" la tassazione è
analoga ai rewards.

### Hard fork

Quando una blockchain si scinde (es. BCH dalla Bitcoin chain) e
ricevi "gratuitamente" i nuovi coin, il valore al momento del fork è
reddito.

### DeFi: yield farming, LP

Zona molto grigia. Receive di token come ricompensa è reddito al
momento. Le "impermanent loss" delle posizioni LP sono difficili da
gestire: ufficialmente non è ancora chiaro come trattarle in
dichiarazione. Tool fiscali aggiornati provano a darne una stima
plausibile, ma la giurisprudenza non si è ancora consolidata.

## 5. Compensazione plus/minus

Le minusvalenze crypto sono compensabili con plusvalenze crypto, sia
nello stesso anno sia per i 4 anni successivi (regime "ordinario" dei
redditi diversi). **Non** sono compensabili con plusvalenze di altri
asset class (es. azioni).

Esempio: anno 2026 hai +5.000 EUR di plusvalenze su BTC e -2.000 EUR
di minusvalenze su SOL. Tassi 26% su (5.000 − 2.000) = 780 EUR di
imposta.

Esempio 2: anno 2026 hai -3.000 EUR di minusvalenze nette. Niente
tasse 2026, ma puoi portarti la minus per i 4 anni successivi e
compensare future plusvalenze fino al 2030.

## 6. Tool pratici

Per chi fa più di poche transazioni l'anno:

- **Koinly**: il più diffuso a livello internazionale. Import da
  exchange e da wallet via API o CSV. Genera report fiscale per Italia
  (RW + dichiarazione plus/minus). Free fino a poche transazioni,
  pagamento ~50-200 EUR per il report completo
- **CryptoTaxCalculator (CTC)**: alternativa, simile a Koinly
- **CoinTracker, Accointing, Tokentax**: altri player

Per chi fa solo qualche acquisto DCA mensile su Coinbase o Bitstamp
italiano: spesso il report che l'exchange ti manda a inizio anno è
sufficiente.

**Importante**: il report fiscale di Koinly/CTC è un input al
commercialista, non una sostituzione. Il commercialista capisce il
quadro RW, le sanzioni, le interpretazioni dell'Agenzia delle Entrate
locali. Tool + commercialista = combo praticabile.

## 7. Errori frequenti da evitare

- **Non dichiarare "tanto è poco"**: c'è una soglia di tolleranza in
  alcuni paesi, NON in Italia. Sanzioni da 3% in su anche per
  importi modesti
- **Non dichiarare il wallet self-custody perché "tanto chi mi
  controlla"**: l'AdE ha contestato casi anche senza segnalazioni
  bancarie, con analisi della blockchain pubblica. Sopra certe soglie
  la probabilità di controllo aumenta
- **Considerare BTC → ETH come "non vendita"**: sbagliato, è swap
  tassabile. Errore comune in chi pensa per "valore EUR netto"
- **Perdere lo storico di acquisto**: se hai comprato BTC nel 2017 a
  €1.000 e non hai più traccia, l'AdE assumerà costo zero in caso di
  contestazione, tassandoti il **lordo** della vendita
- **Pensare che "all'estero non si sa"**: la **DAC8** (direttiva UE
  approvata 2023, applicazione progressiva 2026-2027) impone agli
  exchange europei (inclusi quelli che servono utenti europei) lo
  scambio automatico di informazioni con le AdE nazionali. La era
  della "crypto invisibile" è finita

## 8. Quando andare dal commercialista

**Sicuramente**:
- Hai fatto più di 10 swap crypto-crypto in un anno
- Hai usato DeFi (yield farming, LP, lending)
- Hai ricevuto airdrops o staking rewards
- Hai > €15-30k investiti in crypto
- Hai wallet su exchange esteri

**Forse no**:
- Solo DCA su Bitstamp/Coinbase italiano, < €5k investiti, mai vendute

In ogni caso, **un'ora di consulenza l'anno** costa 100-200 EUR e ti
salva da sanzioni che possono arrivare a migliaia. Investimento
ridicolmente positivo in expected value.

## 9. Collegamento al nostro progetto

Il sistema **non gestisce e non considera la tassazione**. È una
ricerca quantitativa sui mercati. Però se un domani il sistema
dovesse generare segnali operativi (in scenari ADR-004), va ricordato:

- **Le metriche "lorde" del sistema NON sono il rendimento netto
  dell'utente**. 26% del gain va in tasse. Una strategia che fa
  +20% lordo è +14.8% netto
- **Il numero di trade impatta i costi fiscali in modo non banale**:
  ogni swap è evento tassabile e richiede tracciamento. Strategia
  "high turnover" → 100 swap → 100 eventi
- Il **paper trading di Fase 6** mostrerà rendimenti **al lordo**
  delle tasse (è la convenzione standard, e dipende dalla
  giurisdizione dell'utente). Quando passeremo a output "consumibili"
  in Fase 7, può avere senso mostrare una stima "post-tax" per
  ancorare meglio le aspettative

## Glossario rapido

- **Plusvalenza realizzata**: differenza positiva tra prezzo di
  vendita e prezzo di acquisto, al momento della vendita. Tassabile
- **Minusvalenza**: differenza negativa. Compensabile con plusvalenze
- **Imposta sostitutiva 26%**: aliquota standard sui capital gain in
  Italia
- **Quadro RW**: sezione della dichiarazione dei redditi per
  monitoraggio di asset esteri / crypto in self-custody
- **IVAFE**: tassa patrimoniale 0.2% annuo sul valore al 31/12 delle
  crypto
- **FIFO / LIFO / costo medio**: metodi di calcolo del costo base
  quando vendi una parte di una posizione accumulata in tempi
  diversi
- **DAC8**: direttiva UE 2023 che obbliga gli exchange europei allo
  scambio automatico di informazioni con le AdE
- **Soglia tolleranza**: importo sotto cui la dichiarazione non è
  obbligatoria. Per le crypto in Italia attualmente **non c'è soglia
  di esonero generale** secondo la prassi più condivisa
- **Staking reward**: ricompensa per il blocco di crypto a sostegno
  della rete. Reddito al momento della ricezione
- **Airdrop**: distribuzione "gratuita" di token. Reddito al
  momento della ricezione

## Cosa portare via

- **L'evasione fiscale è reato.** Tutto questo capitolo serve a
  **dichiarare correttamente**, non a evitare di dichiarare
- **Ogni swap crypto-crypto è un evento tassabile.** Non solo le
  vendite in EUR. Errore frequente
- **In Italia: 26% sulle plusvalenze, quadro RW per monitoraggio,
  IVAFE 0.2% sul saldo**. Le aliquote sono come quelle dei dividendi
  azionari standard
- **Tracciamento manuale è impossibile sopra una decina di
  transazioni**. Tool dedicati (Koinly, CTC) sono praticamente
  necessari
- **DAC8 e blockchain analytics** rendono l'idea "tanto non si sa"
  sempre più sbagliata. Era finita
- Per casi specifici, **un commercialista esperto di crypto** vale 10
  volte il suo costo
- Il sistema che stiamo costruendo produce **rendimenti lordi**, non
  netti. Quando si valuta una strategia, considerare l'impatto delle
  tasse è parte del lavoro

---

*Prossimo capitolo*: L1.10 — Cosa NON è il trading: le promesse a cui
non credere.
