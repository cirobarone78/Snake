# L1.10 — Cosa NON è il trading: le promesse a cui non credere

> Capitolo finale di L1. Tutti i nove capitoli precedenti hanno cercato
> di dirti **cosa è** e **come funziona**. Questo capitolo fa l'opposto:
> elenca le promesse che senti continuamente da YouTube, Instagram,
> TikTok, "corsi di trading", e ti spiega perché **non funzionano** —
> non per opinione, ma per matematica statistica e onestà intellettuale.
>
> È il capitolo più importante di L1. Se ti porti via solo una cosa di
> tutto il livello, fai in modo che sia questa.

## 1. La premessa: cosa è il trading davvero

Il **trading attivo** (decidere quando entrare e uscire da posizioni
per battere il mercato) è:

- **Un gioco a somma negativa al netto dei costi**. Per ogni euro che
  un trader guadagna, c'è qualcun altro che lo perde — meno fee/spread
  per la "casa" (exchange, broker, market maker). I "vincitori netti"
  esistono ma sono pochi
- **Statisticamente dominato dai professionisti**. Hedge fund, market
  maker, banche d'affari hanno tecnologia, dati e capitale che il
  retail non può eguagliare. Il retail è la "preda strutturale" del
  mercato
- **Estremamente difficile psicologicamente**. Anche chi ha l'edge
  tecnico spesso si distrugge per emozioni, FOMO, panic-sell, revenge
  trading

Tutto questo non significa "non investire". Investire (buy-and-hold,
DCA, portafoglio diversificato) è una cosa diversa dal trading attivo.
Il primo storicamente premia in media; il secondo statisticamente
penalizza in media.

## 2. I numeri che (quasi) nessuno cita

Studi accademici e dati regolamentari pubblici:

- **Brokers Forex europei** sono obbligati per legge (regolamento
  ESMA) a pubblicare la percentuale di **conti retail in perdita**
  sulla home page. La maggior parte mostra **70-85% di conti in
  perdita**. Significa che 3 retail su 4 perdono soldi
- **Studio Barber & Odean** (UC Berkeley) sul retail equity: i
  trader più attivi sotto-performano il mercato del 6-7% l'anno
- **Studio brasiliano FGV** su 1.500 trader retail brasiliani su 1
  anno di Mini-Index futures: **97% perdeva**. Tra quelli che ci
  guadagnavano, il rendimento medio era inferiore al salario minimo
- **Studio universitario sui copy-trader** di eToro: i seguaci di
  trader pubblici performavano peggio del mercato

Conclusione: **fare trading attivo retail è statisticamente perdente
nella stragrande maggioranza dei casi**. È un fatto, non un'opinione.

## 3. Le promesse rosse e perché non funzionano

### "Diventa ricco col trading in 3 mesi / 1 anno / 5 anni"

**Matematica**: per partire da 1.000 EUR e arrivare a 1 milione EUR in
5 anni servono **~120%/anno** di rendimento composto. È meglio del 99%
dei migliori hedge fund storici, sostenuto per 5 anni di fila. Per
fare 10.000 → 1 milione in 3 anni servono **+364%/anno**.

Questi numeri non esistono se non per fortuna estrema (o frode). Chi
te li promette o non capisce la matematica o ti sta vendendo una
storia.

### "Imparerai il segreto che le banche ci nascondono"

**Fatto**: non esiste un "segreto" che genera 50% l'anno e che è
nascosto. Se esistesse, lo userebbero le banche stesse — non c'è
ragione per cui dovrebbero condividerlo per €99 di un corso. Le
banche **usano effettivamente** strategie quantitative sofisticate,
ma il vantaggio è solo parzialmente nella strategia: gran parte sta
in capitale, tecnologia, accesso a dati e ordini in millisecondi.

### "Sistema con 90% di operazioni vincenti"

**Trucco statistico**: un sistema può facilmente avere alta winrate
e essere **complessivamente perdente**. Esempio: 9 trade vinti da 100
EUR + 1 trade perso da -1.500 EUR = 100 EUR di perdita complessiva
con 90% winrate.

I sistemi venduti come "altissima winrate" usano stop-loss molto larghi
o "media del prezzo" su posizioni perdenti (martingala) per evitare
chiusure in perdita. Quando arriva il colpo grosso, **wipe-out totale**
del conto. È matematicamente quasi inevitabile su orizzonti lunghi.

### "Strategia che batte il mercato dimostrata in backtest"

**Problemi del backtest** che la maggior parte degli "expert" non
applica:

1. **Look-ahead bias**: usare dati che non erano disponibili in tempo
   reale (es. ricalcolare un indicatore con la chiusura del giorno
   stesso, quando in tempo reale la conoscevi solo a fine giornata)
2. **Survivorship bias**: testare solo sugli asset che esistono oggi,
   ignorando quelli falliti. Per crypto, ignorare le altcoin morte =
   sovrastimare drasticamente i rendimenti
