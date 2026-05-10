# Brief DB — Nuovo stato preventivo `EVASO` + transizione automatica da `ACCETTATO`

> **Tipo**: seed dati (config.stati_doc_preventivi + config.transizioni_stati_preventivi).
> **Branch**: `dev/db-tid`.
> **Autore brief**: backend agent (Tid, sessione 2026-05-10 23:30).
> **Trigger**: scenario §3.4 test plan — dopo il push commessa il preventivo
> resta in `ACCETTATO` indefinitamente. Manca uno stato terminale che dica
> "preventivo gia' lavorato lato fatturazione". Soluzione richiesta da Tid:
> introdurre lo stato `EVASO`.

## Contesto

`vendite.preventivi.stato_doc_preventivo_id` punta a `config.stati_doc_preventivi`.
Stati attualmente seedati (id, codice_interno, descrizione, ordine):

| id | codice_interno | descrizione | ordine |
|----|----------------|-------------|--------|
| 1  | DRAFT          | Bozza       | 10     |
| 2  | EMESSO         | Emesso      | 20     |
| 4  | ACCETTATO      | Accettato   | 40     |
| 5  | RIFIUTATO      | Rifiutato   | 50     |
| 7  | SCADUTO        | Scaduto     | 60     |
| 9  | ANNULLATO      | Annullato   | 70     |

Le transizioni ammesse (`config.transizioni_stati_preventivi`) sono:

| da → a                | manuale | label_key                       |
|-----------------------|---------|---------------------------------|
| DRAFT → EMESSO        | si      | preventivi.azione_emetti        |
| DRAFT → ANNULLATO     | si      | preventivi.azione_annulla       |
| EMESSO → ACCETTATO    | si      | preventivi.azione_accetta       |
| EMESSO → RIFIUTATO    | si      | preventivi.azione_rifiuta       |
| EMESSO → SCADUTO      | no (auto, job notturno) | -            |
| EMESSO → ANNULLATO    | si      | preventivi.azione_annulla       |
| ACCETTATO → ANNULLATO | si      | preventivi.azione_annulla       |

Manca un percorso da `ACCETTATO` verso uno stato terminale di
"lavorazione fatturazione completata".

## Azione richiesta al team DB (su `dev/db-tid`)

### 1. Insert seed in `config.stati_doc_preventivi`

Nuovo record:

| Campo            | Valore                                                |
|------------------|-------------------------------------------------------|
| `codice_interno` | `EVASO`                                               |
| `codice`         | `EVASO`                                               |
| `descrizione`    | `Evaso` (it) / `Fulfilled` (en — se i18n previsto)   |
| `attivo`         | `true`                                                |
| `ordine`         | `45` (subito dopo ACCETTATO=40, prima di RIFIUTATO=50) |
| `meta`           | `{}`                                                  |

Vincolo univoco su `codice_interno`: verificare che `EVASO` non sia
gia' presente (non lo e' dalla query odierna). `id` autogenerato dalla
sequenza.

Suggerimento naming migration:
`YYYYMMDD-NN-seed-config-stati-doc-preventivi-evaso-<author>.yaml`.

### 2. Insert seed in `config.transizioni_stati_preventivi`

Nuova transizione **automatica** ACCETTATO → EVASO:

| Campo         | Valore                                              |
|---------------|-----------------------------------------------------|
| `stato_da_id` | `4` (ACCETTATO)                                     |
| `stato_a_id`  | id appena inserito di `EVASO`                       |
| `attivo`      | `true`                                              |
| `meta`        | `{"manuale": false}` (scatenata dal BE post-push)   |

**Importante — manuale=false**: la transizione non e' offerta come
pulsante UI ma e' invocata dal codice Python `push_a_commessa` quando
il push commessa completa tutte le righe pushable del preventivo. UX:
nessun pulsante, l'utente vede lo stato cambiare in automatico nel
drawer al refresh post-push.

### 3. Eventuale transizione `EVASO → ANNULLATO` — NON inclusa

Decisione: un preventivo gia' evaso (= dati gia' propagati a
`commesse_attivita`) **non si annulla** dalla UI. Annullarlo lascerebbe
righe orfane in commessa con sorgente "fantasma". Se serve invertire,
si fa lato commessa (annullamento riga commessa_attivita). Per ora
nessuna transizione in uscita da EVASO — stato veramente terminale.

