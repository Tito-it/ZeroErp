## 📘 Documentazione Concettuale – Procedura `maintenance.proc_automations_overlap_job`

> 👀 **Vedi anche**
>
Guide:
> [Automazione DB](/guide/automazione-db)
>
Approfondimento funzioni:
> [dbops.fn_apply_automazione_overlap](/dbzero/dbops/funzioni/fn_apply_automazione_overlap)
> [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log)
>
Approfondimento tabelle:
> [dbops.automazione_overlap](/dbzero/dbops/tabelle/automazione_overlap)

---
### 🎯 Scopo Principale
(latest review 02-06-26)
La procedura **`maintenance.proc_automations_overlap_job()`** e' un wrapper per
eseguire `dbops.fn_apply_automazione_overlap` in modalita' schedulata, con logging
centralizzato e lock applicativo anti-concorrenza.

E' il **runner notturno** del rule OVERLAP: ricrea i vincoli `EXCLUDE` mancanti
per le tabelle marcate `active=true` in `dbops.automazione_overlap`. E' il
meccanismo di **auto-guarigione** che impedisce a un EXCLUDE droppato per errore
(es. da un refactor) di restare assente. Introdotta con `refactor-overlap-v2`:
prima OVERLAP era l'unico rule con seed+apply ma senza job schedulato.

---

### Logica operativa

1. Chiama `maintenance.fn_run_and_log` con:
   * `p_jobname = 'automations_overlap'`
   * `p_stepname = 'run_automations_overlap'`
   * `p_sql = SELECT dbops.fn_apply_automazione_overlap('SCHEDULED', false)`
2. Usa `hashtext('automations_overlap')` come lock per impedire esecuzioni concorrenti.

E' **idempotente**: `fn_apply` crea solo i vincoli mancanti e salta quelli gia'
presenti (di norma, a regime, non fa nulla).

---

### Schedulazione

Invocata dal job pgAgent `automations_overlap` (schedule `daily_21`, ogni giorno
alle 21:00), allineato agli altri job automazioni.

---

### Esempio di esecuzione

`CALL maintenance.proc_automations_overlap_job();`

---

{% include-markdown "signature-core.md" %}
