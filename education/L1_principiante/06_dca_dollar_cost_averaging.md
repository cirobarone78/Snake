# L1.06 — DCA (Dollar Cost Averaging), pro e contro

> Il DCA è la strategia più consigliata in assoluto ai principianti.
> "Non sai quando comprare? Compra un po' ogni mese." Funziona, ma non
> per i motivi che la maggior parte delle persone pensa, e **non è
> quasi mai matematicamente la scelta migliore**. È una di quelle cose
> dove va capita la verità completa, non lo slogan.

## 1. Che cos'è il DCA

**Dollar Cost Averaging** = comprare una **somma fissa** di un asset a
**intervalli regolari**, indipendentemente dal prezzo.

Esempio: 200 EUR di BTC ogni primo del mese, per 24 mesi. Totale
investito: 4.800 EUR. Quante unità di BTC avrai alla fine? Dipende dai
prezzi delle 24 date. Mesi in cui BTC era basso → 200 EUR comprano più
BTC; mesi alti → comprano meno BTC. Il **prezzo medio di acquisto**
sarà la media pesata di tutti questi entry point.

L'alternativa al DCA si chiama **lump sum**: investi tutti i 4.800 EUR
in un colpo solo, al mese 1.

## 2. La promessa del DCA (come viene venduta)

Le narrative classiche che senti:

1. "**Riduci il rischio**": investendo gradualmente, non rischi di
   piazzare tutto al massimo storico
2. "**Mediati**": compri di più quando il prezzo è basso, di meno
   quando è alto → "compri la dip automaticamente"
3. "**Elimini lo stress**": non devi azzeccare il timing
4. "**Strategia da disciplinati**": automatizzabile, non ti devi
   pensare ogni mese

Tutte queste sono **parzialmente vere**. Vediamo cosa nascondono.

## 3. La verità matematica: DCA vs lump sum

Lo studio più famoso su questo tema è di **Vanguard** (2012,
aggiornato dopo), uno dei più grandi asset manager al mondo, su un
campione storico ampio (mercato USA + altri):

**Risultato: lump sum batte DCA nel ~66% dei casi** su orizzonti di
investimento di 10 anni.

Perché? Spiegazione intuitiva: i mercati salgono **più spesso di
quanto scendono**. Se l'expected value del rendimento dell'asset è
positivo (azioni storiche ~6-10% reale annuo, BTC storicamente molto
di più), allora **più tempo sei investito, meglio è**. Il DCA ti
tiene parzialmente fuori dal mercato per N mesi, quindi sotto-rendita
in media.

### Il caso semplice

Hai 4.800 EUR pronti. Due opzioni:

- **Lump sum**: investi tutto al mese 1
- **DCA**: investi 200 EUR/mese per 24 mesi → in media tieni metà
  della somma in cash per metà del periodo

Se l'asset rende il 10% annuo positivo, il "metà somma in cash per
12 mesi" significa rinunciare a ~10% × 50% × 1 anno = ~5% di
rendimento atteso sul totale. Non è una piccolezza.

### Il DCA NON ti "media" automaticamente verso il basso

Questa è una confusione comune. Il DCA **distribuisce** gli acquisti
nel tempo, ma il prezzo medio che ottieni non è "più basso" del prezzo
medio del periodo: è esattamente la **media armonica** dei prezzi (di
solito leggermente più basso del medio aritmetico, ma di poco). Non
è una magia, è solo matematica.

## 4. Quando il DCA è genuinamente meglio del lump sum

Casi reali in cui il DCA vince:

1. **Mercato fortemente bearish nel periodo di accumulo**: se nei 24
   mesi successivi al lump sum il prezzo scende del 40%, il DCA che
   compra anche i prezzi più bassi finisce in vantaggio
2. **Volatilità altissima dell'asset**: per asset con volatilità
   estrema (crypto piccole, asset speculativi), il DCA riduce la
   probabilità di entrare proprio al picco prima di un crash del 70%
