# Brief DB — i job notturni che la CI non esegue mai

> **Perimetro:** DB (`dev/db-tid`), più il workflow di CI (`.github/workflows/`).
> Nessuna ricaduta su BE né FE.
> **Aperto:** 2026-09-26.
> **Origine:** D4 di
> [brief-db-lock-di-colonna-fuori-registro.md](../work-done/brief-db-lock-di-colonna-fuori-registro.md),
> approvata da Tid il 2026-09-26, e l'**R-11** di
> [brief-db-processi-automatici-identita-e-perimetro.md](../work-done/brief-db-processi-automatici-identita-e-perimetro.md).
>
> **Stato:** 🔵 **APERTO: analisi fatta, niente scritto.** Le decisioni D1–D3
> (§4) spettano a Tid.
>
> **In una riga.** In CI `85_pgagent` è `MARK_RAN`: i job notturni non esistono,
> e le procedure che eseguono non girano mai. Tutto ciò che solo un job fa è un
> comportamento che la CI non vede. Il 26-09 questo ha prodotto per due giorni
> una diagnosi rovesciata («dev fuori modello»).

---

## 1. Il difetto, sul modello

Una automazione di `dbops` ha **due** vie per arrivare su un database:

| Via | Dove gira | Che cosa esegue |
| --- | --- | --- |
| `90_end/ci_apply/20250627-31` | CI, a ogni migrazione (seconda invocazione, `--contexts=ci_apply`) | un **elenco scritto a mano** di chiamate `fn_run_automations_*('CI', …)` |
| job pgAgent → `maintenance.proc_*_job()` | solo dove esiste pgAgent (dbdev, domani produzione) | il **corpo della procedura** (`p_sql` di `fn_run_and_log`), con `'SCHEDULED'` |

Sono due copie della stessa domanda, *«che cosa fa girare questa famiglia di
automazioni?»*, e nessuno le tiene allineate. ⇒ Quando la procedura fa qualcosa
che l'elenco di `ci_apply` non fa, quel qualcosa:

* **non è mai collaudato in CI**, né dalla migrazione né dai pgTAP, che girano
  dopo;
* **gira solo su dev**, e una divergenza dev/CI viene letta come «dev sporco»,
  perché la CI ricostruita da zero passa per il metro.

⭐ **Il caso che l'ha mostrato.** `proc_automations_lock_columns_job` chiamava anche
`fn_run_automations_drop_lock_trg`, che `ci_apply` non chiamava. Su dev cancellava
ogni sera i lock di colonna scritti a mano; in CI c'erano ancora. Ritirata il 26-09,
ma il meccanismo che l'ha resa invisibile è ancora lì.

## 2. La fotografia (2026-09-26 — fatto datato, non un motivo)

Le procedure della famiglia `automations_*` a confronto con `ci_apply`, lette sui
corpi vivi di dbdev e sul file di `ci_apply`:

| Procedura | Che cosa esegue | In `ci_apply`? |
| --- | --- | --- |
| `proc_automations_audit_update_job` | `fn_run_automations_audit_update` | ✅ |
| `proc_automations_storico_provision_job` | `fn_run_automations_storico_provision` | ✅ |
| `proc_automations_storico_job` | `fn_run_automations_storico` | ✅ |
| `proc_automations_tx_id_job` | `fn_run_automations_tx_id` | ✅ |
| `proc_automations_attivo_job` | `fn_run_automations_attivo` | ✅ |
| `proc_automations_lock_columns_job` | `fn_run_automations_lock_columns` + **`fn_run_automations_date_validita`** | lock ✅; date di validità ⚠️ solo dal `runAlways` `90_end/20260923-47`, non da `ci_apply` |
| `proc_automations_delete_block_job` | `fn_run_automations_delete_block` | ✅ |
| `proc_automations_overlap_job` | **`fn_apply_automazione_overlap`** | ❌ nessun giro di migrazione |
| `proc_automations_cleanup_job` | **`fn_run_automations_cleanup('SCHEDULED', ARRAY['dbops'])`** | ❌ nessun giro di migrazione |

⇒ Oggi **due** automazioni (OVERLAP, CLEANUP) non girano mai in CI. ⚠️ I 12
vincoli `EXCLUDE` coincidono comunque fra dev e CI (confrontati per nome, il
26-09): non è un argomento per lasciar stare. Vuol dire che oggi i vincoli
nascono anche per altre vie, e che il giorno in cui una riga nuova di
`dbops.automazione_overlap` dipenderà solo dal job, la CI non l'avrà.

