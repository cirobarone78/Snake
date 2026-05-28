# CLAUDE.md

> Istruzioni operative per ogni sessione di Claude Code su questo progetto.
> **Leggere SEMPRE prima di iniziare qualsiasi attività.**

## Cos'è questo progetto

Sistema sperimentale di **analisi multifattoriale dei mercati finanziari** con focus
sulle criptovalute. Obiettivo: integrare dati di mercato, on-chain, macro, cicli e
sentiment da notizie (finanza, tecnologia, geopolitica, politica) per cercare
segnali predittivi sull'andamento di asset selezionati.

**Natura del progetto**: ricerca quantitativa, non "trading bot da arricchirsi".
Il rigore metodologico viene prima dei risultati.

## File da leggere a inizio sessione

In quest'ordine:

1. **`STATUS.md`** — dove siamo ora, cosa è in corso, cosa è bloccato
2. **`ROADMAP.md`** — fase corrente e prossimi obiettivi
3. **`OPEN_QUESTIONS.md`** — decisioni ancora aperte (non assumere risposte)
4. **`DECISIONS.md`** — decisioni già prese, non rimetterle in discussione senza motivo
5. **`VISION.md`** — solo se serve riallineare sull'obiettivo di alto livello

## Convenzioni operative

### Lingua
- **Chat con l'utente**: italiano
- **Codice, identificatori, log, commit message**: inglese
- **File di documentazione (`.md`)**: italiano
- **Commenti nel codice**: solo se aggiungono il "perché" (vedi sotto)

### A fine sessione (importantissimo per la continuità)
- Aggiornare **`STATUS.md`** con: cosa fatto, cosa lasciato in corso, cosa serve sapere alla prossima sessione
- Se è stata presa una decisione architetturale o di scope, registrarla in **`DECISIONS.md`** con format ADR
- Se è emersa una nuova domanda aperta, aggiungerla in **`OPEN_QUESTIONS.md`**
- Se uno step della roadmap è completato, marcarlo in **`ROADMAP.md`**

### Atteggiamento metodologico (non negoziabile)
- **Mai** trarre conclusioni da un singolo backtest senza out-of-sample testing
- **Sempre** documentare look-ahead bias check, survivorship bias check
- **Mai** promettere previsioni: parliamo sempre di segnali probabilistici, mai di certezze
- **Documentare anche cosa NON funziona** — gli esperimenti falliti vanno tracciati
- Le ipotesi vanno scritte **prima** di vedere i risultati, non dopo

### Vincoli operativi
- **Nessuna esecuzione di trade reali** in nessun ambiente, mai, senza richiesta esplicita E documentazione del consenso in `DECISIONS.md`
- API key e credenziali: **mai** in commit; usare `.env` + `.gitignore`
- Dati storici scaricati: tenerli fuori dalla repo se grossi (>10MB), usare `.gitignore`

## Stack & ambiente

**Stack tecnologico**: ancora **da definire** (vedi `OPEN_QUESTIONS.md`).
Probabile direzione: Python (ecosistema data science), ma da confermare.

**Stato attuale**: nessun codice ancora scritto. Siamo in **Fase 0 — Framing**.

## Quando in dubbio

- Su scope o obiettivo → rileggi `VISION.md` e chiedi all'utente
- Su una decisione tecnica → consulta `DECISIONS.md`; se assente, **proponi** prima di implementare
- Su priorità → segui `ROADMAP.md` ordine fasi

## Cosa NON fare

- Non creare file `.md` di documentazione aggiuntivi senza chiedere
- Non installare dipendenze pesanti senza che lo stack sia confermato
- Non scaricare dataset grossi senza prima discutere storage e licenze
- Non creare codice "speculativo" per fasi future della roadmap
- Non aggiungere abstraction layer o framework di test prima che ci sia codice da testare
