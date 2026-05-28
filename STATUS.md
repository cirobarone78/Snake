# STATUS.md

> Stato corrente del progetto. **Aggiornare a ogni sessione.**
> Questo è il primo file che chi (umano o agente) riprende il lavoro deve leggere.

---

## Ultimo aggiornamento
2026-05-28

## Fase corrente
**Fase 0 — Framing & setup**

## Cosa è stato fatto

### 2026-05-28
- Repository svuotata dal precedente progetto Snake (gioco)
- Definita la natura del progetto: analisi multifattoriale dei mercati con
  focus crypto, integrando dati di mercato, on-chain, macro, cicli e sentiment
  da notizie multi-dominio
- Creati i file di documentazione di base:
  - `CLAUDE.md` (istruzioni operative per sessioni)
  - `VISION.md` (obiettivo e principi)
  - `ROADMAP.md` (fasi e deliverable)
  - `STATUS.md` (questo file)
  - `DECISIONS.md` (log decisioni)
  - `OPEN_QUESTIONS.md` (decisioni ancora aperte)

## Cosa è in corso
- Nessuna attività di sviluppo. Stiamo ancora chiudendo la Fase 0.

## Prossimo step
**Risolvere le decisioni critiche in `OPEN_QUESTIONS.md`** prima di passare a
Fase 1. In particolare:

1. Trading reale vs solo ricerca/segnali → definisce vincoli di sicurezza
2. Asset universe iniziale → focalizza l'effort di ingestion
3. Timeframe predittivo → determina granularità dei dati
4. Tipo di output del modello → determina la target variable
5. Budget per dati premium → vincola le sorgenti utilizzabili
6. Stack tecnico (probabilmente Python, da confermare)

## Blocker
Nessuno tecnico. In attesa che le decisioni di scope siano prese (richiedono
input dell'utente).

## Note per la prossima sessione
- Se l'utente non ha ancora risposto alle open questions, **non procedere** a
  scrivere codice. Chiedere conferma sulle decisioni critiche prima.
- Se invece le decisioni sono state prese e registrate in `DECISIONS.md`,
  procedere con Fase 1: inventario sorgenti dati.
- Verificare sempre `OPEN_QUESTIONS.md` per eventuali aggiornamenti.
