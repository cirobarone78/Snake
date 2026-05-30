# L1.08 — Custodia: cold/hot wallet vs custodia su exchange

> Possedere crypto non significa "averli su Binance". Significa essere
> in grado di **firmare transazioni** con le chiavi private associate
> a un indirizzo blockchain. Chi possiede le chiavi possiede i fondi.
> Tutto il resto è IOU: un pezzo di carta che dice "abbiamo i tuoi
> coin", finché qualcuno glielo permette.

Capitolo sulla **custodia**: chi tiene le chiavi, quali sono i
trade-off, quando ognuna delle opzioni è ragionevole. Concetti, non
tutorial.

## 1. Cosa "possedere crypto" significa tecnicamente

In una blockchain (Bitcoin, Ethereum, ecc.) **non esiste un conto** in
senso bancario. Esistono **indirizzi**, a cui sono associati saldi.
Per spostare un saldo da un indirizzo a un altro, serve **firmare**
la transazione con la **chiave privata** dell'indirizzo di partenza.

Quindi:
- Chi conosce la chiave privata → controlla il saldo
- Chi non la conosce → non lo controlla, qualunque cosa pensi

La **seed phrase** (di solito 12 o 24 parole in inglese) è la
rappresentazione *human-readable* della chiave privata. Da quelle
parole si derivano tutte le chiavi private di tutti gli indirizzi
del wallet. Perderle = perdere i fondi. Farsele rubare = i fondi
verranno rubati.

## 2. Tre opzioni di custodia

### A. Custodia su exchange (CEX custody)

Compri BTC su Binance/Coinbase/Kraken. I tuoi coin sono "tuoi"
nell'interfaccia, ma le chiavi private sono dell'exchange. Tu hai un
**IOU**: l'exchange dice "se vuoi prelevarli, li mandi a un tuo
indirizzo".

