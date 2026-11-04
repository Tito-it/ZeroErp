## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — gli schemi del giro, quando non si passano
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole che ogni runner legge
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — l'ordine con cui i runner girano davvero, nel rilascio e su pgAgent
>
> Approfondimento funzioni:
>
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope) — la risoluzione dell'ambito che i runner usano
> * [dbops.fn_run_automations_tx_id](/dbzero/dbops/funzioni/fn_run_automations_tx_id) — parte `TX_ID`
> * [dbops.fn_run_automations_audit_update](/dbzero/dbops/funzioni/fn_run_automations_audit_update) — parte `AUDIT_UPDATE`
> * [dbops.fn_run_automations_storico](/dbzero/dbops/funzioni/fn_run_automations_storico) — parte `STORICO`
> * [dbops.fn_run_automations_lock_columns](/dbzero/dbops/funzioni/fn_run_automations_lock_columns) — parte `LOCK_COLUMNS`
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — parte `ATTIVO`
> * [dbops.fn_run_automations_date_validita](/dbzero/dbops/funzioni/fn_run_automations_date_validita) — parte `DATE_VALIDITA`
> * [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup) — parte `CLEANUP`
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — il giro delle automazioni e le sue regole

---

### 🎯 Scopo Principale

Orchestratore a mano del framework delle automazioni: risolve gli schemi del giro e chiama, una
dopo l'altra, le parti richieste in `p_parts`, passando a ciascuna lo stesso modo di esecuzione,
gli stessi schemi e lo stesso dry run.

⚠️ Non è il punto da cui le automazioni girano davvero. Nessun changeSet, job o funzione la
chiama: la convergenza del rilascio e i job pgAgent chiamano ogni runner attraverso il suo wrapper
`maintenance.proc_automations_*_job`, nell'ordine di `dbops.processi`. Questa funzione resta come
comando per chi lavora a mano.

---

### Le parti

`p_parts` elenca le parti da eseguire, che girano sempre in quest'ordine, qualunque sia l'ordine
in cui si scrivono:

* `TX_ID`, `AUDIT_UPDATE`, `STORICO`, `LOCK_COLUMNS`, `ATTIVO`, `DATE_VALIDITA` — il valore di
  default, cioè tutto tranne il cleanup;
* `CLEANUP` — solo se chiesto;
* `TABLE_RULES` — parola di compatibilità che accende `TX_ID`, `AUDIT_UPDATE`, `STORICO`,
  `LOCK_COLUMNS` e `DATE_VALIDITA`, ma non `ATTIVO` né `CLEANUP`.

Un nome che non è fra questi è ignorato senza errore.

⚠️ L'ordine e l'insieme non sono quelli della convergenza del rilascio, che segue
`dbops.processi`: lì la storicizzazione prepara le tabelle (`fn_run_automations_storico_provision`)
prima dei trigger di storico, e girano anche il blocco delle cancellazioni e i vincoli di
sovrapposizione. Qui quelle parti non ci sono: chi lancia `STORICO` da qui su una tabella nuova non
passa dalla preparazione.

---

### L'ambito

Con `p_schemas` passato, gli schemi sono quelli, così come sono. Senza, sono gli schemi di
`dbops.automation_scope`, e se il registro è vuoto tutti gli schemi tranne quelli di sistema e
`storico`. Ogni runner rifà comunque la risoluzione con `dbops.fn_resolve_scope` e filtra le
tabelle con `dbops.fn_table_in_scope`: il calcolo fatto qui è una copia, che non aggiunge niente
a quello dei runner.

`p_exec_mode` è il modo del giro (`AUTO`, `CI`, `SCHEDULED`): ogni runner applica le regole il cui
modo è `AUTO` o è uguale a questo. Con `p_dry_run` vero ogni runner scrive in `dbops.audit_log`
che cosa farebbe, senza DDL.

---

### Un errore ferma il giro

La funzione non isola le parti: un errore sollevato da un runner esce e annulla anche il lavoro
delle parti già eseguite nella stessa transazione. Non solleva codici suoi.

---

### Note di migrazione

* 2026-01-10 — entra la parte `LOCK_COLUMNS`; il 2026-02-07 la parte `CLEANUP`.
* 2026-08-04 — corretto il ramo di ripiego dell'ambito, che usava un alias non dichiarato.
* 2026-09-23 — entra la parte `DATE_VALIDITA`, anche nel default.

---

{% include-markdown "signature-core.md" %}
