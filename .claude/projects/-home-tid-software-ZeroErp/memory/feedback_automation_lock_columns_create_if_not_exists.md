---
name: feedback_automation_lock_columns_create_if_not_exists
description: Aggiungere colonne a automation_lock_columns su tabella con lock trigger già esistente — su DB esistenti serve DROP+rigenera
metadata:
  type: feedback
---

L'automazione lock di ZeroErp (`dbops.fn_run_automations_lock_columns`, proc
`maintenance.proc_automations_lock_columns_job`) è **create-if-not-exists, NON
reconcile**: genera un unico trigger per tabella `trg_{table}_a10_lock_columns_upd`
solo se **non esiste già** (existence_strategy BY_NAME/BY_FUNCTION); la cleanup
(`fn_run_automations_drop_lock_trg`) droppa il trigger solo se **non resta alcuna
colonna da lockare**.

**Conseguenza**: aggiungere una riga a `dbops.automation_lock_columns.csv` per una
tabella che ha **già** un lock trigger (es. su `numero`) NON aggiunge la nuova
colonna se il trigger esiste già. Il `CALL proc_automations_lock_columns_job()`
non basta: salta la tabella.

**Why**: l'automazione non riconcilia il set di colonne di un trigger esistente.
Su DB **pulito/CI** non si vede (il trigger nasce completo al primo giro, via
`90_end/ci_apply` quando `myapp.env='ci'`); il drift colpisce solo i **DB di lunga
vita** (dev/staging/prod) dove il trigger era già materializzato con meno colonne.

**How to apply**: sui DB esistenti, una tantum:
```sql
DROP TRIGGER IF EXISTS trg_<tabella>_a10_lock_columns_upd ON <schema>.<tabella>;
SELECT dbops.fn_run_automations_lock_columns('AUTO', NULL, false);
```
Le righe del registro con `exec_mode='AUTO'` matchano qualunque p_exec_mode
(CI/SCHEDULED/AUTO). Prassi consolidata (preventivi.emittente_fiscale_id, ordini
cliente 2026-06-04): nessun changeset di remediation, auto su CI/fresh + manuale
sui DB esistenti. All'avvio della produzione valutare un changeset di remediation
riproducibile. Vedi `db-brief-ordini-lock-cliente.md` §5.4. Collegato a
[[feedback_db_actions_passaggio_team]].