3. **Overfitting**: ottimizzare i parametri su dati storici fino a
   trovare la combinazione che funziona meglio **in passato**. In
   tempo reale non funziona perché era solo rumore
4. **Niente costi di transazione**: una strategia in pareggio lordo
   con 100 trade/anno è -10% netto dopo fee+slippage+tasse (vedi
   L1.04, L1.09)
5. **Periodo di test cherry-picked**: testare solo periodi favorevoli
   alla strategia

Il nostro progetto è esplicitamente costruito per **evitare** tutti
e cinque (vedi `CLAUDE.md`, sezione "Atteggiamento metodologico").
La maggior parte dei "corsi" no.

### "Trading semplice come 1-2-3: compra quando RSI < 30"

L'**RSI** (Relative Strength Index) è un indicatore reale, utile come
componente di molte strategie. Ma la regola "compra quando RSI < 30,
vendi quando RSI > 70" applicata isolata genera segnali in continuazione
in mercati trend-strong (dove RSI può stare sotto 30 per settimane
mentre il prezzo continua a scendere) e in mercati range (dove
funziona meglio).

**Nessun indicatore singolo "funziona"**. Tutti sono **componenti**, e
il loro valore dipende dal contesto. Promettere il contrario è
disonesto.

## 4. Il rosso delle micro-influencer

I personaggi YouTube/Instagram/TikTok che mostrano portafogli enormi e
"guadagni di 10.000 EUR/giorno" hanno modelli di business molto diversi
da quello che dicono di avere:

- **Affiliate revenue da exchange**: prendono % su ogni referral.
  Più persone iscrivono, più guadagnano. Indipendentemente da come
  vanno i trade
- **Vendita corsi/segnali**: il vero business. Gli "screenshot" di
  guadagni servono come marketing
- **Pump and dump coordinati**: presentano altcoin "promettenti", lo
  fanno sapere a tutti gli iscritti, il prezzo sale per FOMO, loro
  vendono quello che avevano comprato il giorno prima
- **Telegram/Discord a pagamento**: gruppi privati con "segnali" che
  spesso sono peggio del random

Test pratico: chiedi a un guru di mostrare:
1. Il **track record completo** (tutti i trade, anche perdenti)
2. **Tasse pagate** (se davvero guadagna così tanto, paga molte tasse)
3. Una verifica **indipendente** del conto

Quasi nessuno lo mostrerà.

## 5. Bias di sopravvivenza: chi vedi vs chi non vedi

**Il problema**: vedi solo i "vincitori".

- Su YouTube, gli "esperti di trading" che pubblicano video sono quelli
  che (per fortuna o capacità) sono ancora attivi. Quelli falliti hanno
  cancellato i canali
- Sui gruppi Telegram, vedi screenshot di vincite. Le perdite non
  vengono pubblicate
- Tra i tuoi amici, ti parlano degli investimenti che hanno guadagnato.
  Non di quelli persi (vergogna sociale)

**Effetto**: ti formi un'immagine che il trading sia "molto più facile
e profittevole" di quanto sia statisticamente.

Per correggerla, leggi articoli sui retail che hanno perso. Esistono
forum dedicati (r/wallstreetbets ha molti post di "loss porn"). Non è
intrattenimento, è calibrazione.

## 6. Cosa funziona davvero (in media)

Per il **retail medio** che vuole crescere il proprio patrimonio:

1. **Ridurre i costi**: ETF a basso costo (TER 0.05-0.20%) battono il
   95% dei fondi attivi nel lungo periodo
2. **DCA disciplinato** su asset diversificati (vedi L1.05, L1.06)
3. **Tempo nel mercato > timing del mercato**: stare investiti vince
   nella maggior parte degli scenari storici
4. **Tolleranza a drawdown**: chi vende durante un crash converte
   perdite di carta in perdite reali (vedi L1.07)
5. **Non confondere "investire" con "fare trading"**: sono due
   attività diverse, con probabilità di successo molto diverse

Niente di "sexy". Niente di "rapido". Funziona.

## 7. Come distinguere ricerca seria da bullshit

Segnali rossi (corsa a vendere):

- Pretende **rendimenti garantiti** o "molto probabili" sopra il 20%/anno
- Mostra screenshot ma non track record completo
- Dice "fidati di me", "questa volta è diverso", "Bitcoin va a 1M$
  entro 2027"
- Vende "segnali" o "indicatori segreti" a pagamento
- Non spiega mai i rischi
- Cita "esperti" che nessuno conosce, o si autocita come "esperto"
- Forte focus su **stile di vita** (auto, viaggi, orologi) invece che
  su metriche di performance

Segnali verdi (ascolta con interesse):

- Cita **fonti accademiche** o studi peer-reviewed
- Mostra rendimenti **out-of-sample**, non solo backtest
- Parla di **rischio** quanto di rendimento
- Mostra **drawdown e periodi di sotto-performance**
- Distingue chiaramente tra "ipotesi", "evidenza preliminare",
  "risultato robusto"