3. **Reddito da lavoro continuo**: questo è il caso più rilevante
   nella pratica. Se guadagni stipendio mensile, **non hai mai una
   "lump sum" disponibile**. Il DCA è semplicemente "investo quello
   che riesco a risparmiare ogni mese". In questo caso non stai
   scegliendo DCA contro lump sum — stai facendo DCA perché è
   l'unica opzione fisica

Il punto 3 è quello che spesso confonde la conversazione. Per un
salariato medio il DCA è la **realtà operativa**, non una strategia.
Lo studio Vanguard parla di chi *ha già* una somma e deve decidere
come investirla.

## 5. Quando il lump sum è meglio (la maggior parte dei casi)

- Hai un capitale **disponibile ora** (eredità, bonus, vendita di
  qualcosa)
- L'asset ha trend di lungo periodo positivo atteso (azioni indicizzate,
  Bitcoin storicamente)
- Hai un orizzonte di tempo lungo (anni, non mesi)
- Non hai motivo specifico di pensare che il prezzo crollerà nei
  prossimi 6-12 mesi (e se ce l'hai, semplicemente aspetta — non fare
  DCA, fai market timing dichiarato)

In questi casi la matematica dice: **lump sum**. È la scelta razionale
2/3 delle volte.

## 6. Perché il DCA è raccomandato comunque (e ha senso)

Qui entra la componente psicologica, che la matematica trascura ma
che nella vita reale è enorme.

### Rischio di "rimpiangere" il timing

Investi tutti i 4.800 EUR oggi. Una settimana dopo il prezzo scende
del 20%. Razionalmente sai che è normale, ma **psicologicamente** ti
senti pessimo: hai perso 960 EUR "per colpa tua". Magari panic-vendi
al peggio. Magari smetti di investire per anni.

Il DCA neutralizza questo rischio: se il prezzo scende dopo il primo
acquisto, la seconda rata compra a prezzo più basso. Non sei
"completamente fregato".

### La differenza tra rendimento ottimale e rendimento realizzato

Lump sum ha **rendimento atteso più alto** in media. Ma se ti porta a
prendere decisioni emotive (vendere durante un crash, smettere di
investire), il **rendimento che realmente ottieni** può essere molto
inferiore.

Il DCA, anche se subottimale in attesa, può avere un **rendimento
realizzato superiore** per chi non ha ancora costruito disciplina
emotiva. Non è una "verità sgradevole": è solo onestà sul fatto che
gli investitori sono umani.

### Quando questa componente NON conta

Se sei una persona che capisce davvero le statistiche, ha già passato
crash importanti senza panic-vendere, e tratta gli investimenti come
posizioni di lungo periodo: il vantaggio psicologico del DCA è zero.
La matematica vince.

## 7. Una variante: Value Averaging

Versione "più aggressiva" del DCA. Invece di mettere una somma fissa
ogni mese, ti dai un **obiettivo di valore di portafoglio**: "ogni
mese voglio che il portafoglio crypto valga 500 EUR in più
dell'precedente". Se il mercato è salito tanto, devi mettere meno (o
addirittura vendere). Se è sceso, devi mettere di più.

Questo è **strutturalmente contrarian**: compri di più quando i prezzi
sono bassi, vendi quando sono alti. In simulazione storica spesso
batte sia DCA classico che lump sum, ma:
- Richiede di seguire i numeri ogni mese
- Può richiederti di **mettere cifre molto grandi** durante i crash,
  quando psicologicamente è più difficile
- Genera più costi di transazione (vedi L1.04)

Per L1, basta sapere che esiste. La maggior parte delle persone non lo
applica.

## 8. DCA per crypto, specifically

La crypto ha alcune particolarità:

### Pro per il DCA crypto

- **Volatilità altissima**: BTC fa swing intraday del 5-10% molto più
  spesso delle azioni. Il rischio di "comprare al massimo" è
  effettivamente più rilevante
- **Cicli marcati**: i bull market crypto durano 1-2 anni, i bear
  market 1-2 anni. DCA su 24-36 mesi attraversa naturalmente più di
  un ciclo