Fuori dalla famiglia `automations_*` i job sono **operativi**: agiscono sui dati e
sul tempo, non sulla struttura (`send_pending_emails`, `draina_coda_*`,
`guardiano_digest`, `digest_presidi:*`, `chiusura_scadenze_daily`,
`sync_auth_user_expired_daily`, `listen_cambio_reparto`, `apply_storicizza_weekly`,
`sync_storico_set_storicizza`, `apply_fk_index_policy`). Vedi D2.

## 3. Proposta

### D1 — In CI si eseguono le PROCEDURE, non un elenco parallelo

Un changeSet `90_end/ci_apply` nuovo, `runAlways`, dopo l'attuale, che fa
`CALL maintenance.proc_automations_*_job()` per ogni procedura della famiglia,
nell'ordine di `ci_apply` (audit_update → storico_provision → storico → tx_id →
attivo → lock_columns → delete_block, poi overlap e cleanup).

* ⭐ **Si chiama la procedura, non si copia il suo corpo.** Copiarlo sarebbe una
  terza versione della stessa domanda. La procedura esiste già in CI (sta in
  `20_code`): manca solo **pgAgent**, non il codice.
* `fn_run_and_log` **rilancia** l'errore (rev R-12, 2026-09-05): un job che fallisce
  ferma la migrazione di CI. È voluto.
* ⚠️ Gira col modo `'SCHEDULED'`, come di notte. `ci_apply` resta col suo `'CI'`.
  Oggi tutte le righe dei registri sono `AUTO`; se un giorno una riga sarà `CI` o
  `SCHEDULED`, la CI eserciterà **entrambi** i giri, com'è in produzione.
* Da decidere: l'elenco scritto a mano in `20250627-31` **si ritira** (il giro
  `'CI'` diventa inutile) oppure resta accanto? La regola del 2 dice di
  ritirarlo. ⚠️ Ma `ci_apply` chiama anche `fn_seed_automazione_guard_utility` e
  `fn_apply_automazione_guard_utility`, che non hanno una procedura: quelle restano.

### D2 — I job operativi restano fuori

Mandare email, drenare code, calcolare digest in una CI non collauda niente di
strutturale, e dipende da dati e orologio. **Proposta: fuori**, dichiarato.
⚠️ Con un'eccezione da valutare: `apply_fk_index_policy` e `sync_storico_set_storicizza`
toccano la struttura (indici, storicizzazione). Vanno guardati uno per uno.

### D3 — Un presidio che l'elenco resti completo

Un pgTAP che confronta le procedure `maintenance.proc_automations_%_job` vive con
l'elenco del changeSet di D1, sul **catalogo**: una procedura nuova della famiglia
senza giro in CI fa rosso. ⚠️ Il changeSet non si legge da un pgTAP: il criterio va
dichiarato come elenco nel pgTAP stesso, come già si fa per le liste globali.
Una procedura nuova
richiede quindi due righe, e il rosso lo ricorda.

## 4. Decisioni per Tid

| | Domanda | Proposta |
| --- | --- | --- |
| D1 | Chiamare le procedure in un `ci_apply` nuovo? E ritirare l'elenco `'CI'` di `20250627-31`? | sì; ritirarlo, tenendo le due chiamate `guard_utility` |
| D2 | I job operativi restano fuori dalla CI? | sì, dichiarato; `apply_fk_index_policy` e `sync_storico_set_storicizza` da guardare |
| D3 | Presidio pgTAP sull'elenco delle procedure? | sì |

## 5. Rischi già noti

* **Due passate per lo storico** (nota di memoria del 15-09): su dev
  `automations_storico` parte prima di `automations_storico_provision`, e una
  madre nuova ha lo storico il giorno dopo. Con D1 l'ordine lo decide il
  changeSet, quindi in CI il problema non c'è; su dev resta. Da dire, non da
  risolvere qui.
* **`runAlways` in `90_end` gira prima di `ci_apply`** (memoria): il changeSet di
  D1 va nel contesto `ci_apply`, altrimenti nella prima passata troverebbe tabelle
  senza i trigger che le procedure presuppongono.
* **`fn_run_and_log` salta in silenzio** se l'advisory lock del job è già preso
  (`RETURN` con la riga «skip: another run in progress», `ok = true`). In CI non
  c'è un altro giro concorrente, quindi non dovrebbe succedere; ma un salto
  risulterebbe **verde**. Il changeSet di D1 può verificare, dopo le `CALL`, che
  ogni job abbia una riga `ok` **senza** quel messaggio.