- Non vende segnali; semmai vende ricerca, libri, o lavora per
  istituzioni
- Usa parole come "potrebbe", "in media", "out-of-sample" piuttosto
  che "garantito", "infallibile", "sicuro"

## 8. Il nostro progetto, in questo contesto

Tutto VISION.md è stato scritto per essere il **contrario** della
fuffa che gira:

- Non promette rendimenti
- Non vende segnali
- Non chiama "trading bot da arricchirsi" ma "sistema di ricerca
  multifattoriale"
- Documenta **anche cosa NON funziona** (CLAUDE.md, regola
  metodologica esplicita)
- Usa rigore di backtest: walk-forward, out-of-sample, anti-look-ahead
  (ROADMAP Fase 2)
- Tiene il paper trading come **gate non-bypassabile** prima di
  qualsiasi considerazione live (ADR-004)

Non perché siamo speciali — perché è l'unico modo onesto di fare ricerca
quantitativa in finanza. Tutto il resto è marketing.

Quando in futuro guarderai i risultati del sistema, valuta con la
**stessa scetticità** che hai applicato alla "fuffa" descritta in
questo capitolo. Se il sistema dice "rendimento atteso +15%/anno con
Sharpe 1.2 out-of-sample", chiedi: **out-of-sample su quale periodo?
Quanto è cambiato il regime? E gli scenari worst-case?**

Onestà metodologica vale per ogni produttore di ricerca, incluso noi.

## Glossario rapido

- **Trading attivo**: decidere quando entrare/uscire da posizioni per
  battere il mercato
- **Buy-and-hold**: comprare e tenere a lungo termine, senza tentare
  di "azzeccare il timing"
- **Gioco a somma negativa**: gioco in cui la somma totale dei
  guadagni è inferiore alla somma totale delle perdite, per via dei
  costi/commissioni
- **Edge**: vantaggio statistico effettivo (info, velocità, modello)
  che permette di battere il mercato in modo replicabile
- **Survivorship bias**: bias cognitivo per cui si valuta una
  popolazione guardando solo i sopravvissuti, ignorando i falliti
- **FOMO** (Fear of Missing Out): paura di perdersi qualcosa, che porta
  a comprare al picco
- **FUD** (Fear, Uncertainty, Doubt): tattica di seminare incertezza
  per far vendere
- **Pump and dump**: schema in cui un gruppo coordina l'acquisto di
  un asset (pump), pubblicizza, e vende ai retail che entrano in FOMO
  (dump)
- **Martingala**: strategia di raddoppiare la posizione dopo ogni
  perdita. Matematicamente garantisce wipe-out su orizzonti lunghi
- **Track record**: storia completa e verificabile di tutte le
  operazioni di un trader/gestore
- **Backtest**: simulazione di una strategia su dati storici
- **Out-of-sample**: test di una strategia su dati che NON sono stati
  usati per costruirla. L'unico test che conta davvero

## Cosa portare via

- **Tra il 70% e il 97% del retail attivo perde soldi**, secondo
  studi indipendenti e dati regolamentari. È una statistica, non
  un'opinione
- **Non esiste un "segreto" che genera 50% l'anno e che è nascosto.**
  Se esistesse, gli hedge fund lo userebbero (e in parte lo fanno,
  per pochi % l'anno netti)
- **Backtest senza walk-forward, out-of-sample e costi è marketing**,
  non ricerca
- **Una alta winrate non significa profitto.** Il sistema che vince
  90% delle volte può perdere tutto al primo trade sbagliato
- **Survivorship bias** ti fa vedere solo i vincitori. La realtà
  statistica è dominata dai perdenti
- **Investire ≠ trading.** ETF a basso costo + DCA + tempo nel
  mercato batte la maggior parte degli "esperti" su orizzonti
  decennali
- **Diffida** di chiunque prometta rendimenti garantiti, venda
  segnali a pagamento, mostri solo vincite, o focalizzi il marketing
  su stile di vita
- Il nostro progetto è progettato per essere il **contrario** della
  fuffa: niente promesse di rendimento, niente sale-pitch, tutto
  open-source e documentato. Applica anche al nostro lavoro lo stesso
  scetticismo che applichi alla fuffa altrui — è un servizio che fai
  al progetto

---

**Fine di L1 — Principiante.**

I 10 capitoli di L1 coprono i fondamenti necessari per orientarsi nei
mercati finanziari con onestà. Il livello successivo (**L2 —
Intermedio · Smart Investor**) entra in argomenti più operativi:
bias cognitivi e psicologia del trader, cicli e regimi di mercato,
risk management quantitativo, basi di analisi tecnica trattata
correttamente come strumento e non come oracolo.

Vedi `education/L2_intermedio/README.md` per l'indice.
