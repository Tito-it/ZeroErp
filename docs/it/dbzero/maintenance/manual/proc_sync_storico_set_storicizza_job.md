## 📚 Documentazione Procedura: `maintenance.proc_sync_storico_set_storicizza_job`

> 👀 **Vedi anche:**
>
Approfondimento tabelle:
>
[config.storico_set_storicizza](/dbzero/config/tabelle/storico_set_storicizza)
>
Approfondimento funzioni:
>
[maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log)
> [maintenance.proc_sync_storico_set_storicizza](/dbzero/maintenance/funzioni/proc_sync_storico_set_storicizza)

---
### 🎯 Scopo Principale
(last review 07-01-26)
Wrapper di job che **esegue e traccia** la sincronizzazione della tabella `config.storico_set_storicizza`, delegando l’esecuzione alla procedura core `maintenance.proc_sync_storico_set_storicizza()` e centralizzando **logging** e **advisory lock** tramite `maintenance.fn_run_and_log`.

---

### Firma

```sql
PROCEDURE maintenance.proc_sync_storico_set_storicizza_job()
```

---

### Comportamento

1. Invoca `maintenance.fn_run_and_log(...)` con:

   * `p_jobname = 'sync_storico_set_storicizza'`
   * `p_stepname = 'run_sync_storico_set_storicizza'`
   * `p_sql = 'CALL maintenance.proc_sync_storico_set_storicizza();'`
   * `p_lock_key = hashtext('proc_sync_storico_set_storicizza')` per **evitare overlap**.
2. `fn_run_and_log` si occupa di:

   * aprire una riga su `maintenance.job_run_log`,
   * eseguire il `CALL` e registrare `rows_affected`,
   * chiudere il log con esito `ok = TRUE/FALSE`,
   * catturare e salvare dettagli di errore (SQLSTATE, HINT, CONTEXT) in caso di eccezione,
   * rilasciare l’eventuale advisory lock.

---

### Utilizzo tipico (pgAgent)

Nel job/step di pgAgent usa **SQL** con:

```sql
CALL maintenance.proc_sync_storico_set_storicizza_job();
```

> Consigliato impostare `jstkind = 's'` e `jstdbname` al database che contiene `maintenance.*`.

---

### Esecuzione manuale

```sql
CALL maintenance.proc_sync_storico_set_storicizza_job();
```

Dopo l’esecuzione, verifica il log:

```sql
SELECT *
FROM maintenance.job_run_log
WHERE jobname = 'sync_storico_set_storicizza'
ORDER BY started_at DESC
LIMIT 10;
```

---

### 🧯 Note operative

* L’`advisory lock` impedisce esecuzioni concorrenti multiple dello stesso job/step.
* Il logging standardizzato consente monitoraggio uniforme e diagnostica rapida.
* Il wrapper **non** apre/chiude transazioni: segue il contesto del chiamante.

---

{% include-markdown "signature-core.md" %}