- **Strumenti automatici**: quasi tutti gli exchange supportano
  acquisti ricorrenti gratuiti (settimanali, mensili). Zero fatica
  operativa

### Contro per il DCA crypto

- **Costi di transazione**: 24 acquisti × 0.5% fee = 12% di costi
  cumulativi solo in fee. Per ridurre, accumula 2-3 mesi di risparmio
  e compra ogni 2-3 mesi
- **Crypto è ancora "early"**: il rendimento storico di BTC ha
  fortemente premiato chi è entrato presto e tenuto. Il "lump sum di
  10 anni fa" ha battuto qualsiasi DCA. **Ma** questo non è
  necessariamente replicabile dal 2026 in poi

### DCA come "first time" in crypto

Per chi non ha mai posseduto BTC/ETH: **DCA è probabilmente la scelta
giusta**, non per la matematica ma per il valore di "imparare con
poco". I primi 6-12 mesi di esposizione crypto sono in gran parte
emozionale (panic, FOMO, scimmia che vuole vendere, scimmia che vuole
raddoppiare). Meglio attraversarli con piccole somme.

## 9. Collegamento al nostro progetto

In Fase 6 (paper trading) avremo bisogno di **benchmark** contro cui
misurare i segnali del sistema:

- **Buy-and-hold** del Tier 1
- **DCA mensile** fisso su BTC (e/o ETH) — già menzionato in
  ROADMAP.md fase 7 come confronto continuo
- Eventualmente **DCA equal-weight** sul portafoglio Tier 1 intero

Se il sistema produce segnali che battono out-of-sample sia il
buy-and-hold che il DCA, è un risultato reale. Se batte solo il DCA
ma non il buy-and-hold, abbiamo solo replicato un timing scadente
"con più dati". Se non batte il DCA, il sistema non sta producendo
valore aggiunto rispetto a "investi tutti i mesi senza pensare".

Questo benchmark è importante perché **il DCA, per molti retail, è
il vero baseline pragmatico**, non il buy-and-hold (che richiede di
avere già il capitale).

## Glossario rapido

- **Dollar Cost Averaging (DCA)**: comprare una somma fissa a
  intervalli regolari, indifferentemente dal prezzo
- **Lump sum**: investire tutto il capitale disponibile in una sola
  operazione
- **Prezzo medio di carico**: il prezzo medio pesato a cui hai
  acquistato i tuoi asset
- **Media aritmetica vs media armonica**: la prima fa media dei
  prezzi, la seconda fa media inversa. Il DCA produce una media
  armonica
- **Value averaging**: variante in cui l'obiettivo è il valore del
  portafoglio, non l'importo investito. Strutturalmente contrarian
- **Buy-and-hold**: comprare e tenere per un orizzonte molto lungo,
  senza ribilanciare o vendere
- **Hindsight bias**: la tendenza a giudicare una strategia col senno
  di poi sapendo come è andata. "Era ovvio che il lump sum batteva il
  DCA negli anni 2010"

## Cosa portare via

- **Il lump sum batte il DCA ~2/3 delle volte** in matematica pura
  (studio Vanguard). Più i mercati salgono in media, più questo è
  vero
- Il **DCA è raccomandato comunque** perché protegge dalle decisioni
  emotive, e il rendimento *realizzato* di un investitore disciplinato
  che fa DCA può essere superiore a quello di un investitore che fa
  lump sum e poi si fa prendere dal panico
- Per chi guadagna uno stipendio, **il DCA non è una scelta — è la
  realtà operativa**. Il dibattito DCA vs lump sum riguarda chi ha
  capitale già disponibile
- Per **crypto specificamente**: DCA ha senso per principianti per
  ragioni psicologiche; matematicamente lo storico ha premiato il
  lump sum precoce ma non è replicabile in futuro
- Nel nostro progetto, **il DCA sarà il benchmark più importante**:
  se il sistema non batte il DCA out-of-sample, non sta producendo
  valore aggiunto

---

*Prossimo capitolo*: L1.07 — Volatilità e drawdown: cosa significano
davvero.
