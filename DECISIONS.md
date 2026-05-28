# DECISIONS.md

> Log delle decisioni prese, in stile **ADR (Architecture Decision Record)** semplificato.
> Una volta scritta una decisione qui, non rimetterla in discussione senza un motivo
> concreto (nuovi dati, vincoli cambiati). Le decisioni si **superano**, non si cancellano.

## Format

```
## ADR-NNN — Titolo breve
**Data**: YYYY-MM-DD
**Stato**: Accepted | Superseded by ADR-XXX | Deprecated
**Contesto**: perché si è dovuto decidere
**Decisione**: cosa è stato deciso
**Conseguenze**: cosa implica, cosa preclude, cosa abilita
```

---

## ADR-001 — Riutilizzo della repository "Snake"

**Data**: 2026-05-28
**Stato**: Accepted

**Contesto**: La repository conteneva un piccolo gioco Snake in HTML/JS che
l'utente non vuole più mantenere. Voleva una repo pulita per un nuovo progetto
sperimentale di analisi finanziaria.

**Decisione**: Rimosso completamente il contenuto pregresso (`index.html`).
README azzerato a placeholder. La repo conserva il nome "Snake" — può essere
rinominata in futuro, ma per ora non è una priorità.

**Conseguenze**:
- Il nome "Snake" non è più semanticamente legato al contenuto: ricordarsene
- La storia git mantiene traccia del progetto precedente
- Nessun impatto su sviluppo futuro

---

## ADR-002 — Natura del progetto: ricerca, non trading bot

**Data**: 2026-05-28
**Stato**: Accepted

**Contesto**: Il progetto può essere interpretato in due modi: (a) come trading
bot operativo, (b) come progetto di ricerca quantitativa che produce analisi e
segnali. Le due strade hanno requisiti, rischi e priorità molto diverse.

**Decisione**: Il progetto è inquadrato come **ricerca quantitativa
multifattoriale**. Nessuna esecuzione automatica di trade. Output del sistema
sono segnali probabilistici e analisi, non ordini di compravendita.

**Conseguenze**:
- Eliminato (per ora) il bisogno di integrazioni con exchange per ordini
- Eliminato (per ora) il bisogno di gestione di chiavi API con permessi di trading
- Focus su rigore metodologico, riproducibilità, honest reporting
- Apre la porta a un'eventuale fase futura "paper trading", ma solo dopo che la
  ricerca abbia prodotto risultati out-of-sample credibili
- Qualsiasi futura introduzione di esecuzione reale richiede una nuova ADR
  esplicita e consenso documentato

---

## ADR-003 — Convenzioni linguistiche

**Data**: 2026-05-28
**Stato**: Accepted

**Contesto**: L'utente comunica in italiano. Standard di sviluppo (codice,
librerie, ecosistema) sono in inglese. Serve una regola chiara per evitare
inconsistenze.

**Decisione**:
- Comunicazione chat: **italiano**
- File di documentazione `.md`: **italiano**
- Codice, identificatori, log, commit message: **inglese**
- Commenti nel codice: inglese, solo quando aggiungono il "perché" non ovvio

**Conseguenze**:
- Più facile per l'utente leggere documentazione e roadmap
- Il codice resta portabile e leggibile da chiunque
- Nessun mix di lingue all'interno dello stesso artefatto

---

<!--
Template per nuove ADR:

## ADR-NNN — Titolo breve
**Data**: YYYY-MM-DD
**Stato**: Accepted
**Contesto**:
**Decisione**:
**Conseguenze**:
-->