### 4. Backfill — NON necessario

I preventivi esistenti gia' pushati (es. PRV0000034 con 4 righe in
`commesse_attivita`) restano `ACCETTATO` come dato legacy. Solo i
push successivi al deploy transiteranno a `EVASO`. ZeroErp e' in dev,
breaking-change ammesso, niente backfill richiesto.

### 5. Test pgTAP

* Esistenza record EVASO con `codice_interno = 'EVASO'`, `attivo = TRUE`,
  `ordine = 45`.
* Esistenza transizione (`stato_da_id = 4`, `stato_a_id = <evaso_id>`,
  `meta->>'manuale' = 'false'`).
* Nessuna transizione in uscita da EVASO (cioe' `WHERE stato_da_id =
  <evaso_id>` deve essere 0 righe).

## BE Python (azione lato `dev/backend-tid`)

Da fare dopo l'atterraggio DB:

1. **`preventivi_service.push_a_commessa`**: dopo `pr_run_commesse_push_one`
   con `stato="COMPLETATO"`, transitare il preventivo a `EVASO`:
   ```python
   if report["stato"] == "COMPLETATO":
       repo.update_stato_preventivo(preventivo_id, "EVASO")
   ```
   (Pseudo-codice — implementazione finale richiede risoluzione id stato
   via lookup config).

2. **`_STATI_FATTURABILI`**: invariato (`{"ACCETTATO"}`). Push da EVASO
   bloccato: dopo che lo stato e' EVASO non si ri-pusha. UX coerente
   con pulsante FE gia' disabilitato per "tutte righe in commessa".

3. **Test BE**:
   * `test_push_a_commessa_ok` esteso: mock `update_stato_preventivo`
     chiamato con `"EVASO"` dopo `pr_run_commesse_push_one` ok.
   * `test_push_a_commessa_parziale_non_evade`: se `stato="PARZIALE"`
     il preventivo resta `ACCETTATO`.

## FE — modifiche minime

* i18n: nessuna modifica obbligatoria (lo stato e' visualizzato
  dinamicamente dal `stato_descrizione` BE).
* `PreventiviIntegrazione.vue`: gia' disabilita il pulsante quando le
  righe sono tutte in commessa — niente nuova logica.
* Eventuale Tag color severity per `EVASO`: aggiungere "success"
  (verde) in [severity.js](../../../../frontend/src/core/utils/severity.js)
  `statoPreventivoSeverity` mappa se esiste — verifica prima.

## Smoke post-fix

1. DB applicato.
2. BE atterrato.
3. Smoke UI su un preventivo `ACCETTATO` non ancora pushato:
   click "Invia a fatturazione" → toast "Push completato: N righe inviate"
   + tag stato passa da `ACCETTATO` a `EVASO` (verde).
4. Pulsante "Invia a fatturazione" sparisce/disabilitato (gia' coperto
   dalla logica `tutteRighePushate` del componente).

## Riferimenti

* Memoria progetto: `feedback_stato_terminale_con_data` — pattern
  generico per stati terminali (es. CESSATO/CHIUSO). EVASO segue lo
  stesso pattern semantico, senza colonna data dedicata (timestamp
  cambio stato gia' tracciato da `data_update` audit).
* Schema: `config.stati_doc_preventivi`, `config.transizioni_stati_preventivi`,
  `vendite.preventivi.stato_doc_preventivo_id`.
* Test plan: [sviluppo-listini-v5-test-ui.md §3.4](sviluppo-listini-v5-test-ui.md).

## Note di rollback

Cambio additive (insert seed). Rollback: nuova migration con
`DELETE FROM config.transizioni_stati_preventivi WHERE stato_a_id = (SELECT id FROM config.stati_doc_preventivi WHERE codice_interno = 'EVASO')`
poi `DELETE FROM config.stati_doc_preventivi WHERE codice_interno = 'EVASO'`.
Eventuali preventivi gia' transitati a EVASO restano ANNULLATI o, prima
del rollback, riportati a ACCETTATO con `UPDATE vendite.preventivi SET
stato_doc_preventivo_id = 4 WHERE stato_doc_preventivo_id = <evaso_id>`.