**Pro**:
- Zero gestione, zero rischio di "perdere la seed phrase"
- Recovery in caso di smarrimento password (via KYC + supporto)
- Comodo per trading attivo (zero costi di network per spostarli
  dentro l'exchange)
- Login email/password familiare, 2FA opzionale

**Contro**:
- **Not your keys, not your coins** — se l'exchange fallisce/viene
  hackerato/sequestrato, perdi tutto. È successo davvero più volte:
  - **Mt. Gox** (2014): 850.000 BTC scomparsi, oggi varrebbero
    decine di miliardi. Recupero parziale dopo 10 anni
  - **FTX** (novembre 2022): $8 miliardi di asset clienti usati
    impropriamente. Bancarotta. Recupero parziale in corso
  - **Celsius** (giugno 2022): piattaforma di "earn" che ha
    congelato i prelievi. Migliaia di utenti hanno perso accesso
- Rischio normativo: il governo del paese dove ha sede l'exchange
  può imporre congelamenti, KYC più stringenti, blocchi su certi
  asset
- Account hack diretto (phishing, SIM swap → sostituiscono il tuo
  2FA SMS, e quindi reset password)

**Quando ha senso**: trading attivo con somme che ti puoi permettere
di perdere, oppure parcheggio temporaneo prima di muoverti su
self-custody.

### B. Hot wallet (self-custody software)

Wallet **sul tuo telefono o PC**, dove le chiavi private sono salvate
in locale (di solito cifrate). Esempi: MetaMask (browser),
Phantom (Solana), Trust Wallet, Exodus, l'app ufficiale di
Coinbase Wallet (diverso da Coinbase Exchange).

**Pro**:
- **Tu** controlli le chiavi: l'exchange non può congelarti, il
  governo non può ordinarne il prelievo
- Setup veloce (download app, scrivi seed phrase su un foglio,
  finito)
- Necessario per usare DeFi (interagire con smart contract)
- Costo zero (le commissioni di network le paghi solo quando
  fai una transazione)

**Contro**:
- **Connesso a internet → superficie di attacco**. Un wallet sul
  telefono compromesso da malware perde tutto in un secondo
- **Phishing**: sito che imita MetaMask, ti chiede di "ri-connettere"
  il wallet, in realtà ti fa firmare una transazione che svuota
  tutto. È **la** truffa più frequente in crypto
- Errore umano: mandi all'indirizzo sbagliato, irreversibile
- Seed phrase smarrita = fondi persi. Nessun "supporto clienti" che
  ti aiuta

**Quando ha senso**: importi medi (qualche migliaio di EUR), uso
attivo (DeFi, NFT, swap on-chain).

### C. Cold wallet (hardware wallet)

Dispositivo fisico dedicato (Ledger Nano, Trezor, Coldcard) che
**custodisce le chiavi offline**. Quando vuoi fare una transazione, la
costruisci sul PC, ma la **firma** avviene dentro il dispositivo:
le chiavi non lasciano mai il chip.

**Pro**:
- Le chiavi non sono mai online, **isolate da malware del PC**
- Sopravvive al PC compromesso, al browser compromesso, al malware
  generico (non è bulletproof, ma alza enormemente la barriera)
- Costo modico (~70-150 EUR per device serio)
- Setup: scrivi seed phrase su carta (mai digitalmente!), tieni in
  posto sicuro

**Contro**:
- Costo iniziale + curva di apprendimento
- Comodità ridotta: ogni operazione richiede device fisico + PIN
  + conferma sullo schermo del device
- Non protegge da phishing in modo magico — devi sempre verificare
  l'indirizzo destinatario sul **schermo del dispositivo**, non
  fidarti del PC (a volte i malware swappano l'indirizzo nel
  clipboard)
- Eventi rari ma documentati: vulnerabilità di firmware,
  data breach del produttore (Ledger 2020 ha avuto un leak di email
  customer che ha portato a phishing mirato)

**Quando ha senso**: holding a lungo termine di importi rilevanti
(qualche % del tuo patrimonio personale e oltre).

## 3. Il backup della seed phrase

La seed phrase è il **single point of failure** assoluto del
self-custody. Domande pratiche:

- **Su carta o digitale?** Carta. **Mai** in nessun servizio cloud
  (Google Drive, iCloud, Dropbox, foto del telefono). Mai. Nemmeno
  cifrato — i dati cifrati nei cloud sono comunque target ad alta
  probabilità in caso di breach del provider
- **Una copia o più?** Almeno 2, in posti fisicamente diversi. Una
  copia in casa, una a casa di un genitore/banca. Anche se uno
  brucia/allaga/viene rubato, l'altro funziona
- **Acciaio o carta?** Per importi seri, "steel plates" (Cryptosteel,
  Billfodl) che resistono a fuoco e acqua. Costo aggiuntivo modesto
  rispetto al rischio coperto
- **Passphrase aggiuntiva?** Hardware wallet di alto livello supportano
  una "25a parola" che tu inventi. Senza, anche chi trova la seed
  phrase non accede. Migliora la sicurezza, peggiora se la dimentichi
  tu stesso

## 4. Multisig: cosa è e perché esiste

Per importi grandi esistono setup **multisig** (multi-signature): per
fare una transazione servono N firme su M chiavi (es. 2-of-3).

Esempi pratici:
- 2-of-3: tu hai 2 chiavi (una su Ledger, una su backup acciaio), il
  tuo legale ha la terza. Se perdi una chiave, le altre due bastano.
  Se qualcuno ne ruba una, non basta
- Casa, Unchained, Sparrow sono servizi/strumenti che gestiscono setup
  multisig per privati

Complessità maggiore, sicurezza maggiore. Tipicamente usato per importi
"family office" (centinaia di migliaia di EUR e oltre). Lo nomino per
sapere che esiste.

## 5. Tre profili pratici

### Principiante con 500 EUR in BTC

- Tieni su exchange regolamentato (Coinbase, Bitstamp, Kraken in Europa)
- Attiva 2FA con app (Authy/Google Auth), non SMS
- Non pensare al self-custody finché l'importo non cresce

Rischio sopportato: bancarotta exchange. Probabilità bassa per chi è
regolamentato sul serio (vedi MiCA in UE dal 2024), ma non zero.

### Investitore con 5.000-30.000 EUR

- Operazioni di scambio: hot wallet self-custody (MetaMask + hardware
  wallet collegato per ogni firma → "MetaMask in cold mode")
- Holding a lungo termine: hardware wallet dedicato, seed phrase su
  steel plate in posto sicuro
- Solo piccola % su exchange per trading attivo

Rischio sopportato: phishing, errore umano, malware su PC. Mitigabile
con disciplina.

### Holder con > 50.000 EUR

- Multisig 2-of-3 o setup analogo
- Hardware wallet diversi (es. uno Ledger + uno Trezor, per non
  dipendere da un solo vendor)
- Backup steel + passphrase + processo documentato per il "what if I
  die" (la storia degli holder morti con i coin inaccessibili è
  letteralmente milioni di BTC persi per sempre)

