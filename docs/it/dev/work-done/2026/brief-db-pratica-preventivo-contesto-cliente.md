# Brief DB — Pratica espone il contesto cliente per i documenti collegati

**Area:** `pratiche` (lettura) · **Tipo:** esposizione dato derivato
**Branch destinazione:** `dev/db-tid`
**Richiesto da:** backend agent (per conto di Tid) · **Data:** 2026-06-15
**Stato:** ✅ **CHIUSO (2026-06-15)** — DB ha consegnato `script.fn_get_billing_account_by_istanza`
(commit `f3c4710ca`); BE la proietta su dettaglio pratica + flusso, FE pre-compila e blocca.

> **Portata** (Tid 2026-06-15): non solo preventivo. Stesso contesto serve ai
> documenti che si aprono dal flusso pratica — **preventivo, offerta, contratto**
> — che condividono il modello cliente (`billing_account_id` + `istanza_utility_id`).
> Gli **ordini** restano fuori (nascono dal push a valle, non dal flusso).
>
> Questo brief descrive **cosa** deve mettere a disposizione il DB, **non come**
> (scelta implementativa — vista, colonna derivata, funzione — è del team DB).
> Le azioni DB non sono eseguite dal backend agent.

---

## 1. Contesto

Una pratica apre dal proprio flusso un documento della famiglia **preventivo /
offerta / contratto** (percorso pratica-first). Requisito di Tid: il documento
creato da dentro la pratica deve ereditare **cliente (billing account) e istanza
utility dalla pratica**, valorizzati in automatico e **non modificabili**
dall'operatore (non possono divergere dal contesto della pratica).

Decisione di modello già presa (Tid, 2026-06-15): **l'istanza utility è sempre
presente sulla pratica** ed è la fonte dell'istanza del documento. Il
`billing_account_id` invece può esserci (cliente attivo) o no (prospect): la sua
**presenza** governa anche quali documenti sono offribili dal flusso — offerta e
contratto richiedono BA, il preventivo no (vedi
[brief-design-attivita-ui-da-flusso-data-driven §5-bis](brief-design-attivita-ui-da-flusso-data-driven.md)).

## 2. Cosa serve dal DB

La pratica deve esporre, **per il documento collegato**, il proprio contesto
cliente già risolto:

1. **`istanza_utility_id`** della pratica — già esposto oggi sul dettaglio
   pratica. Nessun lavoro, citato solo per completezza: è la chiave obbligatoria
   del preventivo.
2. **`billing_account_id`** coerente con quell'istanza — **oggi NON esposto** dal
   dettaglio pratica. Serve che la pratica lo metta a disposizione come dato
   **derivato** dal proprio contesto (istanza / soggetto-cliente), così il
   documento lo possa precompilare e bloccare senza che il frontend faccia
   derivazioni di dominio.

Valore atteso del punto 2:

- se il soggetto della pratica è un **cliente attivo** per quell'istanza →
  il `billing_account_id` corrispondente;
- se la pratica è un **prospect puro** (nessun cliente/BA ancora) → **assente
  (NULL)**: il preventivo ammette `billing_account_id` nullo (l'istanza basta);
  offerta e contratto invece **non** sono offribili in questo caso (richiedono BA).

## 3. Vincoli di coerenza da rispettare

- Il `billing_account_id` esposto deve essere **coerente con l'istanza** secondo
  la stessa regola che il preventivo già applica a DB (guard
  `trgfn_preventivi_guard_utility_istanza_coerenza` /
  `script.fn_check_utility_istanza_coerenza`). In altre parole: la coppia
  `(istanza_utility_id, billing_account_id)` che la pratica espone deve essere
  una coppia che il preventivo accetterebbe — altrimenti il blocco lato UI
  porterebbe a un INSERT che il guard rifiuta.
- Nessun nuovo dato persistito sulla pratica è richiesto dal requisito: serve un
  **dato in lettura** (derivato). Se il team DB ritiene più sano materializzarlo,
  è una scelta sua.

## 4. Cosa NON è richiesto

- Nessuna logica di scrittura, nessun trigger nuovo sul preventivo.
- Nessuna gestione del caso "pratica con solo ruolo cliente senza istanza":
  per i preventivi l'istanza è sempre presente (decisione §1).
- Nessun endpoint nuovo se il dato può viaggiare sul dettaglio pratica esistente
  (scelta del team DB).

## 5. A valle (FE/BE, non DB — solo per contesto)

Alla consegna del dato, il frontend (il drawer del documento aperto dalla pratica —
preventivo/offerta/contratto) precompila istanza + BA dal contesto pratica e li
blocca **da subito**. Piano FE in
[brief-fe-pratica-preventivo-cliente-bloccato.md](brief-fe-pratica-preventivo-cliente-bloccato.md)
(in attesa di questo prerequisito — [[feedback_be_fe_attende_prerequisiti_db]]).
