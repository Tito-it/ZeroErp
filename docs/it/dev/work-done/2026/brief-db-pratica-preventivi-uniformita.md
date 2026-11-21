# Brief DB — Pratica preventivi: tipo unico + flussi conferma ordine + revisione

> **Tipo**: brief DB (cosa serve, non come) · **Destinatario**: team DB (`dev/db-tid`)
> **Priorità**: 🟡 media · **Data**: 2026-06-29
> **Analisi di riferimento (il "perché")**:
> [analisi-uniformita-pratica-preventivi.md](analisi-uniformita-pratica-preventivi.md)
>
> Nota: qui descriviamo **cosa** deve ottenere il DB. **Come** realizzarlo
> (DDL, trigger, fn, seed) lo decide il team DB. Sotto solo obiettivi, vincoli e
> criteri di accettazione.

---

## Contesto in una frase

La pratica preventivi oggi automatizza tutto in un handler e diverge dal
programma standalone (niente selezione righe, niente revisione, modalità
fatturazione cablata, e la merce si ferma all'ordine senza arrivare in commessa).
Vogliamo che la pratica **riusi gli stessi passi dello standalone**. Questo brief
copre solo i **prerequisiti lato DB** (catalogo pratiche + aggancio revisione).

---

## Obiettivo 1 — Un unico tipo pratica `PREVENTIVI`

Oggi esistono due tipi che differiscono **solo** per la modalità di fatturazione
cablata sul flusso CONFERMA: `PREVENTIVI_IMMEDIATA` (id 9002) e
`PREVENTIVI_DIFFERITA` (id 9003).

**Cosa serve**:
- un **unico tipo `PREVENTIVI`** (la modalità non è più una proprietà del tipo);
- le **pratiche storiche** dei due tipi devono restare valide e leggibili sotto il
  tipo unico (migrazione/riconduzione — modalità a vostra scelta).

**Criterio di accettazione**: dopo la migrazione non esistono più i due tipi
distinti; le pratiche preventivi esistenti puntano al tipo unico e restano
apribili senza errori.

## Obiettivo 2 — Nuova sequenza di flussi del tipo `PREVENTIVI`

Serve il catalogo flussi (template + prerequisiti + azioni UI) per questa
sequenza, con prerequisiti **esito-aware** (ogni step si abilita al completamento
POSITIVO del precedente):

| Seq | Flusso | Scopo |
|---|---|---|
| 10 | RICHIESTA_CLIENTE | registrazione richiesta (manuale) |
| 20 | PREVENTIVAZIONE | apertura/editing preventivo (apre il drawer) |
| 30 | APPROVAZIONE_CLIENTE | accettazione del preventivo |
| 40 | SMISTAMENTO | apertura del pannello di smistamento righe |
| 50 | CONFERMA_ORDINE | emissione/conferma dell'ordine (**condizionale**: solo se lo smistamento ha generato un ordine merce) |
| 60 | INVIO_COMMESSA | invio dell'ordine a commessa (**condizionale**, come 50) |

**Cosa serve**:
- i flussi 40/50/60 devono poter aprire le **azioni UI** corrispondenti (servono
  le rispettive `azioni_ui` per SMISTAMENTO / CONFERMA_ORDINE / INVIO_COMMESSA,
  come già esiste l'azione "apri preventivo" per PREVENTIVAZIONE);
- 50 e 60 sono **condizionali al ramo merce** (se il preventivo è tutto servizi,
  la commessa nasce già allo step 40 e 50/60 non si applicano);
- **rimuovere la modalità di fatturazione cablata** (`handler_params`) dal flusso
  di conferma: la modalità ora si sceglie all'accettazione e vive sul preventivo
  (vedi Obiettivo 3, lato BE/FE — qui rileva solo togliere il dato cablato).

**Criterio di accettazione**: una pratica `PREVENTIVI` nuova espone, nell'ordine e
con i giusti vincoli di prerequisito, i 6 step; i passi 50/60 compaiono solo
quando esiste un ordine merce da confermare.

## Obiettivo 3 — Revisione preventivo dentro la pratica: aggancio alla rev attiva

La pratica si aggancia al preventivo ROOT (`pratiche_sorgenti`). Quando si crea
una **revisione**, nasce una nuova istanza dello stesso numero (rev attiva nuova).

**Cosa serve**: la pratica deve restare agganciata alla **revisione attiva** del
preventivo, non a quella superata. Il legame ROOT deve "seguire" la rev attiva
(meccanismo a vostra scelta: aggiornamento del legame alla creazione revisione,
oppure risoluzione dinamica via il predicato `is_attiva`).

**Criterio di accettazione**: creata una revisione di un preventivo agganciato a
una pratica, la pratica risulta collegata alla nuova rev attiva; annullata la
revisione, torna collegata al predecessore (coerente con `is_attiva`).

---

## Vincoli trasversali

- Niente ID hardcodati: tipi/stati/azioni risolti per codice.
- Le pratiche e i preventivi storici non devono rompersi (no produzione, ma dati
  di test reali da preservare).

## Fuori scope (non DB — li gestiamo noi BE/FE dopo i vostri prerequisiti)

- Comportamento degli handler / ritiro dell'handler monolitico (BE).
- Dialog di accettazione con modalità+competenza e pulsante "Smista tutto" (FE).
- Persistenza di modalità/competenza sul preventivo all'accettazione (BE/FE,
  riusa il path standalone già esistente).

> A prerequisiti pronti, BE/FE procedono secondo il piano §6.3/§6.4 dell'analisi.