Rischio sopportato: complessità operativa, errore umano. Mitigabile
con processo scritto e test periodici di recovery.

## 6. Collegamento al nostro progetto

Il sistema che stiamo costruendo è di **ricerca quantitativa**, non
opera trade reali (ADR-004) e non gestisce custodia. Però:

- Il **paper trading** (Fase 6) simula transazioni come se fossero
  reali, **incluso il modello di fee** (ADR-012/013). Le fee variano
  per exchange — se la stessa strategia un domani girasse "live" il
  modello di fee va aggiornato all'exchange reale dove l'utente
  vuole eseguire
- L'utente del sistema potrebbe (in futuro condizionale, vedi
  ADR-004) decidere di esecutare manualmente i segnali. In quel
  caso le scelte di custodia sono **sue** e **separate dal sistema**.
  Il sistema produce segnali; come e dove vengono eseguiti è
  responsabilità operativa dell'utente

**Mai** il sistema deve toccare seed phrase, chiavi private, o API
key di exchange con permessi di trading. È una regola operativa
ovvia ma vale la pena scriverla esplicitamente: se in futuro
servisse fetchare dati da un exchange privato (es. saldi reali), si
useranno API key **read-only**.

## Glossario rapido

- **Chiave privata**: il numero matematico che permette di firmare
  transazioni da un indirizzo. Chi lo conosce controlla i fondi
- **Indirizzo**: il "destinatario" pubblico di una transazione,
  derivato dalla chiave privata
- **Seed phrase**: 12 o 24 parole inglesi che codificano la chiave
  privata in modo human-readable
- **Custodial wallet**: la chiave privata è custodita da un terzo
  (exchange, broker)
- **Self-custody / non-custodial wallet**: la chiave privata è
  custodita da te
- **Hot wallet**: wallet su dispositivo connesso a internet
  (telefono, PC)
- **Cold wallet / hardware wallet**: dispositivo dedicato che tiene
  le chiavi offline e firma le transazioni isolatamente
- **Multisig (multi-signature)**: schema in cui servono N firme su M
  chiavi per autorizzare una transazione
- **2FA (two-factor authentication)**: secondo fattore di
  autenticazione oltre alla password (app, hardware key, SMS).
  SMS è il peggiore (SIM swap)
- **Phishing**: sito o messaggio che imita un servizio legittimo per
  rubare credenziali o far firmare transazioni dannose
- **SIM swap**: attacco in cui il truffatore convince l'operatore
  telefonico a trasferire il tuo numero sul suo SIM, intercettando
  SMS di 2FA

## Cosa portare via

- **Chi ha le chiavi possiede i fondi.** Su exchange le chiavi sono
  loro, non tue. È un IOU. Comodo, finché funziona
- I crash storici di exchange (Mt. Gox, FTX, Celsius) **non sono
  eventi rari da museo** — accadono ancora. Non perché tutti gli
  exchange siano cattivi, ma perché è una struttura di custodia
  con incentivi complessi
- **Self-custody trasferisce il rischio da "fallimento dell'exchange"
  a "errore tuo + phishing"**. Non lo elimina, lo sposta
- Per somme piccole, exchange regolamentato + 2FA app è
  ragionevole. Per somme medie, hot wallet + hardware. Per somme
  grandi, multisig + processo scritto
- **La seed phrase non va MAI in cloud, mai in foto, mai in mail.**
  Carta o acciaio. Backup multipli. Test di recovery una volta
  all'anno per verificare che funzionino davvero
- Il **2FA via SMS è meglio di niente, ma vulnerabile a SIM swap**.
  Preferisci app autenticator o hardware key (YubiKey)
- Non c'è "la" risposta giusta universale: dipende da quanto hai,
  dal tuo livello tecnico, e dal rischio che senti di poter
  gestire

---

*Prossimo capitolo*: L1.09 — Fiscalità essenziale (concettuale, non
consulenza).
